# 多用户合同审阅系统使用指南

## 概述

本系统已升级支持多用户并发访问，解决了以下关键问题：

1. **多用户隔离**：每个用户的数据完全独立，互不干扰
2. **审阅记忆逻辑**：大模型能够了解前面分块的内容，避免断章取义
3. **高性能缓存**：使用Redis缓存提升响应速度
4. **会话管理**：支持用户会话的创建、恢复和清理

## 架构改进

### 存储方案
- **SQLite**：持久化存储用户会话、合同分块、审阅结果
- **Redis**：缓存活跃会话、审阅上下文、临时状态

### 审阅上下文管理
- 自动构建审阅上下文，包含：
  - 合同基本信息（甲乙方）
  - 前面分块的审阅结果摘要
  - 当前分块的前后文
  - 审阅指导信息

## 安装和配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 安装Redis
**Windows用户：**
```bash
# 使用Chocolatey安装
choco install redis-64

# 或使用启动脚本
python start_redis.py
```

**Linux/Mac用户：**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis
```

### 3. 配置环境变量
复制 `env_example.txt` 为 `.env` 并修改配置：

```bash
cp env_example.txt .env
```

关键配置项：
- `REDIS_URL`: Redis连接地址
- `SESSION_TIMEOUT`: 会话超时时间（秒）
- `MAX_CONCURRENT_SESSIONS`: 最大并发会话数

### 4. 启动服务
```bash
# 启动Redis（如果未自动启动）
redis-server

# 启动应用
python main_new.py
```

## API使用说明

### 1. 上传合同文档
```http
POST /api/upload
Content-Type: multipart/form-data

user_id: "user123"
session_id: "session456"  # 可选，不提供会自动生成
file: [合同文件]
```

### 2. 开始审阅对话
```http
POST /api/chat
Content-Type: application/json

{
    "message": "请审阅这份合同",
    "user_id": "user123",
    "session_id": "session456",
    "role": "甲方",
    "contract_type": "service"
}
```

### 3. 获取用户会话列表
```http
GET /api/sessions/{user_id}
```

### 4. 获取特定会话信息
```http
GET /api/session/{user_id}/{session_id}
```

### 5. 下载审阅结果
```http
GET /api/download/{user_id}/{session_id}/modified
GET /api/download/{user_id}/{session_id}/report
```

### 6. 删除会话
```http
DELETE /api/session/{user_id}/{session_id}
```

## 多用户特性

### 用户隔离
- 每个用户的数据通过 `user_id` 完全隔离
- 文件存储路径包含用户ID，避免冲突
- 数据库查询都基于用户ID过滤

### 会话管理
- 支持一个用户多个会话
- 会话自动过期清理
- 活跃会话缓存到Redis

### 审阅记忆
- 自动构建审阅上下文
- 包含前面分块的审阅结果
- 提供前后文信息避免断章取义

## 性能优化

### Redis缓存策略
- 活跃会话数据缓存1小时
- 合同分块数据缓存1小时
- 自动清理过期数据

### 数据库优化
- 用户ID和会话ID联合索引
- 定期清理旧数据
- 连接池管理

### 并发控制
- 支持多用户同时审阅
- 会话级别的数据隔离
- 异步处理提升性能

## 监控和维护

### 健康检查
```http
GET /api/health
```

### 清理过期数据
系统会自动清理30天前的数据，也可手动清理：
```python
from app.core.database import DatabaseManager
db = DatabaseManager()
db.cleanup_old_sessions(days=30)
```

### Redis监控
```bash
# 查看Redis状态
redis-cli info

# 查看连接数
redis-cli info clients

# 查看内存使用
redis-cli info memory
```

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis是否启动：`redis-cli ping`
   - 检查连接配置：`REDIS_URL`

2. **会话数据丢失**
   - 检查Redis是否运行
   - 查看数据库连接是否正常

3. **审阅上下文不完整**
   - 检查合同分块是否正确保存
   - 查看Redis缓存是否正常

4. **多用户数据混乱**
   - 确保API调用时提供了正确的 `user_id`
   - 检查数据库查询是否正确过滤

### 日志查看
```bash
# 查看应用日志
tail -f app.log

# 查看Redis日志
tail -f /var/log/redis/redis-server.log
```

## 扩展建议

### 1. 用户认证
- 集成JWT认证
- 添加用户权限管理
- 实现单点登录

### 2. 数据持久化
- 考虑使用PostgreSQL替代SQLite
