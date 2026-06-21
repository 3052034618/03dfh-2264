from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import uuid


@dataclass
class Recording:
    file_path: str
    file_name: str
    store: str
    consultant: str
    record_date: str
    record_time: str
    deal_status: str
    duration_seconds: int = 0
    transcript: str = ""
    category: str = "light"

    @property
    def is_dealt(self) -> bool:
        return self.deal_status == "dealt"


@dataclass
class QARule:
    rule_id: str
    name: str
    category: str
    weight: int
    description: str


@dataclass
class CheckItemResult:
    rule_id: str
    rule_name: str
    passed: bool
    score: int
    detail: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class RecordingQAResult:
    recording: Recording
    total_score: int = 100
    check_results: List[CheckItemResult] = field(default_factory=list)
    ban_word_hits: List[str] = field(default_factory=list)
    interruption_count: int = 0
    price_validity_clear: bool = True
    preop_mentioned: bool = True
    postop_mentioned: bool = True
    issues: List[str] = field(default_factory=list)

    @property
    def is_low_score(self) -> bool:
        from config import LOW_SCORE_THRESHOLD
        return self.total_score < LOW_SCORE_THRESHOLD


@dataclass
class BatchRecord:
    batch_id: str
    batch_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    rule_category: str = "light"
    deal_filter: str = "all"
    results: List[RecordingQAResult] = field(default_factory=list)
    source_dir: str = ""

    @classmethod
    def create(cls, name: str, rule_category: str, deal_filter: str, source_dir: str) -> "BatchRecord":
        return cls(
            batch_id=str(uuid.uuid4())[:8],
            batch_name=name,
            start_time=datetime.now(),
            rule_category=rule_category,
            deal_filter=deal_filter,
            source_dir=source_dir
        )


@dataclass
class StoreSummary:
    store_name: str
    total_count: int
    avg_score: float
    pass_rate: float
    issue_count: int
    top_issues: List[tuple] = field(default_factory=list)
