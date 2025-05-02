import uuid

class Row(dict):
    """Mutable CSV row with chainable .assign()."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._row_id = kwargs.pop("_row_id", uuid.uuid4().hex)

    def assign(self, key: str, value):
        self[key] = value
        return self  # fluency

    def copy(self):
        """Return a shallow copy of the row."""
        return Row(self, _row_id=self._row_id)
