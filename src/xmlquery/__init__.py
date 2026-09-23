"""Deprecated compatibility imports for the former ``xmlquery`` package."""

from dotselect import to_csv, xml_node
from dotselect._prototype import xml_node as xml_node2

__all__ = ["xml_node", "xml_node2", "to_csv"]
