#!/usr/bin/env python3
"""
启动合同审阅系统API服务
"""

import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # 检查环境变量
    # if not os.getenv('DEEPSEEK_API_KEY'):
    #     print("❌ 请设置DEEPSEEK_API_KEY环境变量")
    #     print("例如: set DEEPSEEK_API_KEY=your_api_key_here")
    #     exit(1)
    
    # 确保输出目录存在
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "uploads").mkdir(exist_ok=True)
    (output_dir / "results").mkdir(exist_ok=True)
    (output_dir / "sessions").mkdir(exist_ok=True)
    
    print("🚀 启动合同审阅系统API服务...")
    print("📡 服务地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🔧 健康检查: http://localhost:8000/api/health")
    print("-" * 50)
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

