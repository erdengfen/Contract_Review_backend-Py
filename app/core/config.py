"""
应用配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 环境变量
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://127.0.0.1:8081/mcp/')

# 应用配置
APP_NAME = "合同审阅系统API"
APP_VERSION = "1.0.0"
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 文件路径配置
UPLOAD_DIR = "output/uploads"
RESULTS_DIR = "output/results"
SESSIONS_DIR = "output/sessions"
