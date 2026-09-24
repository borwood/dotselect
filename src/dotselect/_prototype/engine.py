from typing import Callable, List, Dict, Tuple, Union
import uuid
from lxml import etree as ET
from collections import defaultdict
from .row import Row

Predicate = Callable[[Dict[str, str], "NodeProxyChildren", str], bool]
Extraction = Callable[["Row", Dict[str, str], "NodeProxyChildren", str], bool]


class Element:
    """Abstract element class for future non-XML source support."""

    def __init__(self, source_object, source_type: str):
        self._source_object = source_object
        self._source_type = source_type

    def findall(self, tag: str) -> List["Element"]:
        match self._source_type:
            case "xml":
                return [
                    Element(child, self._source_type)
                    for child in self._source_object.iterfind(tag)
                ]
            case _:
                raise NotImplementedError(f"Source type {self._source_type} not supported")

    @property
    def tag(self) -> str:
        match self._source_type:
            case "xml":
                return self._source_object.tag
            case _:
                raise NotImplementedError(f"Source type {self._source_type} not supported")

    @property
    def attributes(self) -> dict:
        match self._source_type:
            case "xml":
                return dict(self._source_object.attrib)
            case _:
                raise NotImplementedError(f"Source type {self._source_type} not supported")

    @property
    def text(self) -> str:
        match self._source_type:
            case "xml":
                return (self._source_object.text or "").strip()
            case _:
                raise NotImplementedError(f"Source type {self._source_type} not supported")

    @property
    def children(self):
        match self._source_type:
            case "xml":
                return [
                    Element(child, self._source_type) for child in self._source_object
                ]
            case _:
                raise NotImplementedError(f"Source type {self._source_type} not supported")


class NodeProxySettings:
    """Settings object that informs the behavior of NodeProxy."""

    def __init__(self, row_mode: str = "split", logging: bool = False):
        self._row_mode = row_mode
        self._logging = logging

    def set_row_mode(self, new_value: str):
        self._row_mode = new_value
        return self

    def set_logging(self, new_value: bool):
        self._logging = new_value
        return self

    def partial_copy(
        self, new_row_mode: str | None = None, new_logging: bool | None = None
    ):
        if new_row_mode is None:
            new_row_mode = self._row_mode
        if new_logging is None:
            new_logging = self._logging
        return NodeProxySettings(row_mode=new_row_mode, logging=new_logging)


class NodeProxyChildren(Dict[str, "NodeProxy"]):
    """Direct children made available to predicate and extraction callbacks."""

    def __getattr__(self, tag: str) -> "NodeProxy":
        try:
            return self[tag]
        except KeyError as error:
            raise AttributeError(tag) from error


