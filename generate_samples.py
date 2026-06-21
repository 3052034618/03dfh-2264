import os
import random
from config import SAMPLES_DIR

stores = ["朝阳店", "海淀店", "西城店", "东城店", "丰台店", "通州店"]
consultants = ["张美丽", "李媛媛", "王婷婷", "刘思琪", "陈雨欣", "赵雅婷", "孙晓雯", "周梦瑶"]
deal_statuses = ["dealt", "undealt"]

def generate_sample_files():
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    existing = [f for f in os.listdir(SAMPLES_DIR) if f.endswith('.wav')]
    if existing:
        print(f"示例文件夹已有 {len(existing)} 个文件，跳过生成")
        return

    print("正在生成示例录音文件...")

    random.seed(42)

    file_count = 0
    for store in stores:
        consultant_count = random.randint(2, 4)
        selected_consultants = random.sample(consultants, consultant_count)

        for consultant in selected_consultants:
            recordings_per_person = random.randint(2, 5)
            for i in range(recordings_per_person):
                date = f"202406{random.randint(10, 20):02d}"
                time = f"{random.randint(9, 18):02d}{random.randint(0, 59):02d}{random.randint(0, 59):02d}"
                deal = random.choice(deal_statuses)

                filename = f"{store}_{consultant}_{date}_{time}_{deal}.wav"
                filepath = os.path.join(SAMPLES_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(b"RIFF" + b"\x00" * 44 + b"\x00" * 1000)

                file_count += 1

    print(f"✓ 已生成 {file_count} 个示例录音文件")
    print(f"  门店数: {len(stores)}")
    print(f"  咨询师: {len(consultants)} 位")
    print(f"  文件夹: {SAMPLES_DIR}")

if __name__ == "__main__":
    generate_sample_files()
