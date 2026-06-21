import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
RECORDS_DIR = os.path.join(BASE_DIR, "records")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

for d in [DATA_DIR, SAMPLES_DIR, RECORDS_DIR, EXPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

FILENAME_PATTERN = r"^{store}_{consultant}_{date}_{time}_{deal}.wav"

RULE_CATEGORIES = {
    "light": "轻医美",
    "surgery": "手术类",
    "skin": "皮肤类"
}

DEAL_STATUS = {
    "all": "全部",
    "dealt": "已成交",
    "undealt": "未成交"
}

BAN_WORDS = {
    "common": ["保证", "100%", "绝对", "永不", "根除", "永久", "一针见效", "立即见效", "无任何副作用", "零风险"],
    "light": ["无恢复期", "随做随走", "零恢复期"],
    "surgery": ["无痛", "完全无痛", "绝对安全"],
    "skin": ["永不反弹", "永久有效"]
}

PRICE_VALIDITY_KEYWORDS = ["有效期", "活动截止", "优惠截止", "活动到", "截止到", "仅限", "活动期", "优惠期", "限时", "仅限今天", "仅限本月"]

PREOP_CHECK_KEYWORDS = ["术前检查", "体检", "身体检查", "血常规", "凝血", "过敏史", "禁忌症", "术前评估"]

POSTOP_CARE_KEYWORDS = ["术后护理", "注意事项", "护理", "忌口", "防晒", "补水", "修复", "恢复", "冰敷", "热敷"]

INTERRUPTION_THRESHOLD = 3

LOW_SCORE_THRESHOLD = 60
