"""Order-independent isolated retrieval store."""

from dm_assistant_core.domain import RetrievalQuery, RetrievalRecord


class InMemoryRetrievalRepository:
    def __init__(self, records: tuple[RetrievalRecord, ...]) -> None:
        self._records = tuple(sorted(records, key=lambda record: record.record_id))

    def relevant_records(self, _query: RetrievalQuery) -> tuple[RetrievalRecord, ...]:
        return self._records
