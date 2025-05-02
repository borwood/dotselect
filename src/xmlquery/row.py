class Row(dict):
    """Mutable CSV row with chainable .assign()."""

    def assign(self, key: str, value):
        self[key] = value
        return self  # fluency

    def copy(self):
        """Return a shallow copy of the row."""
        return Row(self)
