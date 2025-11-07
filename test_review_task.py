"""
测试新的审阅任务功能
"""
import requests

# 测试配置
BASE_URL = "http://localhost:8081"
USERNAME = "test_user"
PASSWORD = "test_password"

def test_review_task_flow():
    """测试完整的审阅任务流程"""
    
    # 1. 登录获取token
    login_data = {
        "identifier": USERNAME,
        "password": PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/api/user/login", json=login_data)
    if login_response.status_code != 200:
        print(f"登录失败: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(" 登录成功")
    
    # 2. 上传合同文件
    with open("data/校园主页升级改版服务合同.docx", "rb") as f:
        files = {"file": f}
        upload_response = requests.post(
            f"{BASE_URL}/api/contract/upload",
            files=files,
            headers=headers
        )
    
    if upload_response.status_code != 200:
        print(f"文件上传失败: {upload_response.text}")
        return
    
    upload_data = upload_response.json()
    file_id = upload_data["data"]["file_id"]
    print(f" 文件上传成功，合同ID: {file_id}")

    # 3. 创建审阅任务
    review_request = {
        "file_id": file_id,
        "stance": "甲方",
        "intensity": "标准",
        "description": "请对合同进行专业审阅"
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/review_task/create",
        json=review_request,
        headers=headers
    )
    
    if create_response.status_code != 200:
        print(f"创建审阅任务失败: {create_response.text}")
        return
    
    task_data = create_response.json()
    task_id = task_data["data"]["id"]
    print(f" 审阅任务创建成功，任务ID: {task_id}")
    
    # 4. 开始执行审阅任务
    start_response = requests.post(
        f"{BASE_URL}/api/review_task/start/{task_id}",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print(f"开始审阅任务失败: {start_response.text}")
        return
    
    print(" 审阅任务已开始执行")
    
    # 5. 监控审阅进度
    import time
    while True:
        progress_response = requests.get(
            f"{BASE_URL}/api/review_task/progress/{task_id}",
            headers=headers
        )
        
        if progress_response.status_code != 200:
            print(f"获取进度失败: {progress_response.text}")
            break
        
        progress_data = progress_response.json()
        progress = progress_data["data"]
        
        print(f"进度: {progress['current_chunk']}/{progress['total_chunks']} ({progress['percentage']}%) - {progress['message']}")
        
        if progress["status"] == "completed":
            print(" 审阅任务完成")
            break
        elif progress["status"] == "failed":
            print(" 审阅任务失败")
            break
        
        time.sleep(2)
    
    # 6. 获取审阅结果
    result_response = requests.get(
        f"{BASE_URL}/api/review_task/result/{task_id}",
        headers=headers
    )
    
    if result_response.status_code != 200:
        print(f"获取审阅结果失败: {result_response.text}")
        return
    
    result_data = result_response.json()
    result = result_data["data"]
    
    print(" 审阅结果:")
    print(f"整体风险等级: {result['result']['overall_risk']}")
    print(f"审阅摘要: {result['result']['summary']}")
    print(f"建议: {result['result']['suggestion']}")
    print(f"风险项数量: {len(result['risk_items'])}")
    
    # 7. 获取任务列表
    list_response = requests.get(
        f"{BASE_URL}/api/review_task/list",
        headers=headers
    )
    
    if list_response.status_code == 200:
        list_data = list_response.json()
        print(f"任务列表获取成功，共 {list_data['data']['total']} 个任务")
    
    print("测试完成！")

if __name__ == "__main__":
    test_review_task_flow()
