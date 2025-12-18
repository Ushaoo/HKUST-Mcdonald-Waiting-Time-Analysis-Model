# MC 人群检测系统 - 集成版本

这是一个集成了YOLOv8人群检测和前端UI的完整应用，用于实时监测排队人数并预估取餐时间。

## 📁 项目结构

```
MC/
├── app.py                    # 主应用程序（集成MC_web.py的功能 + adding by zhc的前端）
├── config.py                 # 应用配置文件
├── data.py                   # 数据统计模块
├── templates/                # HTML模板文件夹
│   ├── index.html           # 首页 - 实时取餐预估
│   ├── history.html         # 历史数据页面
│   ├── upload.html          # 上传功能（可选）
│   └── ...
├── static/                   # 静态资源文件夹
│   ├── style.css            # 样式表
│   ├── chart.js             # 图表脚本
│   └── ...
├── uploads/                  # 上传文件存储夹（自动创建）
├── processed_videos/         # 处理后的视频存储夹（自动创建）
├── yolov8n.pt               # YOLO模型文件（需要提前下载）
└── README.md                # 本文件
```

## 🚀 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install flask opencv-python ultralytics numpy

# 或使用requirements.txt（如果有的话）
pip install -r requirements.txt
```

### 2. 下载模型文件

YOLOv8模型文件需要提前放到项目根目录：

```bash
# 下载yolov8n模型 (最轻量级，推荐)
# 可以在首次运行时自动下载，或从以下地址手动下载：
# https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n.pt

# 其他可用模型：
# - yolov8s.pt (small)
# - yolov8m.pt (medium)
# - yolov8l.pt (large)
# - yolov8x.pt (extra-large)
```

### 3. 启动应用

```bash
# 进入项目目录
cd /home/sunrise/MC

# 运行主程序
python3 app.py
```

应用将在 `http://localhost:5000` 启动。

## 🌐 访问方式

### 通过本地访问

```
主页 (首页):        http://localhost:5000/
历史数据:           http://localhost:5000/history
```

### 通过IP地址访问 (局域网)

```
主页:               http://<你的IP>:5000/
历史数据:           http://<你的IP>:5000/history
```

### 通过自定义域名访问 (可选)

修改 `config.py` 中的 `FLASK_CONFIG` 配置，或在系统hosts文件中添加域名映射。

## 📊 核心功能

### 1. 实时取餐预估（首页）

- **实时人流量显示**: 显示当前排队人数
- **取餐时间预估**: 根据实时人数智能估算取餐等待时间
- **人流量等级**: 显示当前人流量的拥挤程度（低/中等/高）
- **实时视频流**: 显示摄像头的实时视频（MJPEG格式）

#### 人流量与取餐时间对应关系：
- 人数 < 20: 取餐时间 2-5分钟（低流量）
- 人数 20-50: 取餐时间 8-12分钟（中等流量）
- 人数 > 50: 取餐时间 15-20分钟（高流量）

### 2. 历史数据分析（/history 路由）

- **周人流量趋势图**: 折线图显示每周每天的平均人流量
- **高峰时段统计**: 柱状图显示不同时段的人流量高峰
- **热力图分析**: 显示不同时段和不同日期的人流量分布

## 🔌 API 接口

### 实时数据 API

```
GET /api/realtime
```

响应示例：
```json
{
  "pickup_time": "8-12分钟",
  "crowd_level": "中等",
  "crowd_range": "约35人（当前）/ 平均45人 / 最高80人"
}
```

### 历史数据 API

```
GET /api/history
```

响应示例：
```json
{
  "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
  "peak_times": {
    "09:00": 20,
    "12:00": 60,
    "18:00": 40
  },
  "heatmap": [[10, 20, 30, 40], [15, 25, 35, 45], [20, 30, 40, 50]]
}
```

### 实时统计 API

```
GET /api/stats
```

响应示例：
```json
{
  "person_count": 35,
  "density": 0.38,
  "inference_time": 0.025,
  "confidence_threshold": 0.1,
  "frame_count": 1250
}
```

### 视频流

```
GET /video_feed
```

返回 MJPEG 格式的实时视频流，可在 `<img src="/video_feed">` 标签中使用。

### 图片上传

```
POST /upload
Content-Type: multipart/form-data

参数: file (图片文件)
```

响应示例：
```json
{
  "success": true,
  "person_count": 12,
  "density": 0.15,
  "image_url": "/static/result_20231218_150230.jpg"
}
```

## ⚙️ 配置文件说明 (config.py)

### Flask 应用配置

```python
FLASK_CONFIG = {
    'DEBUG': False,           # 调试模式（生产环境应为False）
    'HOST': '0.0.0.0',       # 监听IP地址
    'PORT': 5000,            # 监听端口
    'THREADED': True,        # 启用多线程
}
```

### 摄像头配置

