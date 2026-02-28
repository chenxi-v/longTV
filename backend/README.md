# TVBox 爬虫后端服务

基于 FastAPI 的后端服务，用于实现 TVBox type: 3 爬虫源功能。

## 功能特性

- 加载和执行 Python 爬虫脚本
- 提供与 TVBox 兼容的 RESTful API 接口
- 支持多爬虫实例管理
- 支持远程加载和本地上传爬虫脚本
- 内置缓存机制提升性能
- 支持 Cloudflare Workers 图片代理加速

## 技术栈

- Python 3.10+
- FastAPI
- uvicorn
- requests
- pycryptodome

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # 主应用入口
│   ├── api.py               # API 路由
│   ├── spider_manager.py    # 爬虫管理器
│   ├── spider_instance.py   # 爬虫实例
│   ├── tvbox_parser.py      # TVBox配置解析器
│   ├── base/
│   │   ├── __init__.py
│   │   └── spider.py        # 爬虫基类
│   └── spiders/             # 爬虫脚本目录
│       ├── __init__.py
│       └── example.py       # 示例爬虫
├── requirements.txt
├── Dockerfile
└── README.md
```

## 快速开始

### 本地开发

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 使用 Docker

```bash
docker build -t tvbox-backend .
docker run -p 8000:8000 tvbox-backend
```

### 访问接口

- 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/health`
- API 接口: `http://localhost:8000/api/`

## API 接口

### 获取分类列表
`GET /api/classify`

### 获取分类下的视频列表
`GET /api/videos?t={分类ID}&pg={页码}`

### 获取视频详情
`GET /api/detail?id={视频ID}`

### 搜索视频
`GET /api/search?kw={关键词}&pg={页码}`

### 获取播放地址
`GET /api/playurl?flag={播放源}&id={视频链接}`

## 如何使用

1. 运行后端服务
2. 通过 `/api/add-python-spider` 接口添加爬虫
3. 或者通过 `/api/import-tvbox-config` 接口导入 TVBox 配置
4. 使用 API 接口获取视频数据

## 环境变量

- `CACHE_TTL`: 缓存过期时间（秒），默认为 300
- `MAX_WORKERS`: 最大并发数，默认为 10
- `PROXY_URL`: 代理服务器地址（可选）