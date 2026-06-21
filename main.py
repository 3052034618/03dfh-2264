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
from analyzer import ResultAnalyzer, RecordManager, ExcelExporter
from qa_engine import QARuleEngine

init(autoreset=True)


class QACLI:
    def __init__(self):
        self.importer = RecordingImporter()
        self.processor = BatchProcessor()
        self.analyzer = ResultAnalyzer()
        self.record_manager = RecordManager()
        self.exporter = ExcelExporter()

        self.current_dir = SAMPLES_DIR
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
        directory = self.get_input("请输入文件夹路径", default_dir)

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

        print(f"\n{Fore.GREEN}✓ 找到 {len(files)} 个录音文件{Style.RESET_ALL}\n")

        sample_files = files[:10]
        table_data = []
        for fname in sample_files:
            parsed = self.importer.parser.parse(fname)
            if parsed:
                deal = "已成交" if parsed["deal"] == "dealt" else "未成交"
                table_data.append([
                    parsed["store"],
                    parsed["consultant"],
                    parsed["date"],
                    deal
                ])
            else:
                table_data.append(["(格式不符)", fname, "", ""])

        print(tabulate(table_data, headers=["门店", "咨询师", "日期", "成交状态"], tablefmt="simple"))

        if len(files) > 10:
            print(f"\n  ... 还有 {len(files) - 10} 个文件")

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

            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ 质检完成！{Style.RESET_ALL}")
            print(f"\n  批次ID: {batch.batch_id}")
            print(f"  录音总数: {batch.total_count}")
            print(f"  通过数: {batch.passed_count}  ({batch.passed_count / batch.total_count * 100:.1f}%)")
            print(f"  异常数: {batch.failed_count}  ({batch.failed_count / batch.total_count * 100:.1f}%)")
            print(f"  平均得分: {sum(r.total_score for r in batch.results) / batch.total_count:.1f}")

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

        print(f"{Style.BRIGHT}低分录音（<{LOW_SCORE_THRESHOLD}分）共 {len(low_scores)} 个{Style.RESET_ALL}\n")

        if not low_scores:
            print(f"{Fore.GREEN}太棒了！本次质检没有低分录音{Style.RESET_ALL}")
        else:
            table_data = []
            for i, result in enumerate(low_scores[:20], 1):
                rec = result.recording
                deal = "已成交" if rec.is_dealt else "未成交"
                issues_str = "; ".join(result.issues[:3])
                if len(result.issues) > 3:
                    issues_str += f" ...(+{len(result.issues) - 3})"
                table_data.append([
                    i,
                    rec.store,
                    rec.consultant,
                    deal,
                    result.total_score,
                    issues_str,
                    rec.file_name
                ])

            print(tabulate(
                table_data,
                headers=["序号", "门店", "咨询师", "成交", "得分", "主要问题", "文件名"],
                tablefmt="simple"
            ))

            if len(low_scores) > 20:
                print(f"\n  ... 还有 {len(low_scores) - 20} 个低分录音")

        print(f"\n{Style.BRIGHT}问题类型统计:{Style.RESET_ALL}\n")
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

        choice = self.get_input("\n输入序号加载该批次，回车返回", "")
        if choice.isdigit() and 1 <= int(choice) <= len(records):
            self._load_history(records[int(choice) - 1])

        self.pause()

    def _load_history(self, record_info: dict):
        batch_id = record_info["batch_id"]
        data = self.record_manager.load_batch(batch_id)

        if not data:
            print(f"{Fore.RED}加载失败{Style.RESET_ALL}")
            return

        from models import Recording, RecordingQAResult, CheckItemResult, BatchRecord

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

        self.current_batch = batch
        self.current_batch_name = data["batch_name"]
        self.current_category = data["rule_category"]
        self.current_deal_filter = data["deal_filter"]

        print(f"\n{Fore.GREEN}✓ 已加载批次: {data['batch_name']}{Style.RESET_ALL}")
        print(f"  可在【异常清单】【门店汇总】【结果导出】中查看")

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
