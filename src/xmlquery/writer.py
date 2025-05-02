# src/xmlquery/writer.py
"""
CSV export utilities for xmlquery.
"""

from __future__ import annotations
from pathlib import Path
import csv
from typing import Iterable, List, Dict, Union, TextIO

RowLike = Dict[str, str]


def to_csv(
    rows: Iterable[RowLike],
    headers: List[str],
    out: Union[str, Path, TextIO],
    *,
    newline: str = "",
    encoding: str = "utf-8",
) -> None:
    """
    Dump *rows* (iterable of dict-like objects) to *out* using *headers* for
    column order.

    Parameters
    ----------
    rows     iterable of dicts   • the data you collected with xmlquery
    headers  list[str]           • column order / header row
    out      str | Path | file  • filename **or** open file-object
    newline  str                 • csv module newline handling (default "")
    encoding str                 • file encoding when *out* is a path
    """
    # Accept either a path or an already-open file object
    must_close = False
    if isinstance(out, (str, Path)):
        fp: TextIO = open(out, "w", newline=newline, encoding=encoding)
        must_close = True
    else:
        fp = out  # Assume file-like object already opened in text mode

    writer = csv.DictWriter(fp, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    for row in rows:
        # normalise missing headers to empty string
        writer.writerow({h: row.get(h, "") for h in headers})

    if must_close:
        fp.close()