class NodeProxy:
    def __init__(
        self,
        parent: Union["NodeProxy", None],
        items: List[Tuple[Element, Row]],
        tag: str,
        keys: List[str],
        selections: List[Row],
        settings: NodeProxySettings | None = None,
        origin=None,
        allocates_lineage: bool = False,
        split_axis=None,
    ):
        self._parent = parent
        self._items = items
        self._tag = tag
        self._keys = keys
        self._selections = selections
        self._settings = settings or NodeProxySettings()
        self._origin = origin
        self._allocates_lineage = allocates_lineage
        self._split_axis = split_axis

        self._log(f"Touched: '{assemble_path(self)}'")

    def _datakey(self) -> str:
        datakey = ""
        position = 0
        for el, _ in self._items:
            datakey = hash((el.tag, position))
            position += 1

    def _log(self, log: str):
        if self._settings._logging == True:
            print("[DOTS LOG]", log)

    def _action_args(self, el: Element, row: Row, new_row_id: bool = False):
        a = el.attributes
        t = el.text

        grouped_children = defaultdict(list)
        for child in el.children:
            grouped_children[child.tag].append(child)

        c = NodeProxyChildren(
            {
                tag: NodeProxy(
                    parent=self,
                    items=[(ch, row.copy(new_id=new_row_id)) for ch in group],
                    tag=tag,
                    keys=self._keys,
                    selections=self._selections,
                    settings=self._settings,
                    origin=self._origin,
                    allocates_lineage=False,
                    split_axis=self._split_axis,
                )
                for tag, group in grouped_children.items()
            }
        )
        return a, c, t

    def flatten(self) -> "NodeProxy":
        self._log("Row Mode: 'flatten'")
        shared_rows = {}
        flattened_items = []
        for element, row in self._items:
            lineage_id = row._lineage_id
            if lineage_id not in shared_rows:
                shared_rows[lineage_id] = row.copy(variant_id=None)
            flattened_items.append((element, shared_rows[lineage_id]))
        return NodeProxy(
            parent=self._parent,
            items=flattened_items,
            tag=self._tag,
            keys=self._keys,
            selections=self._selections,
            settings=self._settings.partial_copy(new_row_mode="flatten"),
            origin=self._origin,
            allocates_lineage=self._allocates_lineage,
            split_axis=None,
        )

    def split(self) -> "NodeProxy":
        self._log("Row Mode: 'split'")
        return NodeProxy(
            parent=self._parent,
            items=self._items,
            tag=self._tag,
            keys=self._keys,
            selections=self._selections,
            settings=self._settings.partial_copy(new_row_mode="split"),
            origin=self._origin,
            allocates_lineage=self._allocates_lineage,
            split_axis=self._split_axis,
        )

    def __getattr__(self, tag: str) -> "NodeProxy":
        children = []
        child_groups = []
        has_repeated_children = False
        for el, row in self._items:
            matches = el.findall(tag)
            has_repeated_children |= len(matches) > 1
            child_groups.append((row, matches))

        starts_split_axis = (
            self._settings._row_mode == "split"
            and not self._allocates_lineage
            and self._split_axis is None
            and has_repeated_children
        )
        split_axis = (
            f"{assemble_path(self)}/{tag}" if starts_split_axis else self._split_axis
        )

        for row, matches in child_groups:
            for position, ch in enumerate(matches):
                new_id = self._settings._row_mode != "flatten"
                lineage_id = (
                    uuid.uuid4().hex if self._allocates_lineage else None
                )
                variant_id = (split_axis, position) if starts_split_axis else row._variant_id
                if self._settings._row_mode == "flatten" and not self._allocates_lineage:
                    child_row = row
                else:
                    child_row = row.copy(
                        new_id=new_id,
                        lineage_id=lineage_id,
                        variant_id=variant_id,
                    )
                children.append((ch, child_row))

        return NodeProxy(
            self,
            children,
            tag,
            self._keys,
            self._selections,
            self._settings,
            self._origin,
            False,
            split_axis,
        )

    def __getitem__(self, tag: str) -> "NodeProxy":
        return self.__getattr__(tag)

    def __truediv__(self, tag: str) -> "NodeProxy":
        """Allow ``proxy / \"child\"`` as an alias for dot traversal."""
        return self.__getattr__(tag)

    @property
    def elem(self) -> Element | None:
        """Return the first selected element for ad-hoc inspection."""
        return self._items[0][0] if self._items else None

    @property
    def attributes(self) -> Dict[str, str]:
        """Attributes belonging to the first selected element.

        Predicate child proxies may represent multiple siblings; scalar helpers
        deliberately use the first one so callers can inspect a direct child
        without reaching through the internal item list.
        """
        return self._items[0][0].attributes if self._items else {}

    @property
    def inner_text(self) -> str:
        """Text belonging to the first selected element."""
        return self._items[0][0].text if self._items else ""

    def where(self, fn) -> "NodeProxy":
        kept_items = []
        for el, row in self._items:
            a, c, t = self._action_args(el, row)
            if fn(a, c, t):
                kept_items.append((el, row))
        return NodeProxy(
            self,
            kept_items,
            self._tag,
            self._keys,
            self._selections,
            self._settings,
            self._origin,
            self._allocates_lineage,
            self._split_axis,
        )

    def extract(self, fn: Extraction) -> "NodeProxy":
        """Populate each current row with an extraction callback.

        The callback receives the current row followed by the same element
        context made available to :meth:`where`.
        """
        for el, row in self._items:
            a, c, t = self._action_args(el, row)
            fn(row, a, c, t)
        return self

    def select(self, fn: Extraction) -> "NodeProxy":
        """Temporary non-public alias for :meth:`extract`."""
        return self.extract(fn)

    def commit(self) -> "NodeProxy":
        """Append normalized snapshots of the rows represented by this proxy."""
        committed_lineages = set()
        for _, row in self._items:
            if self._settings._row_mode == "flatten":
                if row._lineage_id in committed_lineages:
                    continue
                committed_lineages.add(row._lineage_id)
            self._selections.append(Row({key: row.get(key, "") for key in self._keys}))
        return self

    def __add__(self, other: "NodeProxy") -> "NodeProxy":
        """Merge independently extracted branches without mutating either one."""
        if not isinstance(other, NodeProxy):
            return NotImplemented
        if self._allocates_lineage or other._allocates_lineage:
            raise ValueError("Cannot merge a document root proxy")
        if self._origin is not other._origin:
            raise ValueError("Cannot merge branches from different source documents")
        if self._keys != other._keys:
            raise ValueError("Cannot merge proxies with different headers")
        if (
            self._split_axis is not None
            and other._split_axis is not None
            and self._split_axis != other._split_axis
        ):
            raise ValueError("Cannot merge independently split axes")
        if any(
            row._lineage_id is None for _, row in [*self._items, *other._items]
        ):
            raise ValueError("Cannot merge rows without source-record lineage")

        rows_by_lineage = {}
        for element, row in [*self._items, *other._items]:
            rows_by_lineage.setdefault(row._lineage_id, []).append((element, row))

        merged_items = []
        for source_rows in rows_by_lineage.values():
            variants = []
            for _, row in source_rows:
                if row._variant_id is not None and row._variant_id not in variants:
                    variants.append(row._variant_id)

            if not variants:
                element, row = source_rows[0]
                merged = row.copy()
                for _, other_row in source_rows[1:]:
                    merged.update(other_row)
                merged_items.append((element, merged))
                continue

            for variant_id in variants:
                variant_rows = [
                    (element, row)
                    for element, row in source_rows
                    if row._variant_id in (None, variant_id)
                ]
                element, row = variant_rows[0]
                merged = row.copy(variant_id=variant_id)
                for _, other_row in variant_rows[1:]:
                    merged.update(other_row)
                merged_items.append((element, merged))

        return NodeProxy(
            parent=None,
            items=merged_items,
            tag=self._tag,
            keys=self._keys,
            selections=self._selections,
            settings=self._settings,
            origin=self._origin,
            allocates_lineage=False,
            split_axis=self._split_axis or other._split_axis,
        )


def strip_namespaces(root: ET._Element):
    """In-place removal of namespace URIs from element tags."""
    for el in root.iter():
        if isinstance(el.tag, str):
            if "}" in el.tag:
                el.tag = el.tag.split("}", 1)[1]


def _parse(source) -> ET._Element:
    """Parse an XML string, path, or file-like object and strip namespaces."""
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


def xml_node(source, keys: List[str], selections: List[Row]) -> NodeProxy:
    root = _parse(source)
    origin = object()

    return NodeProxy(
        parent=None,
        items=[(Element(root, "xml"), Row(origin=origin))],
        tag=root.tag,
        keys=keys,
        selections=selections,
        origin=origin,
        allocates_lineage=True,
        split_axis=None,
    )


def assemble_path(node_proxy: "NodeProxy") -> str:
    tags: List[str] = [node_proxy._tag]

    def parent_tag(child: "NodeProxy"):
        done = child._parent == None
        if not done:
            tags.append(child._parent._tag)
            parent_tag(child=child._parent)

    parent_tag(node_proxy)
    return "/".join(str(tag) for tag in reversed(tags))