```python
CAMERA_CONFIG = {
    'enabled': True,          # 是否启用摄像头
    'camera_id': 0,          # 摄像头ID（0为默认摄像头）
    'width': 1280,           # 分辨率宽度
    'height': 720,           # 分辨率高度
    'fps': 30,               # 帧率
    'quality': 70,           # JPEG质量 (1-100)
}
```

### YOLO 模型配置

```python
MODEL_CONFIG = {
    'enabled': True,                      # 是否启用模型
    'model_name': 'yolov8n.pt',          # 模型文件名
    'confidence_threshold': 0.1,          # 置信度阈值 (0.1-0.9)
    'detection_interval': 3,              # 每N帧进行一次检测
    'class_id': 0,                       # 只检测人（COCO类别0）
}
```

### 数据统计配置

```python
STATS_CONFIG = {
    'history_maxlen': 100,               # 保留最近N条检测结果
    'update_interval': 2000,             # 前端更新间隔（毫秒）
    'enable_hourly_stats': True,         # 启用小时统计
    'enable_daily_stats': True,          # 启用日统计
}
```

## 🔧 自定义配置

### 修改监听端口

编辑 `config.py`:
```python
FLASK_CONFIG = {
    'PORT': 8080,  # 改为8080
}
```

### 修改置信度阈值

编辑 `config.py`:
```python
MODEL_CONFIG = {
    'confidence_threshold': 0.5,  # 更严格的检测
}
```

更高的值 = 更严格的检测（误检少，可能漏检）
更低的值 = 更灵敏的检测（检测多，可能误检）

### 更换模型

编辑 `config.py`:
```python
MODEL_CONFIG = {
    'model_name': 'yolov8m.pt',  # 中等大小的模型，精度更高
}
```

## 🐛 故障排查

### 1. 摄像头无法打开
```bash
# 检查摄像头是否被占用
lsof | grep /dev/video
# 修改config.py中的camera_id
```

### 2. 模型加载失败
```bash
# 检查yolov8n.pt是否存在
ls -la yolov8n.pt
# 如果不存在，第一次运行会自动下载（需要网络）
```

### 3. 端口被占用
```bash
# 查看5000端口是否被占用
lsof -i :5000
# 修改config.py中的PORT配置
```

### 4. 视频流显示异常
- 检查网络连接
- 尝试刷新浏览器
- 检查浏览器是否支持MJPEG流

## 📈 性能调优

### 提高检测精度
- 增加模型大小: `yolov8s.pt` 或 `yolov8m.pt`
- 提高置信度阈值: `confidence_threshold: 0.3`
- 减少检测间隔: `detection_interval: 1`

### 降低资源占用
- 减少视频分辨率: `width: 640, height: 480`
- 增加检测间隔: `detection_interval: 5`
- 使用更轻的模型: `yolov8n.pt`

## 📝 日志输出

应用会在控制台输出日志信息，包括：
- 模型初始化信息
- 检测统计信息
- 错误和警告信息

## 🔐 安全性

- 文件上传大小限制: 500MB
- 允许的图片格式: PNG, JPG, JPEG, GIF, BMP
- 允许的视频格式: MP4, AVI, MOV, MKV, FLV, WMV
- 支持线程安全的并发访问

## 📚 使用示例

### Python 调用 API

```python
import requests

# 获取实时数据
response = requests.get('http://localhost:5000/api/realtime')
data = response.json()
print(f"取餐时间: {data['pickup_time']}")
print(f"人流量等级: {data['crowd_level']}")

# 获取历史数据
response = requests.get('http://localhost:5000/api/history')
data = response.json()
print(f"周人流量: {data['weekly_flow']}")
```

### JavaScript 调用 API

```javascript
// 获取实时数据
fetch('/api/realtime')
  .then(res => res.json())
  .then(data => {
    console.log('取餐时间:', data.pickup_time);
    console.log('人流量等级:', data.crowd_level);
  });

// 上传图片
const formData = new FormData();
formData.append('file', imageFile);

fetch('/upload', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => {
  console.log('检测到的人数:', data.person_count);
  console.log('结果图片:', data.image_url);
});
```

## 🔄 原始 MC_web.py 和 adding by zhc 说明

### 原始功能保留

- ✅ 原 MC_web.py 的所有功能已集成到新的 `app.py`
- ✅ YOLO8 检测功能完全保留
- ✅ 多线程后台检测机制保留
- ✅ 上传文件处理功能保留

### 前端改进

- ✅ 采用了 adding by zhc 设计团队的现代化 UI
- ✅ 更好的用户体验和交互
- ✅ 响应式设计支持多种设备

### 原有文件处理

- 原 `MC_web.py` 仍保留在项目根目录（备份）
- 原 `adding by zhc/` 文件夹仍保留（备份）
- 新的主程序使用统一的 `app.py` 

## 📞 支持

如有问题，请检查：
1. Python 版本 >= 3.7
2. 所有依赖包已正确安装
3. 摄像头硬件正常工作
4. 网络连接正常

## 📄 许可证

根据项目原始许可证规定。

---

**最后更新**: 2025-12-18
**版本**: 1.0 (集成版)
