"""Focused cardinality contract for repeated XML children in the prototype."""

import pytest

from dotselect._prototype import xml_node
from dotselect._prototype.row import Row


XML = """\
<people>
  <person id="1"><name>Ada</name><phone>111</phone><phone>222</phone><email>ada@example.test</email><email>ada@work.test</email></person>
  <person id="2"><name>Bruno</name><phone>333</phone><email>bruno@example.test</email></person>
</people>
"""


def _people(headers, selections):
    return xml_node(XML, headers, selections).person.extract(
        lambda row, attributes, children, text: row.assign("person_id", attributes["id"]).assign(
            "name", children.name.inner_text
        )
    )


def test_default_repeated_child_selection_splits_rows_in_document_order():
    """Each phone occurrence becomes a flat row retaining its person's values."""
    headers = ["person_id", "name", "phone"]
    selections = []
    phones = _people(headers, selections).phone.extract(
        lambda row, attributes, children, text: row.assign("phone", text)
    )

    phones.commit()

    assert selections == [
        {"person_id": "1", "name": "Ada", "phone": "111"},
        {"person_id": "1", "name": "Ada", "phone": "222"},
        {"person_id": "2", "name": "Bruno", "phone": "333"},
    ]


def test_row_extend_aggregates_values_in_document_order_with_the_given_delimiter():
    """Flatten callbacks explicitly choose how repeated scalar values are joined."""
    row = Row()

    assert row.extend("phones", "111", delimiter="; ") is row
    assert row.extend("phones", "222", delimiter="; ") is row

    assert row == {"phones": "111; 222"}


def test_flatten_produces_one_row_per_source_and_extend_accumulates_values():
    """Flattening repeated phones retains one person row and joins in XML order."""
    headers = ["person_id", "name", "phones"]
    selections = []
    phones = _people(headers, selections).phone.flatten().extract(
        lambda row, attributes, children, text: row.extend(
            "phones", text, delimiter="; "
        )
    )

    phones.commit()

    assert selections == [
        {"person_id": "1", "name": "Ada", "phones": "111; 222"},
        {"person_id": "2", "name": "Bruno", "phones": "333"},
    ]


def test_flattened_assign_is_last_write_wins_with_one_row_per_source():
    """Assign remains scalar: flattening does not silently invent aggregation."""
    headers = ["person_id", "phone"]
    selections = []
    phones = _people(headers, selections).phone.flatten().extract(
        lambda row, attributes, children, text: row.assign("phone", text)
    )

    phones.commit()

    assert selections == [
        {"person_id": "1", "phone": "222"},
        {"person_id": "2", "phone": "333"},
    ]


def test_merging_independently_split_sibling_axes_is_rejected():
    """The MVP does not infer zip or Cartesian semantics for sibling lists."""
    headers = ["person_id", "phone", "email"]
    people = _people(headers, [])
    phones = people.phone.split().extract(
        lambda row, attributes, children, text: row.assign("phone", text)
    )
    emails = people.email.split().extract(
        lambda row, attributes, children, text: row.assign("email", text)
    )

    with pytest.raises(ValueError, match="split axes"):
        phones + emails
