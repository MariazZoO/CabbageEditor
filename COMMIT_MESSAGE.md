feat: 重构项目架构，实现客户端/服务端分离部署

## 核心改动

### 架构重构
- **main_test.py**: 统一入口，通过 APP_MODE 环境变量切换客户端/服务端模式
- **cpp_client.py**: C++ 引擎集成接口，提供 initialize()/run()/shutdown() API
- **main.py**: 重构支持双模式启动

### Docker 容器化
```
新增文件:
├── Dockerfile                       # Python 3.12-slim + Gunicorn
├── docker-compose.yml               # 端口 20100，资源限制 2C4G
├── deploy.sh / deploy.bat           # 自动化部署脚本
└── .dockerignore
```

### 网络服务 (Backend/network_service/)
- **server.py**: Flask HTTP API
  - `GET /healthz`: 健康检查
  - `POST /api/ai/message`: AI 对话
  - `POST /api/ai/generate-image`: 图片生成（返回 URL，不下载）

### 工具模块 (Backend/utils/)
- **cleanup.py**: 自动清理 Blockly 临时文件
- **hot_reload.py**: Python 脚本热重载
- **script_runner.py**: 统一脚本执行管理

### 配置优化
- 硬编码默认配置到 `app_config.py`，删除 `settings.ini`
- 优先级: 环境变量 > 用户配置 > 项目配置 > 默认值

### 依赖更新
- 新增: flask>=3.0.0, gunicorn>=23.0.0
- Docker 镜像自动过滤 PySide6 依赖，减少 ~500MB

## 破坏性变更
- `main.py` 重构：C++ 代码需适配新启动方式
- `settings.ini` 移除：需迁移到环境变量或 TOML

## 部署方式
```bash
# 客户端
python main_test.py

# 服务端 (Docker)
docker-compose up -d

# 健康检查
curl http://localhost:20100/healthz
```

## 统计
- 新增 11 个文件，修改 6 个，删除 2 个
- Docker 镜像: ~800MB

