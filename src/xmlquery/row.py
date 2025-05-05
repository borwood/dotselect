import uuid


class Row(dict):
    """
    _row_id  = persistent id for merging
    _sealed  = after the first sibling-split, further copies keep the id
    """

    def __init__(self, *args, _row_id=None, _sealed=False, **kw):
        super().__init__(*args, **kw)
        self._row_id = _row_id or uuid.uuid4().hex
        self._sealed = _sealed

    def assign(self, key, value, *, delimiter=None):
        """
        Store *value* at *key* and return self so callers can chain:
            r.assign("col1", v1).assign("col2", v2)
        """
        if delimiter is not None:
            if isinstance(value, list):
                flat = []
                for v in value:
                    if isinstance(v, list):
                        flat.extend(v)
                    else:
                        flat.append(v)
                value = delimiter.join(str(v) for v in flat)

        self[key] = value
        return self

    def extend(self, key: str, value):
        """Append a value to a list under this key. Initializes the list if needed."""
        if key not in self or not isinstance(self[key], list):
            self[key] = []
        if isinstance(value, list):
            self[key].extend(value)
        else:
            self[key].append(value)
        return self

    def copy(self, *, new_id: bool = False) -> "Row":
        # Preserve or refresh the id
        rid = uuid.uuid4().hex if new_id else self._row_id
        return Row(self, _row_id=rid, _sealed=self._sealed)
