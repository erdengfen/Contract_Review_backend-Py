#!/usr/bin/env python3
"""
Redis启动脚本
用于在Windows环境下启动Redis服务器
"""
import subprocess
import sys
import os
import time
from pathlib import Path

def check_redis_installed():
    """检查Redis是否已安装"""
    try:
        result = subprocess.run(['redis-server', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("Redis已安装")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("Redis未安装或未在PATH中")
    return False

def install_redis_windows():
    """在Windows上安装Redis"""
    print("正在尝试安装Redis...")
    try:
        # 尝试使用chocolatey安装
        subprocess.run(['choco', 'install', 'redis-64', '-y'], check=True)
        print("Redis安装成功")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Chocolatey未安装，请手动安装Redis")
        print("请访问: https://github.com/microsoftarchive/redis/releases")
        return False

def start_redis_server():
    """启动Redis服务器"""
    try:
        print("启动Redis服务器...")
        # 启动Redis服务器
        process = subprocess.Popen(['redis-server'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # 等待一下确保启动成功
        time.sleep(2)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print("Redis服务器启动成功")
            print("Redis运行在: redis://localhost:6379")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f" Redis启动失败: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f" 启动Redis失败: {e}")
        return None

def main():
    """主函数"""
    print(" Redis启动助手")
    print("=" * 50)
    
    # 检查Redis是否已安装
    if not check_redis_installed():
        if sys.platform == "win32":
            install_redis_windows()
        else:
            print("请手动安装Redis")
            return
    
    # 启动Redis服务器
    process = start_redis_server()
    if process:
        try:
            print("\n按 Ctrl+C 停止Redis服务器")
            process.wait()
        except KeyboardInterrupt:
            print("\n正在停止Redis服务器...")
            process.terminate()
            process.wait()
            print("Redis服务器已停止")

if __name__ == "__main__":
    main()
