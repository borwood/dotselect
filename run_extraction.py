from pathlib import Path
from xmlquery import xml_node, to_csv

INPUT_DIR  = Path("input-xml")           # folder with XML docs
OUTPUT_CSV = Path("output.csv")

HEADERS = ["title", "first word"]        # adjust to your needs
rows = []                                # master list for all docs

def extract_one(xml_text: str) -> None:
    """
    Parse *one* XML string, append its extracted Row(s) to the global *rows*.
    """
    (xml_node(xml_text, HEADERS, rows)          # source, headers, target list
        .book.where(lambda a, c, t:                          # filter books
                    a.get("id", "").startswith("1") and
                    c["author"].text == "John Doe")
        .extract(lambda r, a, c, t:                         # capture title
                 r.assign("title", c["title"].text))
        .chapter.where(lambda a, c, t: a.get("number") == "1")
        .page.where(lambda a, c, t: a.get("number") == "1")
        .extract(lambda r, a, c, t:                        # capture first word
                 r.assign("first word", t.split()[0]))
        .commit())                                         # finalise rows

# iterate *.xml files in the folder
for path in INPUT_DIR.glob("*.xml"):
    print(f"Processing {path.name}")
    xml_text = path.read_text(encoding="utf-8")
    extract_one(xml_text)

# dump everything to CSV
to_csv(rows, HEADERS, OUTPUT_CSV)
print(f"\nDone. {len(rows)} rows written to {OUTPUT_CSV}")
