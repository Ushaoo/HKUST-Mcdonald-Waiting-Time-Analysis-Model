#!/usr/bin/env python3
"""
模型性能基准测试
测试不同模型在你的硬件上的实际推理时间
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time
import os

def test_model_performance(model_name, test_frames=50):
    """测试模型性能"""
    
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name}")
    print(f"{'='*60}")
    
    try:
        # 加载模型
        print(f"[1] 加载模型...", end='', flush=True)
        start = time.time()
        model = YOLO(model_name)
        load_time = time.time() - start
        print(f" ✓ ({load_time:.2f}s)")
        
        # 创建测试帧
        print(f"[2] 创建测试帧...", end='', flush=True)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        print(f" ✓")
        
        # 预热
        print(f"[3] 预热模型...", end='', flush=True)
        _ = model(test_frame, verbose=False)
        print(f" ✓")
        
        # 测试推理时间
        print(f"[4] 测试推理性能 ({test_frames}帧)...")
        
        inference_times = []
        for i in range(test_frames):
            start = time.time()
            results = model(test_frame, classes=0, conf=0.5, verbose=False)
            inference_time = time.time() - start
            inference_times.append(inference_time)
            
            if (i + 1) % 10 == 0:
                print(f"    已完成: {i+1}/{test_frames} ", end='', flush=True)
                avg_time = np.mean(inference_times[-10:])
                print(f"(最近10帧平均: {avg_time*1000:.1f}ms)")
        
        # 计算统计
        avg_time = np.mean(inference_times)
        min_time = np.min(inference_times)
        max_time = np.max(inference_times)
        fps = 1.0 / avg_time
        
        print(f"\n[结果] {model_name}")
        print(f"  - 平均推理时间: {avg_time*1000:.1f}ms")
        print(f"  - 最小推理时间: {min_time*1000:.1f}ms")
        print(f"  - 最大推理时间: {max_time*1000:.1f}ms")
        print(f"  - 平均FPS: {fps:.1f} fps")
        
        # 评估
        if fps > 20:
            print(f"  - 评估: ⭐⭐⭐⭐⭐ 优秀 (开发板上表现很好)")
        elif fps > 10:
            print(f"  - 评估: ⭐⭐⭐⭐ 很好 (可以接受)")
        elif fps > 5:
            print(f"  - 评估: ⭐⭐⭐ 一般 (可能有卡顿)")
        elif fps > 2:
            print(f"  - 评估: ⭐⭐ 较差 (会有明显卡顿)")
        else:
            print(f"  - 评估: ⭐ 很差 (无法实时使用)")
        
        return {
            'model': model_name,
            'avg_time': avg_time,
            'fps': fps
        }
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return None

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🔬 模型性能基准测试")
    print("="*60)
    
    # 检查可用模型
    models = []
    for model_file in ['yolov8n.pt', 'yolov5nu.pt']:
        if os.path.exists(f'/home/sunrise/MC/{model_file}'):
            models.append(model_file)
    
    if not models:
        print("❌ 未找到任何模型文件")
        return
    
    print(f"\n找到 {len(models)} 个模型:")
    for model in models:
        size = os.path.getsize(f'/home/sunrise/MC/{model}') / 1024 / 1024
        print(f"  - {model} ({size:.1f}MB)")
    
    # 测试模型
    results = []
    for model_name in models:
        result = test_model_performance(model_name, test_frames=50)
        if result:
            results.append(result)
    
    # 总结
    if results:
        print(f"\n{'='*60}")
        print("📊 性能对比总结")
        print(f"{'='*60}\n")
        
        # 按FPS排序
        results_sorted = sorted(results, key=lambda x: x['fps'], reverse=True)
        
        for i, result in enumerate(results_sorted, 1):
            print(f"{i}. {result['model']}")
            print(f"   推理时间: {result['avg_time']*1000:.1f}ms")
            print(f"   FPS: {result['fps']:.1f}")
        
        best_model = results_sorted[0]['model']
        print(f"\n推荐使用: {best_model}")
        print(f"\n编辑 MC_web.py 并将第一行改为:")
        print(f'  model_name="{best_model}"')

if __name__ == '__main__':
    main()
