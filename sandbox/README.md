# 安全数据分析平台

这是一个注重数据隐私保护的安全数据分析平台，使用Docker容器提供隔离的数据处理环境。

## 项目特点

- 安全的数据处理：所有数据在隔离的Docker容器中处理
- 自动数据清理：分析完成后自动删除所有数据
- 用户友好界面：简单直观的分析配置表单
- 多种图表支持：柱状图、折线图、散点图等

## 项目结构

```
.
├── src/                # 前端源代码
│   ├── components/     # React组件
│   ├── services/       # API服务接口
│   ├── App.jsx         # 主应用组件
│   ├── App.css         # 主应用样式
│   ├── index.js        # 入口文件
│   └── index.css       # 全局样式
├── public/             # 静态资源
├── backend/            # 后端代码
│   ├── Dockerfile      # Docker配置
│   ├── app.py          # 主应用入口
│   ├── docker-compose.yml # Docker编排
│   └── requirements.txt # 依赖列表
├── package.json        # 项目配置和依赖
└── package-lock.json   # 依赖锁定
```

## 快速开始

### 环境要求
- Node.js 16+
- Docker 和 Docker Compose
- npm 或 yarn

### 安装依赖

```bash
# 安装前端依赖
npm install
```

### 运行项目

```bash
# 启动后端服务
cd backend
docker-compose up -d

# 在新的命令行窗口启动前端
cd ..
npm start
```

### 停止服务

```bash
cd backend
docker-compose down  # 关闭所有容器
```

## 使用说明

1. 访问 http://localhost:3000 打开前端界面
2. 上传CSV数据文件进行分析
3. 配置分析选项并提交
4. 查看生成的分析结果和可视化图表

## 开发注意事项

- 前端使用React框架开发
- 后端API在Docker容器中运行，端口映射到本地
- 数据处理在隔离容器中完成，确保数据安全