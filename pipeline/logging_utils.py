"""Lightweight structured logger for the daily pipeline.

Collects one JSON-serialisable record per attempt (news fetch, Claude
call, Pollinations call) so the full methodological trace of a run can
be written to archive/<date>/exchange_log.json.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


@dataclass
class ExchangeLogger:
    records: dict = field(default_factory=lambda: {"news": [], "claude": [], "pollinations": []})

    def log(self, channel: str, **entry) -> None:
        entry.setdefault("timestamp", utc_now_iso())
        self.records.setdefault(channel, []).append(entry)

    def to_dict(self) -> dict:
        return self.records
