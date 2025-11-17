from cas import CASClient
from app.core.config import CAS_VERSION,CAS_SERVER_URL,CAS_SERVICE_URL

cas_client = CASClient(
    version = CAS_VERSION,
    server_url = CAS_SERVER_URL,
    service_url = CAS_SERVICE_URL,
)

def get_login_url():
    """生成跳转到 CAS 登录页的 URL"""
    return cas_client.get_login_url()

def verify_ticket(ticket: str):
    """校验 CAS 返回的 ticket，并返回用户名"""
    username = cas_client.verify_ticket(ticket)
    return username

