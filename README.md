# 八字算命 App 部署指南

## 项目结构

```
web-deployment/
├── index.html          # 前端页面
├── backend/            # 后端API
│   ├── main.py
│   ├── requirements.txt
│   └── Procfile
└── README.md
```

## 部署步骤

### 1. 部署后端 (Render)

1. 登录 [Render](https://render.com/)
2. 创建 new Web Service
3. 连接 GitHub 仓库或直接上传 `backend/` 文件夹
4. 设置环境变量：
   - `MINIMAX_API_KEY`: 你的API密钥
   - `LITELLM_MODEL`: mini-max/maxi-abel
5. 部署后会得到 API 地址，如：`https://bazi-api-xxxx.onrender.com`

### 2. 修改前端 API 地址

找到 `index.html` 中的：
```javascript
const API_BASE = 'https://bazi-api-xxxxx.render.com';
```
替换为实际的 Render API 地址

### 3. 部署前端 (Vercel)

1. 登录 [Vercel](https://vercel.com/)
2. 导入 `index.html` 或上传整个项目
3. 部署后得到前端地址，如：`https://bazi-fortune.vercel.app`

### 4. 分享

把 Vercel 的链接分享到微信即可

---

## 本地测试

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端 (用浏览器打开 index.html)
```

## API 环境变量

| 变量 | 值 |
|------|-----|
| MINIMAX_API_KEY | sk-xxx |
| LITELLM_MODEL | mini-max/maxi-abel |
| MINIMAX_API_BASE | https://api.minimax.io/v1 |