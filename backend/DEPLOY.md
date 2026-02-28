# Vercel 部署说明

## 部署步骤

### 1. 准备工作
确保backend目录包含以下文件：
- `api/index.py` - Serverless入口
- `requirements.txt` - Python依赖
- `app/` - 应用代码目录

### 2. 部署到Vercel

#### 方法1：通过Vercel CLI
```bash
cd backend
npm i -g vercel
vercel login
vercel
```

#### 方法2：通过Vercel Dashboard
1. 将backend目录推送到GitHub
2. 在Vercel Dashboard中导入项目
3. 设置根目录为 `backend`
4. Vercel会自动检测Python并部署

### 3. 部署后配置

部署成功后，Vercel会提供一个URL，例如：
`https://long.chenxi-v.de5.net`

API端点将是：
- 根路径: `https://long.chenxi-v.de5.net/`
- API路径: `https://long.chenxi-v.de5.net/api/*`

## 常见问题

### 问题1：404错误
- 检查部署日志，确认构建成功
- 确认API路径正确
- 检查vercel.json配置

### 问题2：连接失败
- 检查CORS配置
- 确认后端服务正常运行
- 查看Vercel Functions日志

### 问题3：超时错误
Vercel Serverless Functions有执行时间限制：
- Hobby计划: 10秒
- Pro计划: 60秒

如果爬虫请求超时，考虑：
- 优化爬虫代码
- 使用其他部署平台（Railway, Render, Fly.io）

## Vercel限制

⚠️ **注意事项**：
- Serverless函数有执行时间限制
- 不支持WebSocket
- 文件上传功能可能受限
- 爬脚本的动态加载可能需要调整

## 推荐替代方案

如果Vercel无法满足需求，建议使用：
- **Railway** - 完整的FastAPI支持
- **Render** - 免费计划，支持长时间运行
- **Fly.io** - 全球部署，支持WebSocket
