from __future__ import annotations
from typing import Callable, List, Dict, Tuple
from collections import defaultdict
from lxml import etree as ET
from .row import Row

Predicate = Callable[[Dict[str, str], "NodeProxyChildren", str], bool]
Extractor = Callable[[Row, Dict[str, str], "NodeProxyChildren", str], None]
grouped_children = defaultdict(list)

class NodeProxyChildren(dict):
    """Maps child tag names to single-element NodeProxy wrappers."""
    def __getattr__(self, tag: str) -> "NodeProxy":
        try:
            return self[tag]
        except KeyError:
            raise AttributeError(f"No child tag named '{tag}'")


class NodeProxy:
    """
    Fluent, chain-able wrapper around an XML element *plus its in-progress CSV
    row*.  Internal representation is a list of `(element,row)` tuples so that
    each traversal branch keeps an independent copy of the row.
    """

    def __init__(
        self,
        items: List[Tuple[ET._Element, Row]],
        headers: List[str],
        extractions: List[Row],
    ):
        self._items = items
        self.headers = headers
        self.extractions = extractions

    # ── traversal ──────────────────────────────────────────────────────────
    def __getattr__(self, tag: str) -> "NodeProxy":
        children = []
        for el, row in self._items:
            # create NEW id only if this row hasn't been 'sealed' yet
            fresh = not row._sealed
            for child in el.iterfind(tag):
                child_row = row.copy(new_id=fresh)
                print(f"child.tag: {child.tag}" + f" | new_id: {fresh}")
                child_row._sealed = True  # prevent deeper splits
                children.append((child, child_row))
        return NodeProxy(children, self.headers, self.extractions)
    
        # ── branch merge / union ───────────────────────────────────────────────
    def __add__(self, other: "NodeProxy") -> "NodeProxy":
        if not isinstance(other, NodeProxy):
            return NotImplemented
        if self.headers != other.headers:
            raise ValueError("Cannot merge proxies with different header sets")

        merged_by_id: dict[str, Row] = {}

        def _absorb(items):
            for _el, row in items:
                rid = row._row_id
                # first row with this id -> copy
                if rid not in merged_by_id:
                    merged_by_id[rid] = Row(row)        # shallow copy
                else:
                    merged_by_id[rid].update(row)       # union keys

        _absorb(self._items)
        _absorb(other._items)

        # fabricate dummy-element None; we only care about rows now
        combined_items = [(None, r) for r in merged_by_id.values()]
        return NodeProxy(combined_items, self.headers, self.extractions)


    # ── addition ──────────────────────────────────────────────────────────
    def __add__(self, other: "NodeProxy") -> "NodeProxy":
        if not isinstance(other, NodeProxy):
            return NotImplemented
        if self.headers != other.headers:
            raise ValueError("Header sets differ; cannot merge.")

        merged_by_id: dict[str, Row] = {}

        def _absorb(items):
            for _el, row in items:
                rid = getattr(row, "_row_id", id(row))  # fall back for safety
                if rid not in merged_by_id:
                    merged_by_id[rid] = row  # first time we see this row
                else:
                    merged_by_id[rid].update(row)  # union columns

        _absorb(self._items)
        _absorb(other._items)

        # We don't care which element pointer survives; keep first or None
        combined_items = [(None, r) for r in merged_by_id.values()]
        return NodeProxy(combined_items, self.headers, self.extractions)

    # ── filtering ──────────────────────────────────────────────────────────
    def where(self, fn: Predicate) -> "NodeProxy":
        """
        Keep only the element/row pairs for which *fn* returns True.
        fn signature: (attributes, children_proxy, text) -> bool
        """
        kept: List[Tuple[ET._Element, Row]] = []

        for el, row in self._items:
            a = el.attrib

            # Group children by tag
            grouped_children = defaultdict(list)
            for ch in el:
                grouped_children[ch.tag].append(ch)

            # Wrap each tag's group into a NodeProxy
            c = NodeProxyChildren(
                {
                    tag: NodeProxy(
                        [(ch, row.copy(new_id=True)) for ch in group],
                        self.headers,
                        self.extractions,
                    )
                    for tag, group in grouped_children.items()
                }
            )

            t = (el.text or "").strip()

            if fn(a, c, t):
                kept.append((el, row))

        return NodeProxy(kept, self.headers, self.extractions)

    def where2(self, fn) -> "NodeProxy":
        filtered_items = []
        for el, row in self._items:
            a = el.attrib  # attributes
            t = (el.text or "").strip()  # text

            # making 'c' (children)
            child_items = []
            for child in el:
                child_row = row.copy(new_id=False)
                child_items.append((child, child_row))
            c = NodeProxy(child_items, self.headers, self.row)

            if fn(a, c, t):
                filtered_items.append((el, row))
        return NodeProxy(filtered_items, self.headers, self.extractions)

    # ── extraction ─────────────────────────────────────────────────────────
    def extract(self, fn: Extractor) -> "NodeProxy":
        """
        Mutate the Row for every element/row pair using user-supplied *fn*.
        fn signature: (row, attributes, children_proxy, text) -> None
        """
        for el, row in self._items:
            a = el.attrib

            # Group children by tag
            grouped_children = defaultdict(list)
            for ch in el:
                grouped_children[ch.tag].append(ch)

            # Wrap each group in a NodeProxy (sharing the same row)
            c = NodeProxyChildren(
                {
                    tag: NodeProxy(
                        [(ch, row) for ch in group], self.headers, self.extractions
                    )
                    for tag, group in grouped_children.items()
                }
            )

            t = (el.text or "").strip()
            fn(row, a, c, t)

        return self

    # ── termination ────────────────────────────────────────────────────────
    def commit(self) -> "NodeProxy":
        """
        Append a *copy* of every Row in the current proxy to *extractions*,
        normalising missing headers to empty strings.
        """
        for _, row in self._items:
            self.extractions.append(Row(**{h: row.get(h, "") for h in self.headers}))
        return self

    # –– convenience helpers --------------------------------------------------
    @property
    def elem(self) -> ET._Element:
        """Return the *first* element in this proxy (98 % of ad-hoc cases)."""
        return self._items[0][0] if self._items else None

    @property
    def inner_text(self) -> str:
        """Shorthand for `.elem.text.strip()`."""
        el = self.elem
        return (el.text or "").strip() if el is not None else ""

    def __getitem__(self, tag: str) -> "NodeProxy":
        """Allow p['child'] as an alias for p.child."""
        return self.__getattr__(tag)


