#!/usr/bin/env python3
"""
轻量级模型下载脚本
用于在开发板上使用性能更好的轻量模型
"""

import os
import sys

def download_models():
    """下载推荐的轻量模型"""
    print("=" * 60)
    print("轻量级模型下载和切换指南")
    print("=" * 60)
    
    print("\n当前环境信息:")
    print(f"  - Python路径: {sys.executable}")
    print(f"  - 工作目录: {os.getcwd()}")
    
    models = {
        'yolov8n': {
            'name': 'YOLOv8 Nano (当前)',
            'size': '6.3 MB',
            'fps': '~5-10 (开发板)',
            'accuracy': '中等',
            'cmd': 'from ultralytics import YOLO; YOLO("yolov8n.pt")',
            'note': '已安装'
        },
        'yolov5n': {
            'name': 'YOLOv5 Nano',
            'size': '1.9 MB',
            'fps': '~8-15 (开发板)',
            'accuracy': '中等',
            'cmd': 'from ultralytics import YOLO; YOLO("yolov5n.pt")',
            'note': '推荐尝试'
        },
        'yolov8n-int8': {
            'name': 'YOLOv8 Nano Int8量化',
            'size': '3.2 MB',
            'fps': '~10-20 (开发板)',
            'accuracy': '中等',
            'cmd': 'from ultralytics import YOLO; YOLO("yolov8n-int8.pt")',
            'note': '最佳平衡'
        }
    }
    
    print("\n\n可选模型对比:")
    print("-" * 60)
    for model_id, info in models.items():
        print(f"\n{info['name']}")
        print(f"  文件大小: {info['size']}")
        print(f"  预期FPS: {info['fps']}")
        print(f"  准确度: {info['accuracy']}")
        print(f"  状态: {info['note']}")
    
    print("\n\n推荐配置方案:")
    print("-" * 60)
    print("""
    方案1: 快速修复（推荐首先尝试）
    ├─ 降低分辨率: 640x480 → 320x240 ✓ (已实施)
    ├─ 增加跳帧: 3 → 6 ✓ (已实施)
    └─ 预期效果: FPS 提升 2-3倍
    
    方案2: 切换YOLOv5n模型
    ├─ 替换 yolov8n.pt → yolov5n.pt
    ├─ 命令: python3 -c "from ultralytics import YOLO; YOLO('yolov5n.pt')"
    └─ 预期效果: FPS 再提升 30-50%
    
    方案3: 使用Int8量化模型
    ├─ 替换 yolov8n.pt → yolov8n-int8.pt
    ├─ 命令: python3 -c "from ultralytics import YOLO; YOLO('yolov8n-int8.pt')"
    └─ 预期效果: FPS 提升 50-100%，精度损失很小
    
    方案4: 组合优化
    ├─ YOLOv5n + 320x240分辨率 + 跳帧6 + 置信度调低
    └─ 预期效果: FPS 可达 15-20
    """)
    
    print("\n使用步骤:")
    print("-" * 60)
    print("""
    1. 下载模型:
       python3 -c "from ultralytics import YOLO; YOLO('yolov5n.pt')"
       
    2. 编辑 MC_web.py，修改第一行:
       将 model_name='yolov8n.pt' 
       改为 model_name='yolov5n.pt'
       
    3. 重新启动应用:
       python3 ./MC_web.py
       
    4. 观察终端输出，查看推理时间改进
    """)
    
    print("\n当前性能指标获取方式:")
    print("-" * 60)
    print("""
    1. 启动应用后，打开实时视频页面
    2. 右侧显示 "Inference: XXXms" - 推理耗时
    3. 如果 > 500ms，说明模型负载过高
    4. 如果 < 200ms，说明性能可以接受
    """)
    
    print("\n\n故障排除:")
    print("-" * 60)
    print("""
    问题: 下载模型失败
    解决: 检查网络连接，可手动下载:
         wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov5n.pt
    
    问题: 模型文件找不到
    解决: 确保 .pt 文件在 /home/sunrise/MC/ 目录下
    
    问题: 精度下降太多
    解决: 降低frame_skip值，或调高置信度阈值
    """)

if __name__ == '__main__':
    download_models()
