"""Focused branch-merge contract for the non-public prototype engine."""

import pytest

from dotselect._prototype import xml_node


XML = """\
<catalog>
  <record><title>First title</title><author>Ada</author></record>
  <record><title>Second title</title><author>Bruno</author></record>
</catalog>
"""


def test_merge_rejoins_independent_branches_by_original_record_in_source_order():
    """Title and author branches produce one flat row for each selected record."""
    headers = ["title", "author"]
    selections = []
    records = xml_node(XML, headers, selections).record

    titles = records.title.extract(
        lambda row, attributes, children, text: row.assign("title", text)
    )
    authors = records.author.extract(
        lambda row, attributes, children, text: row.assign("author", text)
    )

    (records + titles + authors).commit()

    assert selections == [
        {"title": "First title", "author": "Ada"},
        {"title": "Second title", "author": "Bruno"},
    ]


def test_merge_rejects_branches_from_unrelated_parses():
    """Row identity must not accidentally join independently parsed documents."""
    left = xml_node(XML, ["title"], []).record.title
    right = xml_node(XML, ["title"], []).record.title

    with pytest.raises(ValueError, match="different source"):
        left + right
