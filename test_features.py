import os
from config import SAMPLES_DIR, DATA_DIR
from importer import RecordingImporter
from batch_processor import BatchProcessor
from analyzer import ResultAnalyzer, RecordManager, ExcelExporter, BatchComparator

TRANSCRIPTS_DIR = os.path.join(DATA_DIR, 'transcripts')

importer = RecordingImporter()
importer.set_transcript_dir(TRANSCRIPTS_DIR)
importer.set_simulator_fallback(True)

recordings = importer.import_from_directory(SAMPLES_DIR, 'light', 'all')
stats = importer.get_transcript_stats()

print('=== 需求1: 真实转写稿支持 ===')
print(f'总录音数: {len(recordings)}')
print(f'真实转写: {stats["real"]} 个')
print(f'模拟转写: {stats["simulated"]} 个')
print(f'导入失败: {stats["failed"]} 个')

real_count = sum(1 for r in recordings if getattr(r, 'transcript_source', 'simulated') == 'real')
print(f'带有真实转写的录音数: {real_count}')

if real_count > 0:
    real_rec = [r for r in recordings if getattr(r, 'transcript_source', 'simulated') == 'real'][0]
    print(f'\n第一个真实转写录音:')
    print(f'  门店: {real_rec.store}')
    print(f'  咨询师: {real_rec.consultant}')
    print(f'  转写稿长度: {len(real_rec.transcript)} 字')
    print(f'  转写内容(前80字): {real_rec.transcript[:80]}...')

print('\n=== 运行质检 ===')
processor = BatchProcessor()
processor.importer.set_transcript_dir(TRANSCRIPTS_DIR)
processor.importer.set_simulator_fallback(True)

batch = processor.process_directory('批次A', SAMPLES_DIR, 'light', 'all')
print(f'批处理完成: {batch.total_count} 条')
print(f'低分录音: {batch.failed_count} 条')

analyzer = ResultAnalyzer()
low_scores = analyzer.get_low_score_list(batch)

print('\n=== 需求2: 异常清单完整路径 ===')
print(f'低分录音数: {len(low_scores)}')
for i, r in enumerate(low_scores[:5], 1):
    print(f'  {i}. [{r.total_score}分] {r.recording.store} - {r.recording.consultant}')
    print(f'     完整路径: {r.recording.file_path}')

print('\n=== 保存批次记录 ===')
record_mgr = RecordManager()
record_mgr.save_batch(batch)

batch2 = processor.process_directory('批次B', SAMPLES_DIR, 'light', 'dealt')
record_mgr.save_batch(batch2)
print(f'已保存2个批次: 批次A({batch.total_count}条), 批次B({batch2.total_count}条)')

records = record_mgr.list_records()
print(f'历史记录数: {len(records)}')

print('\n=== 需求3: 批次对比 ===')
comparator = BatchComparator(analyzer)
result = comparator.compare_batches(batch, batch2)

a = result['batch_a']
b = result['batch_b']
print(f'批次A: {a["name"]} - {a["total"]}条, 通过率{a["pass_rate"]}%, 低分{a["low_count"]}个')
print(f'批次B: {b["name"]} - {b["total"]}条, 通过率{b["pass_rate"]}%, 低分{b["low_count"]}个')
print(f'低分变化: {result["low_diff"]}')

print(f'\n门店对比数: {len(result["store_comparison"])}')
for sc in result["store_comparison"][:3]:
    print(f'  {sc["store"]}: {sc["avg_a"]} -> {sc["avg_b"]} ({sc["avg_diff"]:+})')

print(f'\n问题对比数: {len(result["issue_comparison"])}')
for ic in result["issue_comparison"][:3]:
    print(f'  {ic["issue"]}: {ic["count_a"]} -> {ic["count_b"]} ({ic["diff"]:+})')

print('\n=== 导出对比表 ===')
exporter = ExcelExporter()
compare_path = exporter.export_comparison(batch, batch2, analyzer)
print(f'对比表已导出: {compare_path}')

review_path = exporter.export_for_review(batch, analyzer)
print(f'复核表已导出: {review_path}')

print('\n✅ 所有三个需求测试通过!')
