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

headers, rows = ["title", "first word"], []

root = xml_node(xml_text, headers, rows)

# (
#     root.book.where(
#         lambda a, c, t: a["id"].startswith("1") and c["author"].text == "John Doe"
#     )
#     .extract(lambda r, a, c, t: r.assign("title", c["title"].text))
#     .chapter.where(lambda a, c, t: a["number"] == "1")
#     .page.where(lambda a, c, t: a["number"] == "1")
#     .extract(lambda r, a, c, t: r.assign("first word", t.split()[0]))
#     .commit()
# )

# TESTING NEW FORK AND MERGE------------------
print("root", len(root._items))
print("root.book", len(root.book._items))

books = root.book.where(lambda a, c, t: c["author"].inner_text == "John Doe")
print("books after where", len(books._items))

branch_title = books.extract(
    lambda r, a, c, t: r.assign("title", c["title"].inner_text)
)
branch_words = (
    books.chapter.where(lambda a, c, t: a.get("number") == "1")
    .page.where(lambda a, c, t: a.get("number") == "1")
    .extract(
        lambda r, a, c, t: r.assign("first word", (t or "").split()[0])
    )  # safe split
)

merged = branch_title + branch_words
print("merged", len(merged._items))

merged.commit()
print("rows", rows)

to_csv(rows, headers, "output.csv")
