import os
import json
from collections import defaultdict
from typing import List, Dict
from datetime import datetime
from models import BatchRecord, RecordingQAResult, StoreSummary
from config import EXPORTS_DIR, RECORDS_DIR, RULE_CATEGORIES, DEAL_STATUS
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class ResultAnalyzer:
    def __init__(self):
        pass

    def get_store_summaries(self, batch: BatchRecord) -> List[StoreSummary]:
        store_data = defaultdict(list)
        for result in batch.results:
            store_data[result.recording.store].append(result)

        summaries = []
        for store_name, results in store_data.items():
            total = len(results)
            avg_score = sum(r.total_score for r in results) / total if total > 0 else 0
            pass_count = sum(1 for r in results if not r.is_low_score)
            pass_rate = pass_count / total if total > 0 else 0
            issue_count = sum(len(r.issues) for r in results)

            issue_counts = defaultdict(int)
            for r in results:
                for issue in r.issues:
                    issue_counts[issue] += 1

            top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            summaries.append(StoreSummary(
                store_name=store_name,
                total_count=total,
                avg_score=round(avg_score, 1),
                pass_rate=round(pass_rate * 100, 1),
                issue_count=issue_count,
                top_issues=top_issues
            ))

        summaries.sort(key=lambda x: x.avg_score)
        return summaries

    def get_top_issues(self, batch: BatchRecord, top_n: int = 10) -> List[tuple]:
        issue_counts = defaultdict(int)
        for result in batch.results:
            for issue in result.issues:
                issue_counts[issue] += 1

        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_issues[:top_n]

    def get_low_score_list(self, batch: BatchRecord) -> List[RecordingQAResult]:
        low_scores = [r for r in batch.results if r.is_low_score]
        low_scores.sort(key=lambda x: x.total_score)
        return low_scores

    def get_category_stats(self, batch: BatchRecord) -> dict:
        total = len(batch.results)
        passed = batch.passed_count
        failed = batch.failed_count
        avg_score = sum(r.total_score for r in batch.results) / total if total > 0 else 0

        category_stats = defaultdict(lambda: {"count": 0, "score_sum": 0})

        for r in batch.results:
            for check in r.check_results:
                category_stats[check.rule_name]["count"] += 1
                category_stats[check.rule_name]["score_sum"] += check.score

        stats = []
        for name, data in category_stats.items():
            avg = data["score_sum"] / data["count"] if data["count"] > 0 else 0
            stats.append({
                "name": name,
                "avg_score": round(avg, 1),
                "count": data["count"]
            })

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "avg_score": round(avg_score, 1),
            "category_stats": stats
        }


