# 法务合同审阅系统

基于LangGraph Supervisor的多智能体架构，集成Office-Word-MCP-Server的专业合同审阅系统。

## 🎯 系统特点

- **两步审阅流程**：合同审阅 → 合同修改
- **专业律师提示词**：基于专业合同审查律师的提示词模板
- **MCP集成**：支持Office-Word-MCP-Server进行文档处理
- **内容提取**：使用MCP工具自动提取合同完整内容，直接传递给大模型
- **智能分析**：使用DeepSeek LLM进行合同风险识别和修改建议
- **格式保持**：修改时保持合同原有格式和结构

## 🏗️ 核心组件

### 1. ContractReviewSystem
主要的审阅系统类，包含以下核心方法：

- `review_contract_content()` - 第一步：合同审阅
- `modify_contract()` - 第二步：合同修改
- `review_contract()` - 完整的两步审阅流程

### 2. 专业律师提示词
基于专业合同审查律师的提示词模板，包含：
- **Role**: 合同审查律师
- **Profile**: 专业背景和技能描述
- **Rules**: 基本原则和行为准则
- **Workflows**: 标准工作流程
- **OutputFormat**: 标准输出格式

### 3. MCP集成
- **内容提取**: 使用ReAct Agent让大模型决定使用哪个MCP工具
  - 大模型自主选择最合适的工具
  - 支持所有可用的MCP工具
  - 自动处理工具调用和结果解析
  - 智能重试和错误处理
- **文档处理**: 通过ReAct Agent调用Office-Word-MCP-Server工具
  - 文档复制和修改
  - 添加标题和段落
  - 保持文档格式
- **工具支持**: 支持所有MCP服务器提供的Word文档处理工具
- **依赖要求**: 必须启动MCP服务器才能进行文档处理

## 🔄 工作流程

### 第一步：合同审阅
1. **风险识别**: 快速识别合同中的法律风险和潜在纠纷点
2. **条款分析**: 深入分析合同条款的合理性和法律效力
3. **修改建议**: 提供专业、可行的合同修改方案

### 第二步：合同修改
1. **Agent调用**: 通过ReAct Agent调用MCP工具进行文档操作
2. **文档复制**: 使用MCP工具复制原文档
3. **修改说明**: 通过MCP工具添加详细的修改说明和风险分析
4. **格式保持**: 使用MCP工具保持合同原有格式和结构
5. **错误处理**: MCP失败时抛出异常，确保系统依赖MCP服务

## 📋 输出格式

### 修改点格式
每个修改点包含：
- **📄 原文内容**: 完整的原始条款文本
- **⚠️ 风险分析**: 法律风险分析
- **✏️ 修改后内容**: 修改后的完整条款文本

### 报告格式
- **Markdown报告**: 详细的审阅报告
- **JSON数据**: 结构化的审阅数据
- **修改后DOCX**: 包含修改说明的合同文件

## 🚀 快速开始

### 1. 环境准备
```bash
# 设置环境变量
export DEEPSEEK_API_KEY="your_api_key_here"

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动MCP服务器
```bash
# 启动Office-Word-MCP-Server
python start_mcp_server.py
```

### 3. 运行审阅
```bash
# 运行主程序
python main.py

# 或运行测试
python test_multi_agent.py
python test_mcp_only.py
python test_prompt_loading.py
```

## 📁 文件结构

```
contract_review/
├── main.py                    # 主程序
├── test_multi_agent.py        # 多智能体系统测试
├── test_mcp_only.py           # MCP-only系统测试
├── test_prompt_loading.py     # 提示词加载测试
├── start_mcp_server.py        # MCP服务器启动脚本
├── prompts/                   # 提示词文件目录
│   ├── contract_reviewer_prompt.txt  # 合同审查律师提示词
│   └── README.md              # 提示词系统说明
├── requirements.txt           # 依赖列表
├── data/                      # 合同文件目录
│   └── *.docx
└── output/                    # 输出目录
    ├── contract_review_report_*.md
    ├── contract_review_data_*.json
    └── modified_*.docx
```

## 配置说明

### 环境变量
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `MCP_SERVER_URL`: MCP服务器地址（默认：http://127.0.0.1:8080/mcp/）

### 依赖库
- `langchain`: LangChain框架
- `langgraph`: LangGraph框架
- `langchain-mcp-adapters`: MCP适配器
- `aiohttp`: 异步HTTP客户端

## 🔧 故障排除

### 常见问题

1. **MCP连接失败**
   - 检查MCP服务器是否启动
   - 验证服务器地址和端口
   - 系统会自动使用备选方案

2. **LLM调用失败**
   - 检查DEEPSEEK_API_KEY是否正确设置
   - 验证网络连接
   - 检查API配额

3. **文档处理错误**
   - 确保文档格式为.docx
   - 检查文件权限
   - 验证文件路径
   - 确保MCP服务器已启动并可访问

### 日志级别
系统使用INFO级别日志，可以通过修改logging配置调整日志详细程度。

## 📝 使用示例

```python
from main import ContractReviewSystem
import asyncio

async def example():
    # 创建审阅系统
    review_system = ContractReviewSystem()
    
    # 执行两步审阅流程
    result = await review_system.review_contract(
        contract_path="data/contract.docx",
        output_dir="output"
    )
    
    if result["success"]:
        print(f"审阅完成！")
        print(f"报告: {result['report_path']}")
        print(f"修改后合同: {result['modified_contract_path']}")

# 运行示例
asyncio.run(example())
```

## 📄 许可证

本项目仅供学习和研究使用，不构成正式法律意见。具体法律问题请咨询专业律师。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进系统功能。
