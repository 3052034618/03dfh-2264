import re
from typing import List, Tuple
from models import Recording, RecordingQAResult, CheckItemResult
from config import (
    BAN_WORDS, PRICE_VALIDITY_KEYWORDS, PREOP_CHECK_KEYWORDS,
    POSTOP_CARE_KEYWORDS, INTERRUPTION_THRESHOLD, RULE_CATEGORIES
)


class QARuleEngine:
    def __init__(self, category: str = "light"):
        self.category = category
        self.interruption_markers = ["（打断）", "【抢话】", "(插话)", "[打断]", "（插话）"]

    def get_ban_words(self) -> List[str]:
        words = BAN_WORDS.get("common", []) + BAN_WORDS.get(self.category, [])
        return words

    def check_ban_words(self, transcript: str) -> Tuple[List[str], List[str]]:
        hits = []
        evidence = []
        ban_words = self.get_ban_words()

        for word in ban_words:
            if word in transcript:
                hits.append(word)
                idx = transcript.find(word)
                start = max(0, idx - 10)
                end = min(len(transcript), idx + len(word) + 10)
                evidence.append(f"...{transcript[start:end]}...")

        return hits, evidence

    def count_interruptions(self, transcript: str) -> int:
        count = 0
        for marker in self.interruption_markers:
            count += transcript.count(marker)
        return count

    def check_price_validity(self, transcript: str) -> Tuple[bool, str]:
        has_price = any(word in transcript for word in ["价格", "优惠", "活动", "便宜", "划算", "优惠价", "活动价"])

        if not has_price:
            return True, "未提及价格优惠"

        has_validity = any(word in transcript for word in PRICE_VALIDITY_KEYWORDS)

        if has_validity:
            return True, "已说明价格优惠有效期"
        else:
            return False, "提及价格优惠但未说明有效期"

    def check_preop(self, transcript: str) -> Tuple[bool, List[str]]:
        mentioned = []
        for keyword in PREOP_CHECK_KEYWORDS:
            if keyword in transcript:
                mentioned.append(keyword)

        if self.category == "surgery":
            return len(mentioned) >= 2, mentioned
        else:
            return len(mentioned) >= 1, mentioned

    def check_postop(self, transcript: str) -> Tuple[bool, List[str]]:
        mentioned = []
        for keyword in POSTOP_CARE_KEYWORDS:
            if keyword in transcript:
                mentioned.append(keyword)

        return len(mentioned) >= 2, mentioned

    def analyze(self, recording: Recording) -> RecordingQAResult:
        result = RecordingQAResult(recording=recording)
        total_deduction = 0

        ban_hits, ban_evidence = self.check_ban_words(recording.transcript)
        result.ban_word_hits = ban_hits

        if ban_hits:
            deduction = min(len(ban_hits) * 15, 40)
            total_deduction += deduction
            result.check_results.append(CheckItemResult(
                rule_id="ban_words",
                rule_name="禁用词检测",
                passed=False,
                score=max(0, 20 - deduction),
                detail=f"检测到 {len(ban_hits)} 个禁用词: {', '.join(ban_hits)}",
                evidence=ban_evidence
            ))
            result.issues.append(f"禁用词: {', '.join(ban_hits)}")
        else:
            result.check_results.append(CheckItemResult(
                rule_id="ban_words",
                rule_name="禁用词检测",
                passed=True,
                score=20,
                detail="未检测到禁用词"
            ))

        interruption_count = self.count_interruptions(recording.transcript)
        result.interruption_count = interruption_count

        if interruption_count > INTERRUPTION_THRESHOLD:
            deduction = (interruption_count - INTERRUPTION_THRESHOLD) * 5
            deduction = min(deduction, 20)
            total_deduction += deduction
            result.check_results.append(CheckItemResult(
                rule_id="interruption",
                rule_name="打断顾客次数",
                passed=False,
                score=max(0, 20 - deduction),
                detail=f"打断 {interruption_count} 次，超过阈值 {INTERRUPTION_THRESHOLD} 次"
            ))
            result.issues.append(f"打断顾客 {interruption_count} 次")
        else:
            result.check_results.append(CheckItemResult(
                rule_id="interruption",
                rule_name="打断顾客次数",
                passed=True,
                score=20,
                detail=f"打断 {interruption_count} 次，在合理范围内"
            ))

        validity_clear, validity_detail = self.check_price_validity(recording.transcript)
        result.price_validity_clear = validity_clear

        if not validity_clear and "未提及价格优惠" not in validity_detail:
            deduction = 15
            total_deduction += deduction
            result.check_results.append(CheckItemResult(
                rule_id="price_validity",
                rule_name="价格优惠有效期",
                passed=False,
                score=5,
                detail=validity_detail
            ))
            result.issues.append("价格优惠未说明有效期")
        else:
            result.check_results.append(CheckItemResult(
                rule_id="price_validity",
                rule_name="价格优惠有效期",
                passed=True,
                score=20,
                detail=validity_detail
            ))

        preop_ok, preop_mentioned = self.check_preop(recording.transcript)
        result.preop_mentioned = preop_ok

        if not preop_ok:
            deduction = 15
            total_deduction += deduction
            result.check_results.append(CheckItemResult(
                rule_id="preop_check",
                rule_name="术前检查提及",
                passed=False,
                score=5,
                detail="未充分提及术前检查/评估"
            ))
            result.issues.append("未充分提及术前检查")
        else:
            result.check_results.append(CheckItemResult(
                rule_id="preop_check",
                rule_name="术前检查提及",
                passed=True,
                score=20,
                detail=f"提及术前检查相关: {', '.join(preop_mentioned)}"
            ))

        postop_ok, postop_mentioned = self.check_postop(recording.transcript)
        result.postop_mentioned = postop_ok

        if not postop_ok:
            deduction = 15
            total_deduction += deduction
            result.check_results.append(CheckItemResult(
                rule_id="postop_care",
                rule_name="术后护理提及",
                passed=False,
                score=5,
                detail="未充分提及术后护理/注意事项"
            ))
            result.issues.append("未充分提及术后护理")
        else:
            result.check_results.append(CheckItemResult(
                rule_id="postop_care",
                rule_name="术后护理提及",
                passed=True,
                score=20,
                detail=f"提及术后护理相关: {', '.join(postop_mentioned)}"
            ))

        result.total_score = max(0, 100 - total_deduction)

        return result

    def get_rule_list(self) -> List[dict]:
        rules = [
            {"id": "ban_words", "name": "禁用词检测", "weight": 20},
            {"id": "interruption", "name": "打断顾客次数", "weight": 20},
            {"id": "price_validity", "name": "价格优惠有效期", "weight": 20},
            {"id": "preop_check", "name": "术前检查提及", "weight": 20},
            {"id": "postop_care", "name": "术后护理提及", "weight": 20},
        ]
        return rules
