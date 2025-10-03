#!/usr/bin/env python3
"""
测试合同审阅系统API
"""

import requests
import json
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    response = requests.get(f"{API_BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.status_code == 200

def test_upload():
    """测试文档上传"""
    print("\n📤 测试文档上传...")
    
    # 查找测试文档
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ data目录不存在")
        return None
    
    docx_files = list(data_dir.glob("*.docx"))
    if not docx_files:
        print("❌ 未找到.docx文件")
        return None
    
    test_file = docx_files[0]
    print(f"📄 使用测试文件: {test_file}")
    
    with open(test_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{API_BASE_URL}/api/upload", files=files)
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result.get('session_id') if response.status_code == 200 else None

def test_chat(session_id, message):
    """测试聊天功能"""
    print(f"\n💬 测试聊天: {message}")
    
    response = requests.post(f"{API_BASE_URL}/api/chat", json={
        "message": message,
        "session_id": session_id,
        "action": "chat"
    })
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_session_info(session_id):
    """测试会话信息"""
    print(f"\n📊 测试会话信息...")
    
    response = requests.get(f"{API_BASE_URL}/api/session/{session_id}")
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def main():
    """主测试函数"""
    print("🧪 开始测试合同审阅系统API")
    print("=" * 50)
    
    # 测试健康检查
    if not test_health():
        print("❌ 健康检查失败，请确保API服务正在运行")
        return
    
    # 测试文档上传
    session_id = test_upload()
    if not session_id:
        print("❌ 文档上传失败")
        return
    
    # 测试会话信息
    test_session_info(session_id)
    
    # 测试聊天功能
    test_chat(session_id, "你好，请介绍一下你的功能")
    test_chat(session_id, "请帮我审阅这份合同")
    
    # 等待一下让审阅完成
    time.sleep(2)
    
    # 再次测试会话信息，查看是否有修改建议
    test_session_info(session_id)
    
    print("\n✅ 测试完成！")
    print(f"📝 会话ID: {session_id}")
    print(f"🔗 修改后文档: {API_BASE_URL}/api/download/{session_id}/modified")
    print(f"📄 审阅报告: {API_BASE_URL}/api/download/{session_id}/report")

if __name__ == "__main__":
    main()
