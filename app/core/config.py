"""
应用配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 环境变量
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://0.0.0.0:8081/mcp/')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 应用配置
APP_NAME = "合同审阅系统API"
APP_VERSION = "1.0.0"
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 文件路径配置
UPLOAD_DIR = "output/uploads"
RESULTS_DIR = "output/results"
SESSIONS_DIR = "output/sessions"

# 会话配置
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1小时
MAX_CONCURRENT_SESSIONS = int(os.getenv('MAX_CONCURRENT_SESSIONS', '100'))

# CAS配置
CAS_SERVER_URL = os.getenv("CAS_SERVER_URL", "https://cas.example.com/cas/")
CAS_SERVICE_URL = os.getenv("CAS_SERVICE_URL", "http://localhost:8000/cas/login")
CAS_VERSION = int(os.getenv("CAS_VERSION", 3))