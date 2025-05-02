from xmlquery import xml_node, to_csv

xml_text = """<?xml version="1.0"?>
<catalog>
  <book id="1001">
    <author>John Doe</author>
    <title>Example Book</title>
    <chapter number="1">
      <page number="1">Hello world, this is the first page.</page>
      <page number="2">Second page—ignored by the demo filter.</page>
    </chapter>
    <chapter number="2">
      <page number="1">Another chapter page (also ignored).</page>
    </chapter>
  </book>

  <book id="1002">
    <author>John Doe</author>
    <title>Second John Doe Title</title>
    <chapter number="1">
      <page number="1">First page content, will match too.</page>
    </chapter>
  </book>

  <book id="2001">
    <author>Jane Smith</author>
    <title>Other Author Book</title>
    <chapter number="1">
      <page number="1">This record never passes the id/author test.</page>
    </chapter>
  </book>
</catalog>
"""

headers, rows = ["title", "first word", "chapter words"], []

root = xml_node(xml_text, headers, rows)
trunk = root.catalog.book.where(lambda a,c,t: a["id"].startswith("1"))

# Branch 1 –  grab book-level title
branch1 = (trunk.extract(lambda r,a,c,t: r.assign("title", c["title"].text)))

# Branch 2 –  go deeper and capture words
branch2 = (trunk.chapter.where(lambda a,c,t: a["number"] == "1")
               .page.where(lambda a,c,t: a["number"] == "1")
               .extract(lambda r,a,c,t:
                        r.assign("first word", t.split()[0])
                         .assign("chapter words", len(t.split()))))

# Merge, then commit once
(branch1 + branch2).commit()

print(rows)
to_csv(rows, headers, "output.csv")
