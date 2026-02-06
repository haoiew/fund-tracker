# -*- coding: utf-8 -*-
"""
对比测试 EasyOCR vs PaddleOCR
"""
import os
import base64
import sys
import tempfile
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

output_file = 'ocr_comparison_result.txt'
sys.stdout = open(output_file, 'w', encoding='utf-8')

print("=" * 100)
print("EasyOCR vs PaddleOCR 对比测试")
print("=" * 100)

# 测试图片
image_paths = [
    r'd:\workdir\code\Explore\reference\myfund.jpg',
    r'd:\workdir\code\Explore\reference\fund2.jpg'
]

# ============ EasyOCR 测试 ============
print("\n\n" + "=" * 100)
print("【EasyOCR 测试】")
print("=" * 100)

from app.services.ocr_service import ocr_service as easyocr_service

for img_path in image_paths:
    if not os.path.exists(img_path):
        print(f"\n图片不存在: {img_path}")
        continue

    print(f"\n{'='*80}")
    print(f"测试图片: {os.path.basename(img_path)}")
    print('='*80)

    with open(img_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # 扫描图片
    result = easyocr_service.scan_image(image_data)

    print("\n【识别到的文本】")
    lines = result.get('raw_text', '').split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            print(f"[{i:3d}] {line}")

    # 提取持仓
    positions = easyocr_service.extract_positions(image_data)
    print(f"\n【提取的持仓】共 {len(positions)} 只基金")
    for i, pos in enumerate(positions, 1):
        print(f"{i:2d}. {pos.fund_name} | 市值:{pos.market_value} | 收益:{pos.profit_amount}")

# ============ PaddleOCR 测试 ============
print("\n\n" + "=" * 100)
print("【PaddleOCR 测试】")
print("=" * 100)

try:
    from paddleocr import PaddleOCR

    # 初始化PaddleOCR
    print("\n正在初始化 PaddleOCR...")
    import logging
    logging.getLogger('paddleocr').setLevel(logging.ERROR)
    paddle_ocr = PaddleOCR(
        lang='ch'
    )
    print("PaddleOCR 初始化完成！")

    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"\n图片不存在: {img_path}")
            continue

        print(f"\n{'='*80}")
        print(f"测试图片: {os.path.basename(img_path)}")
        print('='*80)

        # PaddleOCR识别
        result = paddle_ocr.predict(img_path)

        print("\n【识别到的文本】")
        texts = []
        if result and result[0]:
            for i, line in enumerate(result[0]):
                text = line[1][0]
                confidence = line[1][1]
                texts.append(text)
                print(f"[{i:3d}] {text} (置信度: {confidence:.3f})")

        print(f"\n共识别到 {len(texts)} 行文本")

except Exception as e:
    print(f"\nPaddleOCR 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
print("测试完成！")
print("=" * 100)

sys.stdout.close()
sys.stdout = sys.__stdout__
print(f"测试结果已保存到 {output_file}")
