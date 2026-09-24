from pathlib import Path

from dotselect import to_csv, xml_node


FIXTURES = Path(__file__).parent / "fixtures"


def test_dot_notation_merges_branches_into_rows(tmp_path):
    """Values found at different depths can become one record per book."""
    headers = ["title", "first_word"]
    rows = []

    root = xml_node(FIXTURES / "catalog.xml", headers, rows)
    books = root.book.where(lambda a, c, t: c.author.inner_text == "John Doe")
    titles = books.extract(lambda r, a, c, t: r.assign("title", c.title.inner_text))
    first_words = (
        books.chapter.page.extract(
            lambda r, a, c, t: r.assign("first_word", t.split()[0])
        )
    )

    (books + titles + first_words).commit()

    assert rows == [
        {"title": "Example Book", "first_word": "Hello"},
        {"title": "Second Book", "first_word": "First"},
    ]

    output = tmp_path / "books.csv"
    to_csv(rows, headers, output)
    assert output.read_text(encoding="utf-8") == (
        "title,first_word\nExample Book,Hello\nSecond Book,First\n"
    )


def test_synthetic_ccda_fixture_supports_namespace_stripping_and_branch_merging():
    """The fictional C-CDA fixture exercises a representative import path."""
    headers = ["first_name", "last_name", "mobile_phone"]
    rows = []

    root = xml_node(FIXTURES / "synthetic_ccda.xml", headers, rows)
    patient_role = root.recordTarget.patientRole
    name = patient_role.patient.name.extract(
        lambda r, a, c, t: r.assign("first_name", c.given.inner_text).assign(
            "last_name", c.family.inner_text
        )
    )
    mobile = patient_role.telecom.where(
        lambda a, c, t: a.get("use") == "MC"
    ).extract(
        lambda r, a, c, t: r.assign("mobile_phone", a["value"].removeprefix("tel:"))
    )

    (patient_role + name + mobile).commit()

    assert rows == [
        {
            "first_name": "Jeremy",
            "last_name": "Bates",
            "mobile_phone": "+1(555)-117-1234",
        }
    ]
