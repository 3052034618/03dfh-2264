import os
import re
import random
from typing import List, Optional, Tuple
from models import Recording
from config import FILENAME_PATTERN, SAMPLES_DIR


class FilenameParser:
    def __init__(self):
        self.pattern = re.compile(
            r"^(?P<store>.+?)_(?P<consultant>.+?)_(?P<date>\d{8})_(?P<time>\d{6})_(?P<deal>dealt|undealt)\.wav$"
        )

    def parse(self, filename: str) -> dict:
        match = self.pattern.match(filename)
        if not match:
            return {}
        return match.groupdict()


class TranscriptLoader:
    INTERRUPTION_MARKERS = ["（打断）", "【抢话】", "(插话)", "[打断]", "（插话）",
                            "打断：", "抢话：", "咨询师打断", "咨询师抢话"]

    @classmethod
    def load_from_file(cls, txt_path: str) -> Tuple[Optional[str], int]:
        if not os.path.exists(txt_path):
            return None, 0

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                transcript = f.read().strip()
        except (UnicodeDecodeError, IOError):
            try:
                with open(txt_path, "r", encoding="gbk") as f:
                    transcript = f.read().strip()
            except Exception:
                return None, 0

        if not transcript:
            return None, 0

        interruption_count = cls.count_interruptions(transcript)
        return transcript, interruption_count

    @classmethod
    def count_interruptions(cls, transcript: str) -> int:
        count = 0
        for marker in cls.INTERRUPTION_MARKERS:
            count += transcript.count(marker)

        pattern = r"顾[客客]：[^\n。？！]*?[。？！](?=\s*咨[询师]：)"
        short_pattern = r"顾[客客]：[^。？！\n]{2,10}[。？！](?=\s*咨[询师]：)"
        matches = re.findall(short_pattern, transcript)
        if len(matches) > 3:
            count += max(0, len(matches) - 2)

        return count

    @classmethod
    def estimate_duration(cls, transcript: str) -> int:
        char_count = len(transcript.replace("\n", "").replace(" ", ""))
        seconds = int(char_count / 3.5)
        return max(60, seconds)


class TranscriptSimulator:
    light_scripts = [
        "顾客您好，欢迎来到我们门店。今天想了解什么项目呢？嗯，我想了解一下玻尿酸隆鼻。好的，玻尿酸隆鼻效果很好，一针见效，保证让您满意。价格方面现在有活动，优惠力度很大。有效期到这个月底，您可以考虑一下。术后需要注意护理，避免按压。",
        "您好，请问有什么可以帮您？我想咨询一下瘦脸针。瘦脸针我们这边很受欢迎，绝对安全，无任何副作用。现在活动价很划算，仅限本周。做完后注意防晒补水，恢复期很短。",
        "欢迎光临，想了解什么项目呢？我想做水光针。水光针效果不错，皮肤会变得很好。价格方面我们有优惠套餐。术前需要做一下简单的皮肤检测，术后注意补水保湿。",
        "您好，请问想咨询什么项目？我想了解一下双眼皮。双眼皮手术我们做得很多，效果自然。现在有活动价，活动截止到月底。术后需要注意护理，忌口辛辣。",
        "欢迎咨询，今天想了解什么呢？我想做个填充。填充项目我们很专业，保证效果持久。现在有优惠活动，价格很实惠。有效期是本月内，您可以考虑。",
    ]

    surgery_scripts = [
        "您好，想了解什么手术项目？我想做隆胸手术。隆胸手术我们很专业，完全无痛，绝对安全。现在有优惠，价格很合适。术前需要做全面体检，包括血常规、凝血功能检查。术后护理很重要，需要休息一段时间。",
        "欢迎咨询，想做什么手术呢？我想咨询吸脂手术。吸脂手术效果很好，永不反弹。现在活动价优惠力度大。术前需要做身体检查，排除禁忌症。术后需要穿塑身衣，注意休息。",
        "您好，请问想了解什么手术项目？我想做鼻综合。鼻综合手术我们专家很厉害，保证效果完美。价格方面现在有活动。术前需要做术前评估和体检。术后护理要注意，避免碰撞。",
    ]

    skin_scripts = [
        "您好，想了解什么皮肤项目？我想做祛斑。祛斑我们用先进仪器，永久有效，永不反弹。现在有优惠活动。术后注意防晒补水，做好修复。",
        "欢迎咨询，皮肤有什么问题吗？我想做嫩肤。嫩肤项目效果很好，皮肤会变得很光滑。现在有优惠套餐，仅限本月。术后注意护理，补水防晒。",
        "您好，想做什么皮肤项目？我想了解一下祛痘。祛痘我们有专业方案，保证根除。现在活动价很划算。术后注意饮食和护理。",
    ]

    interruption_markers = ["（打断）", "【抢话】", "(插话)", "[打断]", "（插话）"]

    @classmethod
    def generate_transcript(cls, category: str, deal_status: str, seed: int = None) -> tuple:
        if seed is not None:
            random.seed(seed)

        scripts = {
            "light": cls.light_scripts,
            "surgery": cls.surgery_scripts,
            "skin": cls.skin_scripts,
        }

        script_list = scripts.get(category, cls.light_scripts)
        transcript = random.choice(script_list)

        interruption_count = random.randint(0, 5)
        if interruption_count > 0:
            parts = transcript.split("，")
            for i in range(min(interruption_count, len(parts) - 1)):
                idx = random.randint(1, len(parts) - 1)
                marker = random.choice(cls.interruption_markers)
                parts.insert(idx, marker)
            transcript = "，".join(parts)

        duration = random.randint(120, 900)

        return transcript, interruption_count, duration


