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
    ):
        self._parent = parent
        self._items = items
        self._tag = tag
        self._keys = keys
        self._selections = selections
        self._settings = settings or NodeProxySettings()
        self._origin = origin
        self._allocates_lineage = allocates_lineage

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
                )
                for tag, group in grouped_children.items()
            }
        )
        return a, c, t

    def flatten(self) -> "NodeProxy":
        self._log("Row Mode: 'flatten'")
        return NodeProxy(
            parent=self._parent,
            items=self._items,
            tag=self._tag,
            keys=self._keys,
            selections=self._selections,
            settings=self._settings.partial_copy(new_row_mode="flatten"),
            origin=self._origin,
            allocates_lineage=self._allocates_lineage,
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
        )

    def __getattr__(self, tag: str) -> "NodeProxy":
        children = []
        for el, row in self._items:
            for ch in el.findall(tag):
                new_id = self._settings._row_mode != "flatten"
                lineage_id = (
                    uuid.uuid4().hex if self._allocates_lineage else None
                )
                child_row = row.copy(new_id=new_id, lineage_id=lineage_id)
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
        )

    def __getitem__(self, tag: str) -> "NodeProxy":
        return self.__getattr__(tag)

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
        for _, row in self._items:
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
        if any(
            row._lineage_id is None for _, row in [*self._items, *other._items]
        ):
            raise ValueError("Cannot merge rows without source-record lineage")

        merged_by_lineage = {}
        for element, row in [*self._items, *other._items]:
            lineage_id = row._lineage_id
            if lineage_id not in merged_by_lineage:
                merged_by_lineage[lineage_id] = (element, row.copy())
            else:
                merged_by_lineage[lineage_id][1].update(row)

        return NodeProxy(
            parent=None,
            items=list(merged_by_lineage.values()),
            tag=self._tag,
            keys=self._keys,
            selections=self._selections,
            settings=self._settings,
            origin=self._origin,
            allocates_lineage=False,
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
