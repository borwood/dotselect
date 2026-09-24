"""Focused contract for the non-public replacement traversal engine.

These tests intentionally import the prototype directly.  They describe the
minimum query behavior it must provide before it can be considered for the
supported ``dotselect`` API.
"""

from io import StringIO

import pytest

from dotselect._prototype import xml_node
from dotselect._prototype.engine import Element


XML = """\
<catalog xmlns=\"urn:example:catalog\">
  <book id=\"first\"><title lang=\"en\">First book</title></book>
  <book id=\"second\"><title lang=\"en\">Second book</title></book>
</catalog>
"""


@pytest.mark.parametrize("source", [XML, StringIO(XML)])
def test_prototype_parses_xml_and_traverses_namespaced_children(source):
    """Raw XML and text streams support dot traversal after namespace stripping."""
    root = xml_node(source, [], [])

    books = root.book

    assert len(books._items) == 2
    assert [element.tag for element, _ in books._items] == ["book", "book"]


def test_prototype_where_exposes_attributes_and_child_proxy_text_and_attributes():
    """Predicates can inspect an element and its direct child proxy."""
    root = xml_node(XML, [], [])

    first_book = root.book.where(
        lambda attributes, children, text: (
            attributes["id"] == "first"
            and children.title.inner_text == "First book"
            and children.title.attributes["lang"] == "en"
            and text == ""
        )
    )

    assert len(first_book._items) == 1
    assert first_book._items[0][0].attributes == {"id": "first"}


def test_prototype_traversal_surfaces_adapter_errors_instead_of_returning_empty(monkeypatch):
    """An adapter failure is a defect, not a query with zero results."""
    root = xml_node(XML, [], [])

    def broken_findall(self, tag):
        raise RuntimeError(f"adapter cannot traverse {tag}")

    monkeypatch.setattr(Element, "findall", broken_findall)

    with pytest.raises(RuntimeError, match="adapter cannot traverse book"):
        root.book