class RecordingImporter:
    def __init__(self):
        self.parser = FilenameParser()
        self.simulator = TranscriptSimulator()
        self.loader = TranscriptLoader()
        self.transcript_dir: Optional[str] = None
        self.use_simulator_fallback: bool = True
        self.transcript_stats = {"real": 0, "simulated": 0, "failed": 0}

    def set_transcript_dir(self, directory: Optional[str]):
        self.transcript_dir = directory

    def set_simulator_fallback(self, enabled: bool):
        self.use_simulator_fallback = enabled

    def _find_transcript_file(self, wav_filename: str, wav_dir: str) -> Optional[str]:
        txt_name = os.path.splitext(wav_filename)[0] + ".txt"

        candidates = []

        if self.transcript_dir and os.path.exists(self.transcript_dir):
            candidates.append(os.path.join(self.transcript_dir, txt_name))

        same_dir_txt = os.path.join(wav_dir, txt_name)
        candidates.append(same_dir_txt)

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return None

    def import_from_directory(self, directory: str, category: str = "light",
                              deal_filter: str = "all") -> List[Recording]:
        recordings = []
        self.transcript_stats = {"real": 0, "simulated": 0, "failed": 0}

        if not os.path.exists(directory):
            return recordings

        for filename in sorted(os.listdir(directory)):
            if not filename.lower().endswith('.wav'):
                continue

            parsed = self.parser.parse(filename)
            if not parsed:
                continue

            if deal_filter == "dealt" and parsed["deal"] != "dealt":
                continue
            if deal_filter == "undealt" and parsed["deal"] != "undealt":
                continue

            file_path = os.path.join(directory, filename)
            transcript = ""
            interruption_count = 0
            duration = 0
            transcript_source = "simulated"

            txt_path = self._find_transcript_file(filename, directory)

            if txt_path:
                loaded_transcript, loaded_interruptions = self.loader.load_from_file(txt_path)
                if loaded_transcript:
                    transcript = loaded_transcript
                    interruption_count = loaded_interruptions
                    duration = self.loader.estimate_duration(transcript)
                    transcript_source = "real"
                    self.transcript_stats["real"] += 1
                else:
                    self.transcript_stats["failed"] += 1
            elif not self.use_simulator_fallback:
                self.transcript_stats["failed"] += 1
                continue

            if transcript_source == "simulated" and self.use_simulator_fallback:
                seed = hash(filename) % 10000
                transcript, interruption_count, duration = self.simulator.generate_transcript(
                    category, parsed["deal"], seed
                )
                self.transcript_stats["simulated"] += 1

            recording = Recording(
                file_path=file_path,
                file_name=filename,
                store=parsed["store"],
                consultant=parsed["consultant"],
                record_date=parsed["date"],
                record_time=parsed["time"],
                deal_status=parsed["deal"],
                duration_seconds=duration,
                transcript=transcript,
                category=category
            )
            recording.transcript_source = transcript_source
            recordings.append(recording)

        return recordings

    def list_recording_files(self, directory: str) -> List[str]:
        if not os.path.exists(directory):
            return []
        return sorted([f for f in os.listdir(directory) if f.lower().endswith('.wav')])

    def get_transcript_stats(self) -> dict:
        return self.transcript_stats.copy()
