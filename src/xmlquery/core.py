from __future__ import annotations
from typing import Callable, List, Dict, Tuple

from lxml import etree as ET
from .row import Row

Predicate = Callable[[Dict[str, str], "NodeProxyChildren", str], bool]
Extractor = Callable[[Row, Dict[str, str], "NodeProxyChildren", str], None]


class NodeProxyChildren(dict):
    """Maps child tag names to single-element NodeProxy wrappers."""


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
        """
        Descend into child elements named *tag*.
        Each child is paired with a copy of its parent's Row so that sibling
        branches cannot overwrite each other's data.
        """
        children: List[Tuple[ET._Element, Row]] = []
        for el, row in self._items:
            for child in el.iterfind(tag):
                children.append((child, row.copy()))
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


    # ── filtering ──────────────────────────────────────────────────────────
    def where(self, fn: Predicate) -> "NodeProxy":
        """
        Keep only the element/row pairs for which *fn* returns True.
        fn(signature): (attributes, children_proxy, text) -> bool
        """
        kept: List[Tuple[ET._Element, Row]] = []
        for el, row in self._items:
            a = el.attrib
            c = NodeProxyChildren(
                {
                    ch.tag: NodeProxy(
                        [(ch, row.copy())], self.headers, self.extractions
                    )
                    for ch in el
                }
            )
            t = (el.text or "").strip()
            if fn(a, c, t):
                kept.append((el, row))
        return NodeProxy(kept, self.headers, self.extractions)

    # ── extraction ─────────────────────────────────────────────────────────
    def extract(self, fn: Extractor) -> "NodeProxy":
        """
        Mutate the Row for every element/row pair using user-supplied *fn*.
        fn(signature): (row, attributes, children_proxy, text) -> None
        """
        for el, row in self._items:
            a = el.attrib
            c = NodeProxyChildren(
                {
                    ch.tag: NodeProxy([(ch, row)], self.headers, self.extractions)
                    for ch in el
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
    def text(self) -> str:
        """Shorthand for `.elem.text.strip()`."""
        el = self.elem
        return (el.text or "").strip() if el is not None else ""

    def __getitem__(self, tag: str) -> "NodeProxy":
        """Allow p['child'] as an alias for p.child."""
        return self.__getattr__(tag)


# ── helper functions ───────────────────────────────────────────────────────


def _parse(source) -> ET._Element:
    """
    Parse *source* into an lxml Element.

    *source* may be:
      • a str/Path pointing to a file,
      • a file-like object,
      • a str containing raw XML (with or without encoding declaration).
    """
    if hasattr(source, "read"):
        data = source.read()
        return ET.fromstring(
            data if isinstance(data, (bytes, bytearray)) else data.encode()
        )
    s = str(source)
    if "<" in s.lstrip()[:10]:
        return ET.fromstring(s.encode())
    parser = ET.XMLParser(recover=True, huge_tree=True)
    return ET.parse(s, parser).getroot()


def xml_node(source, headers: List[str], extractions: List[Row]) -> NodeProxy:
    """
    Public entry point.

    • *source XML string, file path, or file-like object
    • *headers*  list of CSV columns
    • *extractions* list to be populated with Row objects
    """
    root = _parse(source)
    return NodeProxy([(root, Row())], headers, extractions)
