import uuid


_UNSET = object()


class Row(dict):
    shared_data = []

    def __init__(
        self,
        *args,
        row_id=None,
        sealed=False,
        origin=None,
        lineage_id=None,
        variant_id=None,
        **kw,
    ):
        super().__init__(*args, **kw)
        self._row_id = row_id or uuid.uuid4().hex
        self._sealed = sealed
        self._origin = origin
        self._lineage_id = lineage_id
        self._variant_id = variant_id

        # TODO: implement shared data dict with path hash keys
        # such that we don't have to copy row data
        self._shared_data = Row.shared_data

    def assign(self, key, value):
        """Store a value and return this row for fluent extraction callbacks."""
        self[key] = value
        return self

    def extend(self, key, value, *, delimiter: str = ", "):
        """Append a scalar value using an explicit output delimiter."""
        if key in self:
            self[key] = f"{self[key]}{delimiter}{value}"
        else:
            self[key] = value
        return self

    def copy(self, new_id: bool = False, lineage_id=None, variant_id=_UNSET):
        rid = uuid.uuid4().hex if new_id else self._row_id
        return Row(
            self,
            row_id=rid,
            sealed=self._sealed,
            origin=self._origin,
            lineage_id=self._lineage_id if lineage_id is None else lineage_id,
            variant_id=self._variant_id if variant_id is _UNSET else variant_id,
        )

    # def __getitem__
