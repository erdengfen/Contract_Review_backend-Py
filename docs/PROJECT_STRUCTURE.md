# 项目结构说明

## 重构后的项目结构

```
contract_review/
├── main.py                 # 原始文件（已清理，保留作为备份）
├── main_new.py            # 新的主应用入口
├── start_server.py        # 启动脚本
├── app/                   # 应用包
│   ├── __init__.py
│   ├── api/               # API层
│   │   ├── __init__.py
│   │   ├── routes.py      # API路由
│   │   └── models.py      # API数据模型
│   ├── core/              # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py      # 配置管理
│   │   └── llm.py         # LLM初始化
│   ├── services/          # 业务服务层
│   │   ├── __init__.py
│   │   ├── chat_service.py        # 聊天服务
│   │   ├── contract_review.py     # 合同审阅服务
│   │   └── document_processor.py  # 文档处理服务
│   └── utils/             # 工具模块
│       ├── __init__.py
│       └── mcp_client.py  # MCP客户端工具
├── requirements.txt       # 依赖包
├── API_USAGE.md          # API使用文档
└── output/               # 输出目录
    ├── uploads/          # 上传的文档
    ├── results/          # 修改后的文档和报告
    └── sessions/         # 会话状态
```

## 架构说明

### 1. 分层架构
- **API层** (`app/api/`): 处理HTTP请求和响应
- **服务层** (`app/services/`): 业务逻辑处理
- **工具层** (`app/utils/`): 通用工具和客户端
- **核心层** (`app/core/`): 配置和基础组件

### 2. 职责分离
- **routes.py**: 只负责API路由定义
- **models.py**: 只负责数据模型定义
- **services/**: 各服务类负责特定业务逻辑
- **utils/**: 通用工具和外部服务调用

### 3. 依赖注入
- 服务之间通过构造函数注入依赖
- 便于测试和模块替换

## 启动方式

```bash
# 使用新的启动脚本
python start_server.py

# 或直接运行新的主文件
python main_new.py
```

## 优势

1. **代码清晰**: 每个文件职责单一，易于理解
2. **易于维护**: 修改某个功能只需要修改对应的服务类
3. **便于测试**: 可以单独测试每个服务类
4. **可扩展性**: 新增功能只需要添加新的服务类
5. **符合标准**: 遵循Python后端项目的最佳实践
