from pathlib import Path
from xmlquery import xml_node, to_csv


input_dir = Path(__file__).resolve().parent.parent / "input-xml"
print(f"Looking in: {input_dir}")

for f in input_dir.glob("*"):
    print(f.name)

# Load the input XML
# Always resolve relative to project root
project_root = Path(__file__).resolve().parent.parent
input_path = project_root / "input-xml" / "demo_ccda1.xml"
with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
    raw_text = f.read()

# Isolate the ClinicalDocument portion
end_tag = "</ClinicalDocument>"
xml_text = raw_text.split(end_tag)[0] + end_tag if end_tag in raw_text else raw_text
# print(xml_text[:50])  # Print the first 50 characters for debugging
# Output CSV path
output_path = Path(__file__).parent / "ccda1_output.csv"

# Define target columns and output row container
headers = ["id count", "unique row"]
rows = []

# Chainquery pipeline
root = xml_node(xml_text, headers, rows)
# print(root._items)
(
    root.recordTarget.patientRole.where2(
        lambda a, c, t: True
    )  # if there were multi patientRole... would you split c accordingly?
    .extract(lambda r, a, c, t: r.assign("id count", len(c.id._items)))
    .id.extract(lambda r, a, c, t: r.assign("unique row", True))
    .commit()
)
print(rows)
# Write output
to_csv(rows, headers, output_path)
print(f"✓ Extracted {len(rows)} row(s) to {output_path}")
