"""Prototype-only parity checks for the supported XML extraction scenarios."""

from pathlib import Path

from dotselect._prototype import xml_node


FIXTURES = Path(__file__).parent / "fixtures"


def test_prototype_matches_catalog_branch_merge_contract():
    """The prototype produces the supported catalog rows through its own entry point."""
    headers = ["title", "first_word"]
    rows = []

    root = xml_node(FIXTURES / "catalog.xml", headers, rows)
    books = root.book.where(lambda a, c, t: c.author.inner_text == "John Doe")
    titles = books.extract(lambda r, a, c, t: r.assign("title", c.title.inner_text))
    first_words = books.chapter.page.extract(
        lambda r, a, c, t: r.assign("first_word", t.split()[0])
    )

    (books + titles + first_words).commit()

    assert rows == [
        {"title": "Example Book", "first_word": "Hello"},
        {"title": "Second Book", "first_word": "First"},
    ]


def test_prototype_matches_namespaced_synthetic_ccda_contract():
    """The prototype preserves the supported fictional C-CDA extraction result."""
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
