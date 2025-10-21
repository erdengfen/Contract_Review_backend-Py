#!/usr/bin/env python3
"""
测试多用户合同审阅系统API
"""
import requests
import json
import time
from pathlib import Path

API_BASE_URL = "http://0.0.0.0:8080"

def test_health():
    """测试健康检查"""
    print("测试健康检查...")
    response = requests.get(f"{API_BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.status_code == 200

def test_upload(user_id: str):
    """测试文档上传（多用户）"""
    print(f"\n测试文档上传 - 用户: {user_id}")
    
    # 查找测试文档
    data_dir = Path("data")
    if not data_dir.exists():
        print("data目录不存在")
        return None
    
    docx_files = list(data_dir.glob("*.docx"))
    if not docx_files:
        print(" 未找到.docx文件")
        return None
    
    test_file = docx_files[0]
    print(f" 使用测试文件: {test_file}")
    
    with open(test_file, 'rb') as f:
        files = {'file': f}
        data = {'user_id': user_id}
        response = requests.post(f"{API_BASE_URL}/api/upload", files=files, data=data)
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result.get('session_id') if response.status_code == 200 else None

def test_chat(user_id: str, session_id: str, message: str):
    """测试聊天功能（多用户）"""
    print(f"\n 测试聊天 - 用户: {user_id}, 消息: {message}")
    
    response = requests.post(f"{API_BASE_URL}/api/chat", json={
        "message": message,
        "user_id": user_id,
        "session_id": session_id,
        "action": "chat",
        "role": "甲方",
        "contract_type": "service"
    })
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        # 处理流式响应
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    print(f"流式响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                except:
                    pass
    else:
        result = response.json()
        print(f"错误响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200

def test_session_info(user_id: str, session_id: str):
    """测试会话信息（多用户）"""
    print(f"\n 测试会话信息 - 用户: {user_id}")
    
    response = requests.get(f"{API_BASE_URL}/api/session/{user_id}/{session_id}")
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_user_sessions(user_id: str):
    """测试用户会话列表"""
    print(f"\n 测试用户会话列表 - 用户: {user_id}")
    
    response = requests.get(f"{API_BASE_URL}/api/sessions/{user_id}")
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_multi_user():
    """测试多用户并发"""
    print("\n👥 测试多用户并发...")
    
    # 创建两个用户
    user1 = "user_001"
    user2 = "user_002"
    
    # 用户1上传文档
    session1 = test_upload(user1)
    if not session1:
        print(" 用户1文档上传失败")
        return
    
    # 用户2上传文档
    session2 = test_upload(user2)
    if not session2:
        print(" 用户2文档上传失败")
        return
    
    # 用户1开始审阅
    print(f"\n 用户1开始审阅...")
    test_chat(user1, session1, "请审阅这份合同")
    
    # 用户2开始审阅
    print(f"\n 用户2开始审阅...")
    test_chat(user2, session2, "请审阅这份合同")
    
    # 检查用户会话隔离
    print(f"\n 检查用户会话隔离...")
    test_user_sessions(user1)
    test_user_sessions(user2)
    
    # 等待审阅完成
    time.sleep(5)
    
    # 检查审阅结果
    test_session_info(user1, session1)
    test_session_info(user2, session2)

def main():
    """主测试函数"""
    print(" 开始测试多用户合同审阅系统API")
    print("=" * 60)
    
    # 测试健康检查
    if not test_health():
        print(" 健康检查失败，请确保API服务正在运行")
        print("请运行: python main_new.py")
        return
    
    # 测试单用户
    print("\n 测试单用户功能...")
    user_id = "test_user_001"
    session_id = test_upload(user_id)
    if not session_id:
        print(" 文档上传失败")
        return
    
    test_session_info(user_id, session_id)
    test_chat(user_id, session_id, "你好，请介绍一下你的功能")
    test_chat(user_id, session_id, "请审阅这份合同")
    
    # 等待审阅完成
    time.sleep(3)
    test_session_info(user_id, session_id)
    
    # 测试多用户并发
    test_multi_user()
    
    print("\n 测试完成！")
    print(" 测试用户ID: test_user_001")
    print(" API文档: http://localhost:8080/docs")

if __name__ == "__main__":
    main()
