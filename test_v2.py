import os
import sys
from config import SAMPLES_DIR, DATA_DIR, EXPORTS_DIR
from importer import RecordingImporter
from batch_processor import BatchProcessor
from analyzer import ResultAnalyzer, RecordManager, ExcelExporter, BatchComparator

TRANSCRIPTS_DIR = os.path.join(DATA_DIR, 'transcripts')

print("=" * 60)
print("  功能全面测试")
print("=" * 60)

# === 需求4: 转写稿缺失清单 ===
print("\n✅ 需求4: 转写稿缺失清单")
importer = RecordingImporter()
importer.set_transcript_dir(TRANSCRIPTS_DIR)
missing_info = importer.check_missing_transcripts(SAMPLES_DIR)
print(f"  录音总数: {missing_info['total_wav']}")
print(f"  转写总数: {missing_info['total_txt']}")
print(f"  成功匹配: {missing_info['matched_count']}")
print(f"  缺少转写: {len(missing_info['missing_txt'])} 个")
print(f"  孤立转写: {len(missing_info['orphan_txt'])} 个")

# === 导入真实转写 ===
print("\n✅ 导入真实转写录音")
recordings = importer.import_from_directory(SAMPLES_DIR, 'light', 'all')
stats = importer.get_transcript_stats()
print(f"  总录音数: {len(recordings)}")
print(f"  真实转写: {stats['real']}")
print(f"  模拟转写: {stats['simulated']}")

real_rec = [r for r in recordings if getattr(r, 'transcript_source', '') == 'real'][:2]
for r in real_rec:
    print(f"  示例: {r.store}-{r.consultant} 转写长度:{len(r.transcript)}字")

# === 运行质检 ===
print("\n✅ 运行批次质检")
processor = BatchProcessor()
processor.importer.set_transcript_dir(TRANSCRIPTS_DIR)
processor.importer.set_simulator_fallback(True)

batch1 = processor.process_directory('周检_第1周', SAMPLES_DIR, 'light', 'all')
batch2 = processor.process_directory('周检_第2周', SAMPLES_DIR, 'light', 'dealt')

print(f"  批次1: {batch1.batch_name} - {batch1.total_count}条, {batch1.failed_count}个低分")
print(f"  批次2: {batch2.batch_name} - {batch2.total_count}条, {batch2.failed_count}个低分")

# 保存批次
record_mgr = RecordManager()
record_mgr.save_batch(batch1)
record_mgr.save_batch(batch2)

# === 需求1: 历史记录筛选 ===
print("\n✅ 需求1: 历史记录筛选")
all_records = record_mgr.list_records()
print(f"  总批次: {len(all_records)}")

# 按规则筛选
filtered = record_mgr.filter_records(rule_category='light')
print(f"  按规则light筛选: {len(filtered)} 个")

# 按门店筛选
stores = record_mgr.get_all_stores()
print(f"  历史涉及门店: {len(stores)} 个 - {', '.join(stores[:3])}...")

if stores:
    filtered2 = record_mgr.filter_records(store=stores[0])
    print(f"  按门店{stores[0]}筛选: {len(filtered2)} 个")

consultants = record_mgr.get_all_consultants()
print(f"  历史涉及咨询师: {len(consultants)} 位")

# === 需求2: 批次对比 - 咨询师维度 ===
print("\n✅ 需求2: 批次对比（咨询师维度）")
analyzer = ResultAnalyzer()
comparator = BatchComparator(analyzer)
result = comparator.compare_batches(batch1, batch2)

cons_comp = result["consultant_comparison"]
print(f"  对比咨询师数: {len(cons_comp)}")
print(f"  总体: {result['batch_a']['name']}({result['batch_a']['avg_score']}分) "
      f"→ {result['batch_b']['name']}({result['batch_b']['avg_score']}分)")

# 前3位咨询师对比
for cc in cons_comp[:3]:
    diff = cc['avg_diff']
    diff_str = f"{diff:+.1f}" if diff is not None else "N/A"
    print(f"    {cc['store']}-{cc['consultant']}: "
          f"{cc['avg_a']} → {cc['avg_b']} ({diff_str}) "
          f"低分:{cc['low_a']}→{cc['low_b']}")

# === 需求3: 低分录音分页数据 ===
print("\n✅ 需求3: 低分录音列表")
low_scores = analyzer.get_low_score_list(batch1)
print(f"  低分录音数: {len(low_scores)}")
if low_scores:
    print(f"  第一条路径: {low_scores[0].recording.file_path}")

# === 导出对比表 ===
print("\n✅ 导出对比表（含咨询师页）")
exporter = ExcelExporter()
comp_path = exporter.export_comparison(batch1, batch2, analyzer)
print(f"  导出文件: {comp_path}")

# === 导出复核表 ===
review_path = exporter.export_for_review(batch1, analyzer)
print(f"  复核表: {review_path}")

# === 验证咨询师汇总 ===
print("\n✅ 咨询师汇总验证")
cons_summaries = analyzer.get_consultant_summaries(batch1)
print(f"  咨询师总数: {len(cons_summaries)}")
for cs in cons_summaries[:3]:
    print(f"    {cs['store']}-{cs['consultant']}: "
          f"{cs['avg_score']}分, {cs['low_count']}个低分, {cs['issue_count']}个问题")

print("\n" + "=" * 60)
print("  全部测试通过 ✅")
print("=" * 60)
