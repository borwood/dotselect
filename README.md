# dotselect

**dotselect** is a small Python DSL for compiling branching XML into flat rows.
It is designed for data-import pipelines where deeply nested documents need to
become CSV-shaped records—for example, C-CDA and healthcare-platform
interoperability feeds.

It is intentionally narrower than XPath: use dot notation to follow element
names, small callbacks to filter or extract values, and branch merging to
assemble one flat row from values found at different depths.

## Status

Experimental and pre-release. The current public API is backed by a retained
legacy engine while a more capable replacement is developed behind tests.
Expect API changes before an MVP release.

## Example

```python
from dotselect import to_csv, xml_node

headers = ["title", "first_word"]
rows = []

root = xml_node("catalog.xml", headers, rows)
books = root.book.where(lambda a, c, t: c.author.inner_text == "John Doe")

titles = books.extract(lambda r, a, c, t: r.assign("title", c.title.inner_text))
first_words = (
    books.chapter
    .page
    .extract(lambda r, a, c, t: r.assign("first_word", t.split()[0]))
)

(books + titles + first_words).commit()
to_csv(rows, headers, "books.csv")
```

The expression `root.book.chapter.page` follows XML structure directly. The
`+` operator merges branches that came from the same source record, letting
data found at different levels become one row.

## Development

Tests are the contract. Add or update a failing test before implementation,
then run:

```bash
python -m pytest
```

The repository includes a small catalog fixture and a fictional C-CDA fixture
for this purpose.
