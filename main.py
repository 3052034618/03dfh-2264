import os
import sys
from datetime import datetime
from colorama import init, Fore, Style, Back
from tabulate import tabulate

from config import (
    SAMPLES_DIR, RULE_CATEGORIES, DEAL_STATUS,
    LOW_SCORE_THRESHOLD, BASE_DIR
)
from importer import RecordingImporter
from batch_processor import BatchProcessor
from analyzer import ResultAnalyzer, RecordManager, ExcelExporter, BatchComparator
from qa_engine import QARuleEngine

init(autoreset=True)


class QACLI:
    def __init__(self):
        self.importer = RecordingImporter()
        self.processor = BatchProcessor()
        self.analyzer = ResultAnalyzer()
        self.record_manager = RecordManager()
        self.exporter = ExcelExporter()
        self.comparator = BatchComparator(self.analyzer)

        self.current_dir = SAMPLES_DIR
        self.transcript_dir = None
        self.use_simulator_fallback = True
        self.current_category = "light"
        self.current_deal_filter = "all"
        self.current_batch = None
        self.current_batch_name = ""

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self):
        print(f"{Fore.CYAN}{Style.BRIGHT}")
        print("=" * 60)
        print("      医美集团录音批量质检工具 v1.0")
        print("=" * 60)
        print(Style.RESET_ALL)

    def print_menu(self):
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 主菜单 】{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}[1] 导入录音{Style.RESET_ALL}    指定文件夹，解析门店和咨询师")
        print(f"{Fore.GREEN}[2] 规则选择{Style.RESET_ALL}    轻医美/手术类/皮肤类，成交筛选")
        print(f"{Fore.GREEN}[3] 开始质检{Style.RESET_ALL}    批处理，实时显示进度")
        print(f"{Fore.GREEN}[4] 异常清单{Style.RESET_ALL}    低分录音、问题明细")
        print(f"{Fore.GREEN}[5] 门店汇总{Style.RESET_ALL}    各门店得分、Top10问题")
        print(f"{Fore.GREEN}[6] 结果导出{Style.RESET_ALL}    导出表格给主管复核")
        print(f"{Fore.GREEN}[7] 历史记录{Style.RESET_ALL}    查看历史批次，对比分析")
        print(f"{Fore.RED}[0] 退出{Style.RESET_ALL}")

    def print_status_bar(self):
        cat_name = RULE_CATEGORIES.get(self.current_category, self.current_category)
        deal_name = DEAL_STATUS.get(self.current_deal_filter, self.current_deal_filter)

        file_count = len(self.importer.list_recording_files(self.current_dir))

        print(f"\n{Fore.CYAN}{'-' * 60}")
        print(f"  当前文件夹: {self.current_dir}")
        if self.transcript_dir:
            print(f"  转写文件夹: {Fore.GREEN}{self.transcript_dir}{Style.RESET_ALL}")
        else:
            print(f"  转写文件夹: {Fore.LIGHTBLACK_EX}未设置（使用同名txt或模拟）{Style.RESET_ALL}")
        print(f"  录音文件数: {file_count} 个")
        print(f"  质检规则: {cat_name} | 成交筛选: {deal_name}")
        if self.current_batch:
            print(f"  当前批次: {self.current_batch_name} ({self.current_batch.batch_id})")
            print(f"  批处理状态: 已完成 | 通过率: {self.current_batch.passed_count}/{self.current_batch.total_count}")
        else:
            print(f"  当前批次: 无")
        print(f"{'-' * 60}{Style.RESET_ALL}")

    def get_input(self, prompt: str, default: str = "") -> str:
        if default:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "

        try:
            value = input(f"{Fore.WHITE}{prompt}{Style.RESET_ALL}").strip()
            return value if value else default
        except (EOFError, KeyboardInterrupt):
            return default

    def pause(self):
        input(f"\n{Fore.YELLOW}按回车键继续...{Style.RESET_ALL}")

    # ===== 操作1: 导入录音 =====
    def action_import(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 导入录音 】{Style.RESET_ALL}")
        print(f"  请指定录音文件夹路径")
        print(f"  文件名格式: 门店_咨询师_日期_时间_成交状态.wav")
        print(f"  例: 朝阳店_张美丽_20240115_143000_dealt.wav\n")

        default_dir = self.current_dir or SAMPLES_DIR
        directory = self.get_input("请输入录音文件夹路径", default_dir)

        if not os.path.exists(directory):
            print(f"\n{Fore.RED}错误: 文件夹不存在 - {directory}{Style.RESET_ALL}")
            self.pause()
            return

        files = self.importer.list_recording_files(directory)
        if not files:
            print(f"\n{Fore.RED}该文件夹下没有找到 .wav 录音文件{Style.RESET_ALL}")
            self.pause()
            return

        self.current_dir = directory

        print(f"\n{Fore.GREEN}✓ 找到 {len(files)} 个录音文件{Style.RESET_ALL}")

        transcript_dir_default = self.transcript_dir if self.transcript_dir else "留空表示不设置"
        transcript_input = self.get_input("\n请输入转写稿文件夹路径（留空则使用同名txt或模拟）", transcript_dir_default)
        if transcript_input and transcript_input != "留空表示不设置":
            if os.path.exists(transcript_input):
                self.transcript_dir = transcript_input
                self.importer.set_transcript_dir(transcript_input)
                print(f"{Fore.GREEN}✓ 已设置转写文件夹{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ 转写文件夹不存在，继续使用默认设置{Style.RESET_ALL}")
                self.transcript_dir = None
                self.importer.set_transcript_dir(None)
        else:
            self.transcript_dir = None
            self.importer.set_transcript_dir(None)

        fallback_choice = self.get_input("无转写稿时是否使用模拟数据？(y/n)", "y" if self.use_simulator_fallback else "n")
        self.use_simulator_fallback = fallback_choice.lower() == "y"
        self.importer.set_simulator_fallback(self.use_simulator_fallback)

        self.importer.import_from_directory(self.current_dir, self.current_category, self.current_deal_filter)
        stats = self.importer.get_transcript_stats()

        print(f"\n{Style.BRIGHT}转写稿统计:{Style.RESET_ALL}")
        print(f"  真实转写: {Fore.GREEN}{stats['real']} 个{Style.RESET_ALL}")
        if stats['simulated'] > 0:
            print(f"  模拟转写: {Fore.YELLOW}{stats['simulated']} 个{Style.RESET_ALL}")
        if stats['failed'] > 0:
            print(f"  导入失败: {Fore.RED}{stats['failed']} 个{Style.RESET_ALL}")

        sample_files = files[:8]
        table_data = []
        for fname in sample_files:
            parsed = self.importer.parser.parse(fname)
            if parsed:
                deal = "已成交" if parsed["deal"] == "dealt" else "未成交"
                txt_name = os.path.splitext(fname)[0] + ".txt"
                has_txt = os.path.exists(os.path.join(self.current_dir, txt_name))
                if self.transcript_dir:
                    has_txt = has_txt or os.path.exists(os.path.join(self.transcript_dir, txt_name))
                source = "真实转写" if has_txt else ("模拟转写" if self.use_simulator_fallback else "无转写")
                source_color = Fore.GREEN if has_txt else (Fore.YELLOW if self.use_simulator_fallback else Fore.RED)
                table_data.append([
                    parsed["store"],
                    parsed["consultant"],
                    parsed["date"],
                    deal,
                    f"{source_color}{source}{Style.RESET_ALL}"
                ])
            else:
                table_data.append(["(格式不符)", fname, "", "", ""])

        print(f"\n{Style.BRIGHT}文件预览（前8个）:{Style.RESET_ALL}\n")
        print(tabulate(table_data, headers=["门店", "咨询师", "日期", "成交状态", "转写来源"], tablefmt="simple"))

        if len(files) > 8:
            print(f"\n  ... 还有 {len(files) - 8} 个文件")

        self.pause()

    # ===== 操作2: 规则选择 =====
    def action_rules(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 规则选择 】{Style.RESET_ALL}\n")

        print(f"{Style.BRIGHT}请选择质检规则类型:{Style.RESET_ALL}")
        categories = list(RULE_CATEGORIES.items())
        for i, (key, name) in enumerate(categories, 1):
            marker = " ◄" if key == self.current_category else ""
            print(f"  [{i}] {name}{marker}")

        cat_choice = self.get_input("\n请选择规则编号", "")
        if cat_choice.isdigit() and 1 <= int(cat_choice) <= len(categories):
            self.current_category = categories[int(cat_choice) - 1][0]

        print(f"\n{Style.BRIGHT}请选择成交筛选:{Style.RESET_ALL}")
        deals = list(DEAL_STATUS.items())
        for i, (key, name) in enumerate(deals, 1):
            marker = " ◄" if key == self.current_deal_filter else ""
            print(f"  [{i}] {name}{marker}")

        deal_choice = self.get_input("\n请选择筛选编号", "")
        if deal_choice.isdigit() and 1 <= int(deal_choice) <= len(deals):
            self.current_deal_filter = deals[int(deal_choice) - 1][0]

        engine = QARuleEngine(category=self.current_category)
        ban_words = engine.get_ban_words()

        print(f"\n{Style.BRIGHT}当前规则配置:{Style.RESET_ALL}")
        print(f"  规则类型: {RULE_CATEGORIES[self.current_category]}")
        print(f"  成交筛选: {DEAL_STATUS[self.current_deal_filter]}")
        print(f"  禁用词库（{len(ban_words)}个）: {', '.join(ban_words[:5])}...")
        print(f"  打断阈值: {__import__('config').INTERRUPTION_THRESHOLD} 次")
        print(f"  低分阈值: {LOW_SCORE_THRESHOLD} 分")

        self.pause()

    # ===== 操作3: 开始质检 =====
    def action_batch(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 开始质检 】{Style.RESET_ALL}\n")

        if not self.current_dir or not os.path.exists(self.current_dir):
            print(f"{Fore.RED}请先指定录音文件夹（选择 导入录音）{Style.RESET_ALL}")
            self.pause()
            return

        default_name = f"周检_{datetime.now().strftime('%Y%m%d')}"
        self.current_batch_name = self.get_input("请输入批次名称", default_name)

        cat_name = RULE_CATEGORIES.get(self.current_category, self.current_category)
        deal_name = DEAL_STATUS.get(self.current_deal_filter, self.current_deal_filter)

        print(f"\n  质检规则: {cat_name}")
        print(f"  成交筛选: {deal_name}")
        print(f"  源文件夹: {self.current_dir}")

        confirm = self.get_input("\n确认开始质检？(y/n)", "y")
        if confirm.lower() != "y":
            print("已取消")
            self.pause()
            return

        print(f"\n{Fore.CYAN}正在加载录音文件...{Style.RESET_ALL}")

        try:
            self.processor.importer.set_transcript_dir(self.transcript_dir)
            self.processor.importer.set_simulator_fallback(self.use_simulator_fallback)

            batch = self.processor.process_directory(
                name=self.current_batch_name,
                directory=self.current_dir,
                category=self.current_category,
                deal_filter=self.current_deal_filter
            )
            self.current_batch = batch

            if batch.total_count == 0:
                print(f"\n{Fore.RED}没有找到符合条件的录音文件{Style.RESET_ALL}")
                self.pause()
                return

            self.record_manager.save_batch(batch)
            transcript_stats = self.processor.importer.get_transcript_stats()

            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ 质检完成！{Style.RESET_ALL}")
            print(f"\n  批次ID: {batch.batch_id}")
            print(f"  录音总数: {batch.total_count}")
            print(f"  通过数: {batch.passed_count}  ({batch.passed_count / batch.total_count * 100:.1f}%)")
            print(f"  异常数: {batch.failed_count}  ({batch.failed_count / batch.total_count * 100:.1f}%)")
            print(f"  平均得分: {sum(r.total_score for r in batch.results) / batch.total_count:.1f}")
            print(f"\n  转写来源:")
            print(f"    真实转写: {Fore.GREEN}{transcript_stats['real']} 个{Style.RESET_ALL}")
            if transcript_stats['simulated'] > 0:
                print(f"    模拟转写: {Fore.YELLOW}{transcript_stats['simulated']} 个{Style.RESET_ALL}")
            if transcript_stats['failed'] > 0:
                print(f"    导入失败: {Fore.RED}{transcript_stats['failed']} 个{Style.RESET_ALL}")

            duration = (batch.end_time - batch.start_time).total_seconds() if batch.end_time else 0
            print(f"  耗时: {duration:.1f} 秒")

        except Exception as e:
            print(f"\n{Fore.RED}质检过程出错: {e}{Style.RESET_ALL}")

        self.pause()

    # ===== 操作4: 异常清单 =====
    def action_issues(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 异常清单 】{Style.RESET_ALL}\n")

        if not self.current_batch:
            print(f"{Fore.RED}请先执行批处理（选择 开始质检）{Style.RESET_ALL}")
            self.pause()
            return

        low_scores = self.analyzer.get_low_score_list(self.current_batch)

        print(f"{Style.BRIGHT}低分录音（<{LOW_SCORE_THRESHOLD}分）共 {len(low_scores)} 个{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}提示: 文件路径可直接复制用于精听{Style.RESET_ALL}\n")

        if not low_scores:
            print(f"{Fore.GREEN}太棒了！本次质检没有低分录音{Style.RESET_ALL}")
        else:
            table_data = []
            for i, result in enumerate(low_scores[:15], 1):
                rec = result.recording
                deal = "已成交" if rec.is_dealt else "未成交"
                issues_str = "; ".join(result.issues[:2])
                if len(result.issues) > 2:
                    issues_str += f" ...(+{len(result.issues) - 2})"
                source = "真实" if getattr(rec, "transcript_source", "simulated") == "real" else "模拟"
                table_data.append([
                    i,
                    rec.store,
                    rec.consultant,
                    deal,
                    result.total_score,
                    source,
                    issues_str,
                ])

            print(tabulate(
                table_data,
                headers=["#", "门店", "咨询师", "成交", "得分", "转写", "主要问题"],
                tablefmt="simple"
            ))

            print(f"\n{Style.BRIGHT}📂 低分录音完整路径（按得分升序）:{Style.RESET_ALL}\n")
            for i, result in enumerate(low_scores[:15], 1):
                rec = result.recording
                score_color = Fore.RED if result.total_score < 40 else Fore.YELLOW
                print(f"  {i:2d}. [{score_color}{result.total_score}分{Style.RESET_ALL}] {rec.store} - {rec.consultant}")
                print(f"     {Fore.CYAN}{rec.file_path}{Style.RESET_ALL}")

            if len(low_scores) > 15:
                print(f"\n  ... 还有 {len(low_scores) - 15} 个低分录音，详见导出表格")

        print(f"\n{Style.BRIGHT}问题类型统计 Top10:{Style.RESET_ALL}\n")
        top_issues = self.analyzer.get_top_issues(self.current_batch, top_n=10)
        table_data = []
        for i, (issue, count) in enumerate(top_issues, 1):
            pct = count / self.current_batch.total_count * 100
            table_data.append([i, issue, count, f"{pct:.1f}%"])

        print(tabulate(table_data, headers=["排名", "问题类型", "出现次数", "占比"], tablefmt="simple"))

        if low_scores:
            detail = self.get_input("\n输入序号查看详细质检结果，回车返回", "")
            if detail.isdigit() and 1 <= int(detail) <= len(low_scores):
                self._show_detail(low_scores[int(detail) - 1])

        self.pause()

    def _show_detail(self, result):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 质检详情 】{Style.RESET_ALL}\n")

        rec = result.recording
        print(f"  文件: {Fore.CYAN}{rec.file_name}{Style.RESET_ALL}")
        print(f"  路径: {rec.file_path}")
        print(f"  门店: {rec.store} | 咨询师: {rec.consultant}")
        print(f"  日期: {rec.record_date} {rec.record_time}")
        print(f"  状态: {'已成交' if rec.is_dealt else '未成交'} | 时长: {rec.duration_seconds}秒")
        print(f"\n  {Style.BRIGHT}总得分: {Fore.RED if result.is_low_score else Fore.GREEN}{result.total_score}分{Style.RESET_ALL}\n")

        print(f"{Style.BRIGHT}各分项得分:{Style.RESET_ALL}")
        for check in result.check_results:
            status = f"{Fore.GREEN}✓{Style.RESET_ALL}" if check.passed else f"{Fore.RED}✗{Style.RESET_ALL}"
            print(f"  {status} {check.rule_name}: {check.score}分 - {check.detail}")
            if check.evidence:
                for ev in check.evidence[:2]:
                    print(f"      证据: {Fore.LIGHTBLACK_EX}{ev}{Style.RESET_ALL}")

        print(f"\n{Style.BRIGHT}问题列表:{Style.RESET_ALL}")
        for i, issue in enumerate(result.issues, 1):
            print(f"  {i}. {Fore.RED}{issue}{Style.RESET_ALL}")

        print(f"\n{Style.BRIGHT}转写文本预览:{Style.RESET_ALL}")
        transcript = rec.transcript
        if len(transcript) > 300:
            transcript = transcript[:300] + "..."
        print(f"  {Fore.LIGHTBLACK_EX}{transcript}{Style.RESET_ALL}")

    # ===== 操作5: 门店汇总 =====
    def action_stores(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 门店汇总 】{Style.RESET_ALL}\n")

        if not self.current_batch:
            print(f"{Fore.RED}请先执行批处理（选择 开始质检）{Style.RESET_ALL}")
            self.pause()
            return

        summaries = self.analyzer.get_store_summaries(self.current_batch)

        print(f"{Style.BRIGHT}各门店质检得分排名（由低到高）:{Style.RESET_ALL}\n")

        table_data = []
        for i, summary in enumerate(summaries, 1):
            color = Fore.RED if summary.avg_score < LOW_SCORE_THRESHOLD else Fore.GREEN
            top_issues_str = "; ".join([f"{issue}({count})" for issue, count in summary.top_issues[:2]])
            table_data.append([
                i,
                summary.store_name,
                summary.total_count,
                f"{color}{summary.avg_score}{Style.RESET_ALL}",
                f"{summary.pass_rate}%",
                summary.issue_count,
                top_issues_str
            ])

        print(tabulate(
            table_data,
            headers=["排名", "门店", "录音数", "平均分", "通过率", "问题数", "主要问题"],
            tablefmt="simple"
        ))

        print(f"\n{Style.BRIGHT}全店问题 Top 10:{Style.RESET_ALL}\n")
        top_issues = self.analyzer.get_top_issues(self.current_batch, top_n=10)
        table_data = []
        for i, (issue, count) in enumerate(top_issues, 1):
            pct = count / self.current_batch.total_count * 100
            bar_len = int(pct / 2)
            bar = "█" * bar_len
            table_data.append([i, issue, count, f"{pct:.1f}%", bar])

        print(tabulate(table_data, headers=["排名", "问题类型", "次数", "占比", "分布"], tablefmt="simple"))

        self.pause()

    # ===== 操作6: 结果导出 =====
    def action_export(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 结果导出 】{Style.RESET_ALL}\n")

        if not self.current_batch:
            print(f"{Fore.RED}请先执行批处理（选择 开始质检）{Style.RESET_ALL}")
            self.pause()
            return

        print(f"  当前批次: {self.current_batch_name}")
        print(f"  录音总数: {self.current_batch.total_count}")
        print(f"  异常数: {self.current_batch.failed_count}")
        print(f"\n  将导出 Excel 表格，包含以下工作表:")
        print(f"    1. 质检总览 - 批次基本信息")
        print(f"    2. 异常清单 - 问题类型排名")
        print(f"    3. 门店汇总 - 各门店得分统计")
        print(f"    4. 详细结果 - 每条录音的完整质检结果\n")

        confirm = self.get_input("确认导出？(y/n)", "y")
        if confirm.lower() != "y":
            print("已取消")
            self.pause()
            return

        try:
            filepath = self.exporter.export_for_review(self.current_batch, self.analyzer)
            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ 导出成功！{Style.RESET_ALL}")
            print(f"\n  文件路径: {Fore.CYAN}{filepath}{Style.RESET_ALL}")
            print(f"  请将此文件发送给质检主管进行复核")
        except Exception as e:
            print(f"\n{Fore.RED}导出失败: {e}{Style.RESET_ALL}")

        self.pause()

    # ===== 操作7: 历史记录 =====
    def action_history(self):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 历史记录 】{Style.RESET_ALL}\n")

        records = self.record_manager.list_records()

        if not records:
            print(f"{Fore.LIGHTBLACK_EX}暂无历史记录{Style.RESET_ALL}")
            self.pause()
            return

        print(f"共找到 {len(records)} 条历史批次:\n")

        table_data = []
        for i, rec in enumerate(records[:15], 1):
            start_time = rec["start_time"][:19].replace("T", " ")
            cat_name = RULE_CATEGORIES.get(rec["rule_category"], rec["rule_category"])
            pct = rec["passed_count"] / rec["total_count"] * 100 if rec["total_count"] > 0 else 0
            table_data.append([
                i,
                rec["batch_name"],
                rec["batch_id"],
                cat_name,
                rec["total_count"],
                f"{pct:.1f}%",
                start_time
            ])

        print(tabulate(
            table_data,
            headers=["序号", "批次名称", "批次ID", "规则", "总数", "通过率", "开始时间"],
            tablefmt="simple"
        ))

        print(f"\n{Style.BRIGHT}操作选项:{Style.RESET_ALL}")
        print(f"  [1] 加载某个批次查看详情")
        print(f"  [2] 选择两个批次进行对比")
        print(f"  [0] 返回主菜单")

        choice = self.get_input("\n请选择操作", "1")

        if choice == "1":
            idx = self.get_input("请输入批次序号", "1")
            if idx.isdigit() and 1 <= int(idx) <= len(records):
                self._load_history(records[int(idx) - 1])
        elif choice == "2":
            if len(records) < 2:
                print(f"\n{Fore.YELLOW}至少需要2个批次才能对比{Style.RESET_ALL}")
                self.pause()
                return

            idx1 = self.get_input("请输入第一个批次序号（较旧）", "1")
            idx2 = self.get_input("请输入第二个批次序号（较新）", "2")

            if idx1.isdigit() and idx2.isdigit() \
               and 1 <= int(idx1) <= len(records) \
               and 1 <= int(idx2) <= len(records) \
               and idx1 != idx2:

                batch_a = self._load_batch_to_memory(records[int(idx1) - 1])
                batch_b = self._load_batch_to_memory(records[int(idx2) - 1])

                if batch_a and batch_b:
                    self._show_comparison(batch_a, batch_b)
                else:
                    print(f"\n{Fore.RED}批次加载失败{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}序号无效{Style.RESET_ALL}")

        self.pause()

    def _load_batch_to_memory(self, record_info: dict) -> object:
        from models import Recording, RecordingQAResult, CheckItemResult, BatchRecord

        batch_id = record_info["batch_id"]
        data = self.record_manager.load_batch(batch_id)

        if not data:
            return None

        batch = BatchRecord(
            batch_id=data["batch_id"],
            batch_name=data["batch_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            total_count=data["total_count"],
            passed_count=data["passed_count"],
            failed_count=data["failed_count"],
            rule_category=data["rule_category"],
            deal_filter=data["deal_filter"],
            source_dir=data["source_dir"]
        )

        for r_data in data["results"]:
            rec = Recording(
                file_path=r_data["file_path"],
                file_name=r_data["file_name"],
                store=r_data["store"],
                consultant=r_data["consultant"],
                record_date=r_data["record_date"],
                record_time=r_data["record_time"],
                deal_status=r_data["deal_status"],
                duration_seconds=r_data["duration_seconds"],
                transcript="",
                category=r_data["category"]
            )

            result = RecordingQAResult(
                recording=rec,
                total_score=r_data["total_score"],
                ban_word_hits=r_data["ban_word_hits"],
                interruption_count=r_data["interruption_count"],
                price_validity_clear=r_data["price_validity_clear"],
                preop_mentioned=r_data["preop_mentioned"],
                postop_mentioned=r_data["postop_mentioned"],
                issues=r_data["issues"],
                check_results=[
                    CheckItemResult(
                        rule_id=cr["rule_id"],
                        rule_name=cr["rule_name"],
                        passed=cr["passed"],
                        score=cr["score"],
                        detail=cr["detail"],
                        evidence=cr.get("evidence", [])
                    )
                    for cr in r_data["check_results"]
                ]
            )
            batch.results.append(result)

        return batch

    def _load_history(self, record_info: dict):
        batch = self._load_batch_to_memory(record_info)
        if batch:
            self.current_batch = batch
            self.current_batch_name = record_info["batch_name"]
            self.current_category = record_info["rule_category"]
            self.current_deal_filter = record_info["deal_filter"]

            print(f"\n{Fore.GREEN}✓ 已加载批次: {record_info['batch_name']}{Style.RESET_ALL}")
            print(f"  可在【异常清单】【门店汇总】【结果导出】中查看")
        else:
            print(f"\n{Fore.RED}加载失败{Style.RESET_ALL}")

    def _show_comparison(self, batch_a, batch_b):
        self.clear_screen()
        self.print_header()
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}【 批次对比 】{Style.RESET_ALL}")
        print(f"\n  {batch_a.batch_name}  →  {batch_b.batch_name}\n")

        result = self.comparator.compare_batches(batch_a, batch_b)

        a = result["batch_a"]
        b = result["batch_b"]

        print(f"{Style.BRIGHT}📊 总体指标对比:{Style.RESET_ALL}\n")

        diff_color = Fore.GREEN if b['pass_rate'] >= a['pass_rate'] else Fore.RED
        diff_sign = "+" if (b['pass_rate'] - a['pass_rate']) >= 0 else ""

        table_data = [
            ["录音总数", a['total'], b['total'],
             self._format_diff_num(b['total'] - a['total'])],
            ["通过数", a['passed'], b['passed'],
             self._format_diff_num(b['passed'] - a['passed'], good='+')],
            ["低分异常数", a['low_count'], b['low_count'],
             self._format_diff_num(b['low_count'] - a['low_count'], good='-')],
            ["通过率", f"{a['pass_rate']}%", f"{b['pass_rate']}%",
             f"{diff_color}{diff_sign}{round(b['pass_rate'] - a['pass_rate'], 1)}%{Style.RESET_ALL}"],
            ["平均分", a['avg_score'], b['avg_score'],
             self._format_diff_num(round(b['avg_score'] - a['avg_score'], 1), good='+')],
        ]

        print(tabulate(table_data, headers=["指标", a['name'], b['name'], "变化"], tablefmt="simple"))

        print(f"\n{Style.BRIGHT}🏪 门店平均分对比（按变化升序）:{Style.RESET_ALL}\n")

        store_comparison = sorted(
            result["store_comparison"],
            key=lambda x: x["avg_diff"] if x["avg_diff"] is not None else -999
        )

        store_table = []
        for sc in store_comparison:
            diff_str = self._format_diff_num(sc["avg_diff"], good='+') if sc["avg_diff"] is not None else "-"
            store_table.append([
                sc["store"],
                sc["avg_a"] if sc["avg_a"] is not None else "-",
                sc["avg_b"] if sc["avg_b"] is not None else "-",
                diff_str,
            ])

        print(tabulate(store_table, headers=["门店", f"{a['name']}(分)", f"{b['name']}(分)", "变化"], tablefmt="simple"))

        print(f"\n{Style.BRIGHT}🔝 问题类型 Top10 对比:{Style.RESET_ALL}\n")

        issue_table = []
        for i, ic in enumerate(result["issue_comparison"], 1):
            diff_str = self._format_diff_num(ic["diff"], good='-')
            issue_table.append([
                i,
                ic["issue"],
                ic["count_a"],
                ic["count_b"],
                diff_str,
            ])

        print(tabulate(issue_table, headers=["排名", "问题类型", a['name'], b['name'], "变化"], tablefmt="simple"))

        print(f"\n{Style.BRIGHT}操作选项:{Style.RESET_ALL}")
        print(f"  [1] 导出对比表到 Excel（用于周会复盘）")
        print(f"  [2] 将较新批次设为当前批次")
        print(f"  [0] 返回")

        choice = self.get_input("\n请选择操作", "0")
        if choice == "1":
            try:
                filepath = self.exporter.export_comparison(batch_a, batch_b, self.analyzer)
                print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ 对比表导出成功！{Style.RESET_ALL}")
                print(f"  文件路径: {Fore.CYAN}{filepath}{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.RED}导出失败: {e}{Style.RESET_ALL}")
        elif choice == "2":
            self.current_batch = batch_b
            self.current_batch_name = batch_b.batch_name
            self.current_category = batch_b.rule_category
            self.current_deal_filter = batch_b.deal_filter
            print(f"\n{Fore.GREEN}✓ 已将 [{batch_b.batch_name}] 设为当前批次{Style.RESET_ALL}")

    def _format_diff_num(self, value, good='+'):
        if value is None:
            return "-"
        if value > 0:
            color = Fore.GREEN if good == '+' else Fore.RED
            return f"{color}+{value}{Style.RESET_ALL}"
        elif value < 0:
            color = Fore.RED if good == '+' else Fore.GREEN
            return f"{color}{value}{Style.RESET_ALL}"
        else:
            return "0"

    # ===== 主循环 =====
    def run(self):
        while True:
            self.clear_screen()
            self.print_header()
            self.print_status_bar()
            self.print_menu()

            choice = self.get_input("\n请选择操作", "")

            if choice == "1":
                self.action_import()
            elif choice == "2":
                self.action_rules()
            elif choice == "3":
                self.action_batch()
            elif choice == "4":
                self.action_issues()
            elif choice == "5":
                self.action_stores()
            elif choice == "6":
                self.action_export()
            elif choice == "7":
                self.action_history()
            elif choice == "0":
                print(f"\n{Fore.CYAN}感谢使用，再见！{Style.RESET_ALL}\n")
                break
            else:
                print(f"\n{Fore.RED}无效选项，请重新选择{Style.RESET_ALL}")
                self.pause()


def main():
    try:
        cli = QACLI()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}感谢使用，再见！{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"\n{Fore.RED}程序异常: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main()
