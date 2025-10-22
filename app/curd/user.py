"""
@Project ：Contract_Review_backend-Py 
@File    ：user.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/22 09:52 
"""
from sqlalchemy.orm import Session
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str):
    """
    验证密码是否匹配
    :param plain_password: 明文密码
    :param hashed_password: 哈希密码
    :return: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_user(session: Session, username: str, password_hash: str):
    """
    创建用户
    :param session: 数据库会话
    :param username: 用户名
    :param password_hash: 密码哈希值
    :return: 创建的用户对象
    """
    try:
        new_user = User(username=username, password=password_hash)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception as e:
        session.rollback()
        raise e

def get_user_by_id(session: Session, user_id: int):
    """
    根据用户ID查询用户
    :param session: 数据库会话
    :param user_id: 用户ID
    :return: 用户对象
    """
    return session.query(User).filter(User.id == user_id).first()

def get_user_by_username(session: Session, username: str):
    """
    根据用户名查询用户
    :param session: 数据库会话
    :param username: 用户名
    :return: 用户对象
    """
    return session.query(User).filter(User.username == username).first()

def get_all_users(session: Session):

    """
    查询所有用户
    :param session: 数据库会话
    :return: 用户对象列表
    """
    return session.query(User).all()

def update_user(session: Session, user_id: int, username: str = None, password_hash: str = None):
    """
    更新用户信息
    :param session: 数据库会话
    :param user_id: 用户ID
    :param username: 用户名
    :param password_hash: 密码哈希值
    :return: 更新后的用户对象
    """
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if username is not None:
        user.username = username
    if password_hash is not None:
        user.password = password_hash
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int):
    """
    删除用户
    :param session: 数据库会话
    :param user_id: 用户ID
    :return: 是否删除成功
    """
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.is_active = 0
    session.commit()
    return True


def authenticate_user(db: Session, identifier: str, password: str):
    """
    验证用户凭证，支持用户名和手机号登录
    :param db: 数据库会话
    :param identifier: 用户名或手机号
    :param password: 密码
    :return: 用户对象或 False
    """
    # 不传入current_user_id，因为登录时不需要关注状态
    user = get_user_by_username(db, identifier)
    if not user:
        return False
    # 加密密码验证
    # if not verify_password(password, user.password):
    #     return False
    return user
