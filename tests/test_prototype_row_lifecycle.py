"""Focused row-lifecycle contract for the non-public prototype engine."""

from dotselect._prototype import xml_node
from dotselect._prototype.row import Row


XML = """\
<catalog>
  <book id="first"><title>First book</title></book>
  <book id="second"><title>Second book</title></book>
</catalog>
"""


def test_row_assign_is_chainable_and_copies_preserve_or_fork_identity():
    """Rows are independent mappings, with an explicit choice to fork identity."""
    row = Row()

    assert row.assign("title", "First book") is row
    assert row == {"title": "First book"}

    same_source = row.copy()
    forked_source = row.copy(new_id=True)

    assert same_source is not row
    assert same_source == row
    assert same_source._row_id == row._row_id
    assert forked_source._row_id != row._row_id

    same_source.assign("edition", "first")
    assert "edition" not in row


def test_extract_passes_row_attributes_children_and_text_to_callback():
    """Extraction callbacks can populate the current row from an XML element."""
    selections = []
    books = xml_node(XML, ["id", "title"], selections).book
    observed = []

    extracted = books.extract(
        lambda row, attributes, children, text: (
            observed.append((row, attributes, children.title.inner_text, text)),
            row.assign("id", attributes["id"]).assign("title", children.title.inner_text),
        )
    )

    assert extracted is books
    assert [(attributes, title, text) for _, attributes, title, text in observed] == [
        ({"id": "first"}, "First book", ""),
        ({"id": "second"}, "Second book", ""),
    ]
    assert [row for row, _, _, _ in observed] == [row for _, row in books._items]
    assert [row for _, row in books._items] == [
        {"id": "first", "title": "First book"},
        {"id": "second", "title": "Second book"},
    ]


def test_commit_appends_one_normalized_selection_per_current_item():
    """Commit materializes current rows and fills every declared missing header."""
    headers = ["id", "title", "missing"]
    selections = []
    books = xml_node(XML, headers, selections).book.extract(
        lambda row, attributes, children, text: row.assign("id", attributes["id"]).assign(
            "title", children.title.inner_text
        )
    )

    assert books.commit() is books
    assert selections == [
        {"id": "first", "title": "First book", "missing": ""},
        {"id": "second", "title": "Second book", "missing": ""},
    ]
