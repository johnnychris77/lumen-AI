"""
Lightweight stub for MongoDB so the API can run without a real Mongo instance.

We keep the same public symbols (`inspections`, `ensure_indexes`) that other
modules import, but implement them as no-ops / empty results.
"""

from typing import Any


class _DummyInsertResult:
    def __init__(self, inserted_id=None):
        self.inserted_id = inserted_id


class _DummyCursor:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _DummyCollection:
    async def insert_one(self, doc: Any) -> _DummyInsertResult:
        return _DummyInsertResult(inserted_id=None)

    def find(self, *args, **kwargs) -> _DummyCursor:
        return _DummyCursor()


inspections = _DummyCollection()


async def ensure_indexes() -> None:
    # No-op stub so startup won't break
    return None
