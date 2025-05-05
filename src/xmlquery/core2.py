from typing import Callable, List, Dict, Tuple
from lxml import etree as ET
from collections import defaultdict


class Row(dict):
    pass


class NodeProxy:

    def __init__(
        self,
        items: List[Tuple[ET._Element, Row]],
        keys: List[str],
        extractions: List[Row],
    ):
        self._items = items
        self.keys = keys
        self.extractions = extractions

    # --- traversal ---
    def __getattr__(self, tag: str) -> "NodeProxy":
        children = []
        for el, row in self._items:
            fresh = not row._sealed
            for child in el.iterfind(tag):
                child_row = row.copy(new_id=fresh)
                child_row._sealed = True
                children.append((child, child_row))
        return NodeProxy(items=children, keys=self.keys, extractions=self.extractions)

    def __getitem__(self, key: str) -> "NodeProxy":
        return self.__getattr__(key)

    def __where(self, fn) -> "NodeProxy":
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

    def _where(self, fn) -> "NodeProxy":
        """
        Filter the current node set based on a predicate function.
        """
        filtered_items = []
        for el, row in self._items:
            attributes = el.attrib
            text = (el.text or "").strip()
            if fn(attributes, self, text):
                filtered_items.append((el, row))
        return NodeProxy(
            items=filtered_items, keys=self.keys, extractions=self.extractions
        )
