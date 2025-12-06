# Nenggong Zhiban — AI-Native Enterprise Office Automation Platform
一个前后端分离的综合 OA 办公自动化平台，涵盖用户与权限管理、文档管理、审批工作流、知识库检索、AI 助手、邮件系统与数据分析沙盒等模块。

## 技术栈
- 后端：FastAPI、SQLAlchemy、SQLite、Pydantic、PyJWT、Passlib、LangChain、FAISS、Ollama
- 前端：Vue 3、Vite、Pinia、Vue Router、Ant Design Vue、ECharts、Mermaid、Axios
- 工具与其他：Alembic 迁移、Docker、日志与异常中间件

## 目录结构
```
.
├─ backend/              # 后端服务
│  ├─ api/               # 业务接口（认证、审批、文档、邮件、聊天、文件、沙盒等）
│  ├─ config/            # 配置（settings、email_config、workflow 配置等）
│  ├─ database/          # 数据库会话与基类
│  ├─ models/            # 领域模型（用户、权限、部门、文档、审批等）
│  ├─ services/          # 业务服务（智能代理、审批引擎、沙盒等）
│  ├─ utils/             # 工具集（安全、日志、异常处理、工作流解析）
│  ├─ knowledge_base/    # 知识库加载与向量存储
│  ├─ alembic/           # 数据库迁移（版本脚本）
│  ├─ data/              # 业务数据（documents/personal/knowledge/images）
│  ├─ faiss_index/       # 向量索引持久化
│  ├─ docker/            # 后端 Dockerfile
│  ├─ app.py             # FastAPI 入口（端口默认 8000）
│  ├─ init_db.py         # 初始化 SQLite 表与测试数据
│  └─ requirements.txt   # 后端依赖
├─ frontend/             # 前端应用
│  ├─ src/               # 源码（组件、路由、状态、API、工具等）
│  ├─ public/            # 静态资源
│  ├─ dist/              # 构建产物
│  ├─ vite.config.js     # 开发代理到后端（/api → http://localhost:8000）
│  ├─ docker/            # 前端 Dockerfile
│  └─ package.json       # 前端依赖与脚本
├─ db_backups/           # 数据库备份
├─ faiss_index/          # 根级索引副本
├─ .env                  # 项目环境变量（后端读取）
└─ .gitignore
```

## 功能模块
- 认证与用户：登录获取 JWT、用户注册与信息获取、管理员权限校验
- 组织与权限：部门、职位、角色与权限表，用户角色/权限关联
- 文档中心：文档存储与附件管理，静态文件通过 `/files` 暴露
- 审批工作流：流程定义、实例、节点与历史记录；支持撤回、详情等接口
- 工作流设计器：可视化设计与权限控制（管理员/设计者）
- AI 助手与聊天：基于 Ollama + LangChain 的对话与意图识别，支持“撰写邮件/发起审批/创建用户/创建工作流”等智能建议
- 知识库检索：FAISS 向量索引，支持 PDF/文本内容加载与检索融合
- 邮件系统：邮件表单与集成指引，支持主题/正文/收件人智能提取与生成
- 沙盒分析：文件上传与基本分析流程演示

## 快速开始
### 环境准备
- Python ≥ 3.9（建议 3.10/3.12）
- Node.js ≥ 18（Vite 6 需 Node 18+）
- 可选：Ollama（本地 LLM，默认地址 `http://localhost:11434`）

### 后端启动
- 安装依赖：
  ```bash
  cd backend
  python -m venv .venv
  .venv\Scripts\activate  # Windows
  pip install -r requirements.txt
  ```
- 初始化数据库（首次可选，应用启动会自动执行）：
  ```bash
  python init_db.py
  ```
- 启动服务：
  ```bash
  python app.py
  # 或
  uvicorn backend.app:app --host 0.0.0.0 --port 8000
  ```
- 默认地址：`http://localhost:8000`，API 前缀：`/api`

### 前端启动
- 安装依赖并运行开发服务器：
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
- 默认地址：`http://localhost:5173`
- 通过 `vite.config.js` 已代理 `/api` 到后端 `http://localhost:8000`

## 环境变量
- 根目录 `.env`（后端读取）：
  - `DATABASE_URL=sqlite:///./oa.db`
  - `SECRET_KEY=...`、`ALGORITHM=HS256`、`ACCESS_TOKEN_EXPIRE_MINUTES=30`
  - `ALLOWED_ORIGINS=http://localhost:5173,...`
  - `SANDBOX_URL=http://localhost:8002/api/sandbox/v1`
- 前端 `frontend/.env`：
  - `VITE_API_URL=http://localhost:8000`

## 认证与默认账号
- 首次启动会自动初始化数据库与管理员账号：`admin / admin`
- 开发模式下部分接口对 Token 容忍度较高，生产环境请关闭模拟并更换 `SECRET_KEY`

## AI 聊天与智能代理
- 需要本地运行 Ollama 并拉取模型（例如 `deepseek-r1:7b`）：
  - 安装与启动参考 https://ollama.com
  - 常见端点：`http://localhost:11434`
- 初始化逻辑会自动探测与选择可用模型；若不可用则降级至普通模式
- 智能代理可识别并生成以下操作建议：撰写邮件、创建审批、创建用户、创建工作流等

## 知识库与文件
- 后端 `backend/data/` 用于业务数据与静态文件挂载（通过 `/files` 访问）
- 向量索引存放 `backend/faiss_index/`，应用在首次启动时自动初始化/检查
- 可将 PDF 放入 `backend/data/documents/` 后重启或编写脚本重建索引

## API 概览（部分）
- 认证：`/api/auth/token`（表单登录，返回 JWT）
- 用户：`/api/users/...`
- 文档：`/api/documents/...`、静态文件 `/files/...`
- 审批：`/api/approval/...`、工作流：`/api/workflow-auth/...`
- 聊天：`/api/chat/...`（依赖 Ollama 与向量检索）
- 沙盒：`/api/sandbox/...`

## Docker（可选）
- 后端镜像：
  ```bash
  cd backend
  docker build -t oa-backend .
  docker run -p 8001:8001 oa-backend
  ```
  后端 Dockerfile 默认监听 `8001`，与本地开发 `8000` 不同，可按需调整。
- 前端镜像（开发态示例）：
  ```bash
  cd frontend
  docker build -t oa-frontend .
  docker run -p 3000:3000 oa-frontend
  ```
  注意：当前 Dockerfile 使用 `npm start`，需调整为实际脚本（如 `npm run dev` 或生产用 `npm run preview`）。

## 注意事项
- 安全：生产环境务必更换 `SECRET_KEY`、关闭开发模式与模拟 Token、限制 CORS
- 模型：AI 聊天依赖 Ollama，本地未运行时功能会回退
- 端口：后端本地默认 `8000`，容器示例为 `8001`；前端开发默认 `5173`
- 数据：首次运行会创建 SQLite 文件 `oa.db` 与基础数据/管理员账号

## 常用命令
```bash
# 后端
cd backend && pip install -r requirements.txt && python app.py

# 前端
cd frontend && npm install && npm run dev

# 数据初始化（可选）
cd backend && python init_db.py
```

