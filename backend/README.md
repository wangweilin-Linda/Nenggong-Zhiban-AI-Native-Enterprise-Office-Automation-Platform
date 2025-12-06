# OA系统后端

OA系统的后端实现，基于FastAPI和SQLAlchemy开发。

## 技术栈

- FastAPI: 高性能API框架
- SQLAlchemy: ORM数据库操作
- Pydantic: 数据验证
- PyJWT: 用户认证
- SQLite: 本地数据存储
- Langchain: AI集成
- PyPDF2: PDF文件处理

## 项目结构

```
backend/
├── api/               # API路由和控制器
│   ├── auth.py        # 认证API
│   ├── chat.py        # AI聊天API
│   ├── documents.py   # 文档管理API
│   ├── email.py       # 邮件系统API
│   ├── files.py       # 文件操作API
│   └── workflow.py    # 工作流API
├── config/            # 配置文件
├── data/              # 上传文件和数据
│   └── documents/     # PDF文档存储目录
├── database/          # 数据库连接和模型
├── faiss_index/       # 向量索引
├── knowledge_base/    # 知识库操作
├── middlewares/       # 中间件
├── models/            # 数据模型
│   ├── document/      # 文档相关模型
│   └── user/          # 用户相关模型
├── models_embeddings/ # 嵌入模型
├── scripts/           # 脚本工具
│   └── rebuild_documents.py # 重建文档索引脚本
├── services/          # 业务逻辑
├── utils/             # 工具函数
├── uploads/           # 上传文件目录
├── approval_configs/  # 审批配置
├── migrations/        # 数据库迁移记录
├── app.py             # 主应用入口
├── models.py          # 模型定义
├── oa.db              # 主数据库
├── documents.db       # 文档数据库
└── requirements.txt   # 后端依赖
```

## 启动后端

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（如果是第一次运行）
python init_db.py

# 启动后端服务
python app.py
```

## API文档

启动服务后可访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要功能模块

### 文档管理功能

文档管理功能由`api/documents.py`实现，主要特点：

1. **自动扫描与导入**
   - 系统启动时自动扫描`data/documents`目录中的PDF文件
   - 解析文件名提取标题、发布时间和发布单位信息
   - 提取PDF文件内容用于全文检索
   - 防止重复导入相同文件

2. **文档API接口**
   - `/api/documents/list`：获取文档列表，支持分页、排序和搜索
   - `/api/documents/{doc_id}`：获取单个文档详情
   - `/api/documents/attachment/{filename}`：下载文档附件

3. **文档数据库模型**
   ```python
   # 文档模型结构
   class Document(Base):
      id = Column(Integer, primary_key=True)
      title = Column(String(200))           # 文档标题
      publish_time = Column(String(50))     # 发布时间
      publish_unit = Column(String(100))    # 发布单位
      content = Column(Text)                # 文档内容
      attachments = Column(Text)            # 附件列表（JSON格式）
      status = Column(String(20))           # 文档状态
      document_type = Column(String(50))    # 文档类型
   ```

4. **维护工具**
   - 提供`rebuild_documents.py`脚本用于重建文档索引
   - 提供清理和检查功能，确保文档数据完整性

### 用户认证

使用JWT Token实现用户认证，主要API：
- `/api/auth/token`: 获取访问令牌
- `/api/auth/me`: 获取当前用户信息

### 工作流管理

支持自定义审批流程，主要API：
- `/api/workflow/templates`: 获取工作流模板
- `/api/workflow/instances`: 管理工作流实例

### AI集成

通过Langchain集成大语言模型，提供智能助手功能：
- `/api/chat/message`: 发送聊天消息
- `/api/chat/history`: 获取聊天历史

## 文档命名规范

为了让系统正确提取文档信息，推荐使用以下格式命名PDF文件：

```
标题_日期_发布单位.pdf
```

例如：
- `员工手册_2024-05-07_人力资源部.pdf`
- `季度销售报告_2024-05-13_销售部.pdf`

系统会自动解析文件名，提取标题、日期和发布单位信息。 