# ── helper functions ───────────────────────────────────────────────────────
def strip_namespaces(root: ET._Element):
    """In-place removal of namespace URIs from element tags."""
    for el in root.iter():
        if isinstance(el.tag, str):
            if "}" in el.tag:
                el.tag = el.tag.split("}", 1)[1]  # remove namespace prefix


def _parse(source) -> ET._Element:
    """
    Parse *source* into an lxml Element.
    Supports: str path, file-like object, or raw XML string.
    Always strips namespaces.
    """
    if hasattr(source, "read"):
        data = source.read()
        root = ET.fromstring(
            data if isinstance(data, (bytes, bytearray)) else data.encode()
        )
    else:
        s = str(source)
        if "<" in s.lstrip()[:10]:
            root = ET.fromstring(s.encode())
        else:
            parser = ET.XMLParser(recover=True, huge_tree=True)
            root = ET.parse(s, parser).getroot()

    strip_namespaces(root)
    return root


def xml_node(source, headers: List[str], extractions: List[Row]) -> NodeProxy:
    """
    Public entry point.

    • *source XML string, file path, or file-like object
    • *headers*  list of CSV columns
    • *extractions* list to be populated with Row objects
    """
    root = _parse(source)
    print("root.tag:", root.tag)
    for el in root.iter():
        print(el.tag)
        break

    return NodeProxy([(root, Row())], headers, extractions)
