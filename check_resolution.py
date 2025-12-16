#!/usr/bin/env python3
"""
摄像头分辨率检测和配置工具
帮助你找到最佳的分辨率和性能平衡
"""

import cv2
import subprocess
import time

def test_camera_resolutions(camera_id=0):
    """测试摄像头支持的分辨率"""
    
    print("\n" + "=" * 60)
    print("🎥 摄像头分辨率检测工具")
    print("=" * 60)
    
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print(f"❌ 无法打开摄像头 {camera_id}")
        return
    
    print(f"\n[1] 测试摄像头 {camera_id} 支持的分辨率...")
    
    # 常见分辨率列表
    resolutions = [
        (640, 480),      # VGA
        (800, 600),      # SVGA
        (1024, 768),     # XGA
        (1280, 720),     # 720p
        (1280, 960),     
        (1600, 1200),    # UXGA
        (1920, 1080),    # 1080p
        (2560, 1440),    # 2K
        (2560, 1920),    
        (3840, 2160),    # 4K
    ]
    
    supported = []
    
    print("\n测试中", end="", flush=True)
    for width, height in resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_width == width and actual_height == height:
            supported.append((width, height))
            print(".", end="", flush=True)
        else:
            print("x", end="", flush=True)
    
    cap.release()
    
    print("\n\n[2] 支持的分辨率:")
    print("-" * 60)
    
    for i, (w, h) in enumerate(supported, 1):
        mp = (w * h) / 1000000
        name = ""
        if w == 640 and h == 480:
            name = " (VGA)"
        elif w == 1280 and h == 720:
            name = " (720p) ⭐ 推荐"
        elif w == 1920 and h == 1080:
            name = " (1080p) ⭐ 最好"
        elif w == 2560 and h == 1440:
            name = " (2K)"
        elif w == 3840 and h == 2160:
            name = " (4K)"
        
        print(f"  {i}. {w:4d}×{h:4d} ({mp:.1f}MP){name}")
    
    if not supported:
        print("  ❌ 未检测到支持的分辨率")
        return
    
    print("\n[3] 性能分析:")
    print("-" * 60)
    
    # 分析不同分辨率的检测时间
    test_resolutions = {
        '标清 (640×480)': (640, 480),
        '720p (1280×720)': (1280, 720),
        '1080p (1920×1080)': (1920, 1080),
    }
    
    for name, (w, h) in test_resolutions.items():
        cap = cv2.VideoCapture(camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if actual_w != w or actual_h != h:
            cap.release()
            continue
        
        # 读取几帧计算读取速度
        times = []
        for _ in range(5):
            start = time.time()
            ret, frame = cap.read()
            elapsed = time.time() - start
            if ret:
                times.append(elapsed)
        
        cap.release()
        
        if times:
            avg_time = sum(times) / len(times)
            fps = 1.0 / avg_time
            print(f"  {name:20s}: {fps:5.1f} FPS (读取耗时 {avg_time*1000:6.1f}ms)")
    
    print("\n[4] 建议配置:")
    print("-" * 60)
    print("""
    🎯 目标: 高精度检测 + 流畅视频播放
    
    ✓ 最佳配置 (推荐):
      - 分辨率: 1280×720 (720p)
      - 原因: 足够精度 + 可接受的处理延迟
      
    ✓ 如果需要更高精度 (检测远处目标):
      - 分辨率: 1920×1080 (1080p)
      - 警告: 处理时间较长，可能需要更强的硬件
      
    ✓ 如果性能不足 (检测太慢):
      - 分辨率: 640×480 (VGA)
      - 权衡: 失去部分精度
    
    当前系统特点:
    • 多线程架构: 视频流和检测分离
    • 视频播放: 始终流畅 (30 FPS)
    • 检测频率: 每3帧检测一次
    • 检测精度: 取决于分辨率
    """)
    
    print("\n[5] 修改分辨率的方法:")
    print("-" * 60)
    print("""
    编辑 MC_web.py，找到这一行:
    
      monitor = CrowdDensityMonitor(width=1280, height=720)
    
    修改为你需要的分辨率，例如:
    
      monitor = CrowdDensityMonitor(width=1920, height=1080)  # 1080p
      monitor = CrowdDensityMonitor(width=640, height=480)    # VGA
      
    然后重新启动应用。
    """)

def main():
    """主函数"""
    import sys
    
    # 检查是否提供了摄像头ID
    camera_id = 0
    if len(sys.argv) > 1:
        camera_id = int(sys.argv[1])
    
    test_camera_resolutions(camera_id)

if __name__ == '__main__':
    main()
