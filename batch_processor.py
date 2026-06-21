import sys
import time
from datetime import datetime
from typing import List, Callable, Optional
from models import Recording, RecordingQAResult, BatchRecord
from qa_engine import QARuleEngine
from importer import RecordingImporter


class ProgressBar:
    def __init__(self, total: int, prefix: str = "进度", size: int = 40):
        self.total = total
        self.prefix = prefix
        self.size = size
        self.current = 0
        self.start_time = time.time()

    def update(self, current: int, info: str = ""):
        self.current = current
        progress = current / self.total if self.total > 0 else 0
        filled = int(self.size * progress)
        bar = "█" * filled + "░" * (self.size - filled)
        percent = progress * 100

        elapsed = time.time() - self.start_time
        if current > 0:
            eta = elapsed * (self.total - current) / current
            eta_str = f" 剩余: {self._format_time(eta)}"
        else:
            eta_str = ""

        elapsed_str = f" 用时: {self._format_time(elapsed)}"

        line = f"\r{self.prefix}: |{bar}| {percent:.1f}% ({current}/{self.total}){elapsed_str}{eta_str}"
        if info:
            line += f"  {info}"

        sys.stdout.write(line)
        sys.stdout.flush()

    def finish(self):
        self.update(self.total)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}小时{mins}分"


class BatchProcessor:
    def __init__(self):
        self.importer = RecordingImporter()
        self.current_batch: Optional[BatchRecord] = None
        self.progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback

    def create_batch(self, name: str, rule_category: str, deal_filter: str,
                     source_dir: str) -> BatchRecord:
        batch = BatchRecord.create(
            name=name,
            rule_category=rule_category,
            deal_filter=deal_filter,
            source_dir=source_dir
        )
        self.current_batch = batch
        return batch

    def run_batch(self, batch: BatchRecord, recordings: List[Recording]) -> BatchRecord:
        engine = QARuleEngine(category=batch.rule_category)
        total = len(recordings)
        batch.total_count = total
        batch.results = []
        passed = 0
        failed = 0

        progress = ProgressBar(total, prefix="质检进度")

        for i, recording in enumerate(recordings, 1):
            result = engine.analyze(recording)
            batch.results.append(result)

            if result.is_low_score:
                failed += 1
            else:
                passed += 1

            info = f"[{recording.store} - {recording.consultant}] 得分: {result.total_score}"
            progress.update(i, info)

            if self.progress_callback:
                self.progress_callback(i, total, recording, result)

            time.sleep(0.05)

        progress.finish()

        batch.passed_count = passed
        batch.failed_count = failed
        batch.end_time = datetime.now()

        return batch

    def process_directory(self, name: str, directory: str, category: str = "light",
                          deal_filter: str = "all") -> BatchRecord:
        recordings = self.importer.import_from_directory(directory, category, deal_filter)

        if not recordings:
            batch = self.create_batch(name, category, deal_filter, directory)
            batch.end_time = datetime.now()
            return batch

        batch = self.create_batch(name, category, deal_filter, directory)
        batch = self.run_batch(batch, recordings)

        return batch

    def get_low_score_recordings(self, batch: BatchRecord) -> List[RecordingQAResult]:
        return [r for r in batch.results if r.is_low_score]

    def get_issue_summary(self, batch: BatchRecord) -> dict:
        issue_counts = {}
        for result in batch.results:
            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return {
            "total_issues": sum(issue_counts.values()),
            "issue_types": len(issue_counts),
            "top_issues": sorted_issues[:10]
        }
