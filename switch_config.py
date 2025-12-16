#!/usr/bin/env python3
"""
模型和性能配置切换工具
快速在不同配置之间切换
"""

import os
import sys

def show_menu():
    """显示配置菜单"""
    config_file = '/home/sunrise/MC/MC_web.py'
    
    print("\n" + "=" * 60)
    print("🚀 性能优化配置工具")
    print("=" * 60)
    
    print("\n当前可用配置:\n")
    
    configs = {
        '1': {
            'name': '平衡模式 (推荐)',
            'model': 'yolov8n.pt',
            'resolution': '320x240',
            'frame_skip': '6',
            'desc': '已优化，最适合开发板'
        },
        '2': {
            'name': '高性能模式',
            'model': 'yolov5nu.pt',
            'resolution': '320x240',
            'frame_skip': '6',
            'desc': '更快更轻，但精度略低'
        },
        '3': {
            'name': '高精度模式',
            'model': 'yolov8n.pt',
            'resolution': '640x480',
            'frame_skip': '3',
            'desc': '更精准但更慢，需要性能强悍的硬件'
        },
        '4': {
            'name': '极限模式',
            'model': 'yolov5nu.pt',
            'resolution': '240x180',
            'frame_skip': '8',
            'desc': '最快，适合实时监控但精度最低'
        }
    }
    
    for key, config in configs.items():
        print(f"选项 {key}: {config['name']}")
        print(f"  - 模型: {config['model']}")
        print(f"  - 分辨率: {config['resolution']}")
        print(f"  - 跳帧: {config['frame_skip']}")
        print(f"  - 说明: {config['desc']}\n")
    
    print("选项 5: 查看当前配置")
    print("选项 6: 自定义配置")
    print("选项 0: 退出\n")
    
    choice = input("请选择配置 (0-6): ").strip()
    
    if choice == '0':
        print("退出")
        return
    elif choice == '5':
        show_current_config(config_file)
        show_menu()
    elif choice in configs:
        apply_config(config_file, configs[choice])
        show_menu()
    elif choice == '6':
        custom_config(config_file)
        show_menu()
    else:
        print("❌ 无效选择")
        show_menu()

def show_current_config(config_file):
    """显示当前配置"""
    print("\n当前配置:")
    print("-" * 60)
    
    try:
        with open(config_file, 'r') as f:
            content = f.read()
            
            # 提取配置
            import re
            
            # 模型名称
            model_match = re.search(r"model_name='([^']+)'", content)
            model = model_match.group(1) if model_match else "未找到"
            
            # 分辨率
            width_match = re.search(r'set\(cv2\.CAP_PROP_FRAME_WIDTH,\s*(\d+)\)', content)
            height_match = re.search(r'set\(cv2\.CAP_PROP_FRAME_HEIGHT,\s*(\d+)\)', content)
            resolution = f"{width_match.group(1)}x{height_match.group(1)}" if width_match and height_match else "未找到"
            
            # 跳帧
            frame_skip_match = re.search(r'self\.frame_skip\s*=\s*(\d+)', content)
            frame_skip = frame_skip_match.group(1) if frame_skip_match else "未找到"
            
            print(f"模型: {model}")
            print(f"分辨率: {resolution}")
            print(f"跳帧间隔: {frame_skip}")
            
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")

def apply_config(config_file, config):
    """应用配置"""
    print(f"\n正在应用配置: {config['name']}...")
    
    try:
        with open(config_file, 'r') as f:
            content = f.read()
        
        # 替换模型
        import re
        content = re.sub(
            r"model_name='[^']+'",
            f"model_name='{config['model']}'",
            content
        )
        
        # 替换分辨率
        res = config['resolution'].split('x')
        width, height = int(res[0]), int(res[1])
        
        content = re.sub(
            r'set\(cv2\.CAP_PROP_FRAME_WIDTH,\s*\d+\)',
            f'set(cv2.CAP_PROP_FRAME_WIDTH, {width})',
            content
        )
        
        content = re.sub(
            r'set\(cv2\.CAP_PROP_FRAME_HEIGHT,\s*\d+\)',
            f'set(cv2.CAP_PROP_FRAME_HEIGHT, {height})',
            content
        )
        
        # 替换跳帧
        content = re.sub(
            r'self\.frame_skip\s*=\s*\d+',
            f'self.frame_skip = {config["frame_skip"]}',
            content
        )
        
        with open(config_file, 'w') as f:
            f.write(content)
        
        print(f"✓ 配置已应用!")
        print(f"  - 模型: {config['model']}")
        print(f"  - 分辨率: {config['resolution']}")
        print(f"  - 跳帧: {config['frame_skip']}")
        print("\n💡 请重新启动应用来应用新配置:")
        print("   python3 ./MC_web.py")
        
    except Exception as e:
        print(f"❌ 应用配置失败: {e}")

def custom_config(config_file):
    """自定义配置"""
    print("\n自定义配置")
    print("-" * 60)
    
    models = ['yolov8n.pt', 'yolov5nu.pt']
    print("可用模型:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    model_choice = input("选择模型 (1-2): ").strip()
    model = models[int(model_choice)-1] if model_choice in ['1', '2'] else models[0]
    
    width = input("输入宽度 (默认320): ").strip() or "320"
    height = input("输入高度 (默认240): ").strip() or "240"
    frame_skip = input("输入跳帧间隔 (默认6): ").strip() or "6"
    
    config = {
        'name': 'Custom Config',
        'model': model,
        'resolution': f"{width}x{height}",
        'frame_skip': frame_skip,
        'desc': '自定义配置'
    }
    
    apply_config(config_file, config)

if __name__ == '__main__':
    show_menu()
