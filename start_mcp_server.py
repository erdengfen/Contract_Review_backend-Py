#!/usr/bin/env python3
"""
启动Office-Word-MCP-Server的脚本
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_mcp_server():
    """检查MCP服务器是否正在运行"""
    try:
        response = requests.get("http://0.0.0.0:8081/mcp/",
                              headers={"Accept": "text/event-stream"},
                              timeout=5)
        # 在Streamable HTTP模式下，406状态码表示服务器要求text/event-stream
        # 这实际上表示服务器正在运行
        return response.status_code in [200, 406]
    except:
        return False

def start_mcp_server():
    """启动MCP服务器"""
    print("🚀 正在启动Office-Word-MCP-Server...")
    
    # 检查MCP服务器路径
    mcp_server_path = Path("../Office-Word-MCP-Server-main/setup_mcp.py")
    
    if not mcp_server_path.exists():
        print(f"❌ MCP服务器路径不存在: {mcp_server_path}")
        print("请确保Office-Word-MCP-Server-main目录存在")
        return False
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['HOST'] = '0.0.0.0'
        env['PORT'] = '8081'
        
        # 启动服务器，但工作目录设为contract_review
        process = subprocess.Popen([
            sys.executable, str(mcp_server_path)
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=Path.cwd())
        
        print(f"✅ MCP服务器已启动 (PID: {process.pid})")
        print("📍 服务器地址: http://127.0.0.1:8081/mcp/")
        print(f"📍 工作目录: {Path.cwd()}")
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        for i in range(10):
            time.sleep(1)
            if check_mcp_server():
                print("✅ MCP服务器启动成功！")
                return True
            print(f"  检查中... ({i+1}/10)")
        
        print("❌ MCP服务器启动超时")
        return False
        
    except Exception as e:
        print(f"❌ 启动MCP服务器失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("Office-Word-MCP-Server 启动器")
    print("=" * 50)
    
    # 检查是否已经运行
    if check_mcp_server():
        print("✅ MCP服务器已经在运行")
        return
    
    # 启动服务器
    if start_mcp_server():
        print("\n🎉 现在可以运行合同审阅系统了！")
        print("运行命令: python main.py")
    else:
        print("\n❌ 启动失败，请检查配置")

if __name__ == "__main__":
    main() 