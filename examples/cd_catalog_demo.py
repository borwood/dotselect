from pathlib import Path
from xmlquery import xml_node, to_csv

INPUT_DIR = Path("input-xml")  # folder with XML docs
OUTPUT_CSV = Path("output.csv")

HEADERS = ["artist", "title"]  # adjust to your needs
rows = []  # master list for all docs


def extract_one(xml_text: str) -> None:
    """
    Parse *one* XML string, append its extracted Row(s) to the global *rows*.
    """
    (
        xml_node(xml_text, HEADERS, rows)
        .CATALOG.CD.where(lambda a, c, t: c.COUNTRY.text == "USA")
        .extract(lambda r, a, c, t: r.assign("artist", c.ARTIST.text))
        .extract(lambda r, a, c, t: r.assign("title", c.TITLE.text))
        .commit()
    )  # finalise rows


# iterate *.xml files in the folder
for path in INPUT_DIR.glob("cd*.xml"):
    print(f"Processing {path.name}")
    xml_text = path.read_text(encoding="utf-8")
    extract_one(xml_text)

# dump everything to CSV
to_csv(rows, HEADERS, OUTPUT_CSV)
print(f"\nDone. {len(rows)} rows written to {OUTPUT_CSV}")