class RecordManager:
    def __init__(self):
        self.records_dir = RECORDS_DIR
        os.makedirs(self.records_dir, exist_ok=True)

    def save_batch(self, batch: BatchRecord) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{batch.batch_id}_{timestamp}.json"
        filepath = os.path.join(self.records_dir, filename)

        data = {
            "batch_id": batch.batch_id,
            "batch_name": batch.batch_name,
            "start_time": batch.start_time.isoformat(),
            "end_time": batch.end_time.isoformat() if batch.end_time else None,
            "total_count": batch.total_count,
            "passed_count": batch.passed_count,
            "failed_count": batch.failed_count,
            "rule_category": batch.rule_category,
            "deal_filter": batch.deal_filter,
            "source_dir": batch.source_dir,
            "results": [self._serialize_result(r) for r in batch.results]
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def _serialize_result(self, result: RecordingQAResult) -> dict:
        return {
            "file_path": result.recording.file_path,
            "file_name": result.recording.file_name,
            "store": result.recording.store,
            "consultant": result.recording.consultant,
            "record_date": result.recording.record_date,
            "record_time": result.recording.record_time,
            "deal_status": result.recording.deal_status,
            "duration_seconds": result.recording.duration_seconds,
            "category": result.recording.category,
            "total_score": result.total_score,
            "ban_word_hits": result.ban_word_hits,
            "interruption_count": result.interruption_count,
            "price_validity_clear": result.price_validity_clear,
            "preop_mentioned": result.preop_mentioned,
            "postop_mentioned": result.postop_mentioned,
            "issues": result.issues,
            "check_results": [
                {
                    "rule_id": cr.rule_id,
                    "rule_name": cr.rule_name,
                    "passed": cr.passed,
                    "score": cr.score,
                    "detail": cr.detail,
                    "evidence": cr.evidence
                }
                for cr in result.check_results
            ]
        }

    def list_records(self) -> List[dict]:
        records = []
        for filename in os.listdir(self.records_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.records_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append({
                    "batch_id": data["batch_id"],
                    "batch_name": data["batch_name"],
                    "start_time": data["start_time"],
                    "end_time": data.get("end_time"),
                    "total_count": data["total_count"],
                    "passed_count": data["passed_count"],
                    "failed_count": data["failed_count"],
                    "rule_category": data["rule_category"],
                    "deal_filter": data["deal_filter"],
                    "filepath": filepath
                })
            except Exception:
                continue

        records.sort(key=lambda x: x["start_time"], reverse=True)
        return records

    def load_batch(self, batch_id: str) -> dict:
        for filename in os.listdir(self.records_dir):
            if not filename.endswith(".json"):
                continue
            if batch_id in filename:
                filepath = os.path.join(self.records_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {}


class ExcelExporter:
    def __init__(self):
        self.exports_dir = EXPORTS_DIR
        os.makedirs(self.exports_dir, exist_ok=True)

    def export_for_review(self, batch: BatchRecord, analyzer: ResultAnalyzer) -> str:
        wb = Workbook()

        ws1 = wb.active
        ws1.title = "质检总览"
        self._fill_overview_sheet(ws1, batch, analyzer)

        ws2 = wb.create_sheet("异常清单")
        self._fill_issues_sheet(ws2, batch, analyzer)

        ws3 = wb.create_sheet("门店汇总")
        self._fill_stores_sheet(ws3, batch, analyzer)

        ws4 = wb.create_sheet("详细结果")
        self._fill_detail_sheet(ws4, batch)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"质检报告_{batch.batch_name}_{timestamp}.xlsx"
        filepath = os.path.join(self.exports_dir, filename)

        wb.save(filepath)
        return filepath

    def _set_header_style(self, cell):
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

    def _set_cell_style(self, cell):
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

    def _fill_overview_sheet(self, ws, batch, analyzer):
        stats = analyzer.get_category_stats(batch)

        ws.merge_cells("A1:D1")
        ws["A1"] = f"质检报告 - " + batch.batch_name
        ws["A1"].font = Font(bold=True, size=16)
        ws["A1"].alignment = Alignment(horizontal="center")

        info = [
            ["批次ID", batch.batch_id],
            ["质检规则", RULE_CATEGORIES.get(batch.rule_category, batch.rule_category)],
            ["成交筛选", DEAL_STATUS.get(batch.deal_filter, batch.deal_filter)],
            ["源文件夹", batch.source_dir],
            ["开始时间", batch.start_time.strftime("%Y-%m-%d %H:%M:%S")],
            ["结束时间", batch.end_time.strftime("%Y-%m-%d %H:%M:%S") if batch.end_time else ""],
            ["录音总数", stats["total"]],
            ["通过数量", stats["passed"]],
            ["异常数量", stats["failed"]],
            ["通过率", f"{stats['pass_rate']}%"],
            ["平均分", stats["avg_score"]],
        ]

        row = 3
        for key, value in info:
            ws.cell(row=row, column=1, value=key)
            ws.cell(row=row, column=2, value=value)
            row += 1

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 40

    def _fill_issues_sheet(self, ws, batch, analyzer):
        headers = ["排名", "问题类型", "出现次数", "占比"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._set_header_style(cell)

        top_issues = analyzer.get_top_issues(batch, top_n=20)
        total = batch.total_count

        for row_idx, (issue, count) in enumerate(top_issues, 2):
            ws.cell(row=row_idx, column=1, value=row_idx - 1)
            ws.cell(row=row_idx, column=2, value=issue)
            ws.cell(row=row_idx, column=3, value=count)
            ws.cell(row=row_idx, column=4, value=f"{count/total*100:.1f}%")
            for col in range(1, 5):
                self._set_cell_style(ws.cell(row=row_idx, column=col))

        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 10

    def _fill_stores_sheet(self, ws, batch, analyzer):
        summaries = analyzer.get_store_summaries(batch)

        headers = ["门店名称", "录音数", "平均分", "通过率", "问题总数", "主要问题"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._set_header_style(cell)

        for row_idx, summary in enumerate(summaries, 2):
            ws.cell(row=row_idx, column=1, value=summary.store_name)
            ws.cell(row=row_idx, column=2, value=summary.total_count)
            ws.cell(row=row_idx, column=3, value=summary.avg_score)
            ws.cell(row=row_idx, column=4, value=f"{summary.pass_rate}%")
            ws.cell(row=row_idx, column=5, value=summary.issue_count)

            top_issues_str = "; ".join([f"{issue}({count})" for issue, count in summary.top_issues[:3]])
            ws.cell(row=row_idx, column=6, value=top_issues_str)

            if summary.avg_score < 60:
                for col in range(1, 7):
                    ws.cell(row=row_idx, column=col).fill = PatternFill(
                        start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                    )

            for col in range(1, 7):
                self._set_cell_style(ws.cell(row=row_idx, column=col))

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 10
        ws.column_dimensions["E"].width = 10
        ws.column_dimensions["F"].width = 40

    def _fill_detail_sheet(self, ws, batch):
        headers = [
            "门店", "咨询师", "日期", "成交状态",
            "总得分", "禁用词", "打断次数",
            "有效期说明", "术前检查", "术后护理",
            "问题列表", "文件路径"
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            self._set_header_style(cell)

        results = sorted(batch.results, key=lambda x: x.total_score)

        for row_idx, result in enumerate(results, 2):
            rec = result.recording
            ws.cell(row=row_idx, column=1, value=rec.store)
            ws.cell(row=row_idx, column=2, value=rec.consultant)
            ws.cell(row=row_idx, column=3, value=rec.record_date)
            ws.cell(row=row_idx, column=4, value="已成交" if rec.is_dealt else "未成交")
            ws.cell(row=row_idx, column=5, value=result.total_score)
            ws.cell(row=row_idx, column=6, value="、".join(result.ban_word_hits) if result.ban_word_hits else "无")
            ws.cell(row=row_idx, column=7, value=result.interruption_count)
            ws.cell(row=row_idx, column=8, value="是" if result.price_validity_clear else "否")
            ws.cell(row=row_idx, column=9, value="是" if result.preop_mentioned else "否")
            ws.cell(row=row_idx, column=10, value="是" if result.postop_mentioned else "否")
            ws.cell(row=row_idx, column=11, value="; ".join(result.issues))
            ws.cell(row=row_idx, column=12, value=rec.file_path)

            if result.is_low_score:
                for col in range(1, 13):
                    ws.cell(row=row_idx, column=col).fill = PatternFill(
                        start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                    )

            for col in range(1, 13):
                self._set_cell_style(ws.cell(row=row_idx, column=col))

        widths = [12, 12, 12, 10, 8, 20, 10, 10, 10, 10, 30, 50]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + i)].width = w
