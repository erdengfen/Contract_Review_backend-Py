"""
review_task 真实端到端联调入口。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.config.config import settings
from app.models.contract import ContractFile
from app.models.model_configs import ModelConfig
from app.models.session_message import Session
from app.models.user import User

DEFAULT_SAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "review_task_minimal_sample.json"


def load_sample_manifest(sample_path: Path) -> dict[str, Any]:
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_contract_sample_path(sample_manifest: dict[str, Any]) -> Path:
    relative_path = sample_manifest["contract_file"]["contract_content_relative_path"]
    return Path(__file__).resolve().parents[3] / relative_path


def sanitize_model_config(model_config: ModelConfig | None) -> dict[str, Any] | None:
    if model_config is None:
        return None
    return {
        "id": model_config.id,
        "model_name": model_config.model_name,
        "model_type": model_config.model_type,
        "provider": model_config.provider,
        "api_endpoint": model_config.api_endpoint,
        "temperature": model_config.temperature,
        "top_p": model_config.top_p,
        "max_tokens": model_config.max_tokens,
        "is_default": model_config.is_default,
        "status": model_config.status,
    }


def summarize_review_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total_events": len(events),
        "event_types": {},
        "message_count": 0,
        "first_message": None,
        "end_event": None,
    }
    for event in events:
        event_name = event.get("event", "unknown")
        summary["event_types"][event_name] = summary["event_types"].get(event_name, 0) + 1
        if event_name == "message":
            summary["message_count"] += 1
            if summary["first_message"] is None:
                summary["first_message"] = event.get("data")
        if event_name == "end":
            summary["end_event"] = event.get("data")
    return summary


def prepare_review_task_sample(db, sample_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    将最小联调样本写入数据库。
    """
    user_spec = sample_manifest["user"]
    contract_spec = sample_manifest["contract_file"]
    session_spec = sample_manifest["session"]
    model_spec = sample_manifest["default_chat_model"]
    contract_path = resolve_contract_sample_path(sample_manifest)
    api_key = os.getenv(model_spec["api_key_env"]) or settings.openai_config.api_key
    if not api_key:
        raise ValueError(
            f"准备默认模型样本时缺少 API Key，请设置环境变量 {model_spec['api_key_env']}。"
        )

    user = db.query(User).filter(User.id == user_spec["id"]).first()
    if user is None:
        user = User(
            id=user_spec["id"],
            username=user_spec["username"],
            password="review-task-validation-only",
            is_active=1,
            employee_id="review-task-validation",
            department="rag",
            role=1,
        )
        db.add(user)
    else:
        user.username = user_spec["username"]
        user.is_active = 1

    contract = db.query(ContractFile).filter(ContractFile.id == contract_spec["id"]).first()
    if contract is None:
        contract = ContractFile(id=contract_spec["id"])
        db.add(contract)
    contract.user_id = user_spec["id"]
    contract.type = contract_spec["type"]
    contract.title = contract_spec["title"]
    contract.file_path = str(contract_path)
    contract.file_type = contract_spec["file_type"]
    contract.party_a = contract_spec["party_a"]
    contract.party_b = contract_spec["party_b"]
    contract.amount = contract_spec["amount"]
    contract.status = "parsed"
    contract.contract_content_path = str(contract_path)

    session = db.query(Session).filter(Session.id == session_spec["id"]).first()
    if session is None:
        session = Session(id=session_spec["id"])
        db.add(session)
    session.file_id = contract_spec["id"]
    session.user_id = user_spec["id"]
    session.title = session_spec["title"]
    session.session_type = session_spec["session_type"]

    db.query(ModelConfig).filter(
        ModelConfig.model_type == model_spec["model_type"],
        ModelConfig.id != model_spec["id"],
    ).update({"is_default": 0}, synchronize_session=False)
    model = db.query(ModelConfig).filter(ModelConfig.id == model_spec["id"]).first()
    if model is None:
        model = ModelConfig(id=model_spec["id"])
        db.add(model)
    model.model_name = model_spec["model_name"]
    model.model_type = model_spec["model_type"]
    model.provider = model_spec["provider"]
    model.api_endpoint = model_spec["api_endpoint"]
    model.api_key = api_key
    model.temperature = model_spec["temperature"]
    model.top_p = model_spec["top_p"]
    model.presence_penalty = model_spec["presence_penalty"]
    model.frequency_penalty = model_spec["frequency_penalty"]
    model.max_tokens = model_spec["max_tokens"]
    model.is_default = 1
    model.status = "active"

    db.commit()
    return {
        "user_id": user.id,
        "session_id": session.id,
        "contract_file_id": contract.id,
        "contract_content_path": contract.contract_content_path,
        "default_model_id": model.id,
    }


async def run_review_task_validation(
    *,
    sample_path: Path,
    prepare_sample: bool,
    use_sample: bool,
    session_id: int | None,
    user_id: int | None,
    stance: str | None,
    intensity: str | None,
    contract_type: str | None,
    description: str | None,
    max_concurrent: int | None,
    max_events: int | None,
) -> dict[str, Any]:
    from app.core.dependencies import SessionLocal
    from app.curd.contract_file import CRUDContract
    from app.curd.model_configs import get_default_model_by_type
    from app.curd.chat_session import CRUDSession
    from app.router.review_task import iter_review_task_events
    from app.schemas.review_task import ReviewTaskCreateRequest

    sample_manifest = load_sample_manifest(sample_path)
    db = SessionLocal()
    try:
        prepared = None
        if prepare_sample:
            prepared = prepare_review_task_sample(db, sample_manifest)

        request_spec = sample_manifest["review_request"]
        resolved_session_id = session_id or (sample_manifest["session"]["id"] if use_sample else None)
        if resolved_session_id is None:
            raise ValueError("未提供 session_id，且未启用最小样本。")

        session = await CRUDSession.get_session(db, resolved_session_id)
        if session is None:
            raise ValueError(f"会话不存在: session_id={resolved_session_id}")

        contract = await CRUDContract.get_contract_file(db, session.file_id)
        if contract is None:
            raise ValueError(f"合同文件不存在: file_id={session.file_id}")

        resolved_user_id = user_id or session.user_id or sample_manifest["user"]["id"]
        model_config = await get_default_model_by_type(db, model_type="chat")
        if model_config is None:
            raise ValueError("默认聊天模型配置不存在。")
        if not os.path.exists(contract.contract_content_path):
            raise FileNotFoundError(f"合同内容文件不存在: {contract.contract_content_path}")

        request = ReviewTaskCreateRequest(
            session_id=resolved_session_id,
            stance=stance or request_spec["stance"],
            intensity=intensity or request_spec["intensity"],
            contract_type=contract_type or request_spec["contract_type"],
            description=description or request_spec["description"],
            max_concurrent=max_concurrent or request_spec["max_concurrent"],
        )

        current_user = SimpleNamespace(id=resolved_user_id)
        events: list[dict[str, Any]] = []
        async for raw_event in iter_review_task_events(
            request=request,
            current_user=current_user,
            db=db,
        ):
            parsed_event = json.loads(raw_event)
            events.append(parsed_event)
            if max_events and len(events) >= max_events:
                break

        return {
            "prepared_sample": prepared,
            "request": request.model_dump(),
            "session": {
                "id": session.id,
                "user_id": session.user_id,
                "file_id": session.file_id,
                "title": session.title,
            },
            "contract_file": {
                "id": contract.id,
                "type": contract.type,
                "title": contract.title,
                "contract_content_path": contract.contract_content_path,
            },
            "default_model": sanitize_model_config(model_config),
            "event_summary": summarize_review_events(events),
            "events": events,
        }
    finally:
        db.close()


def _main_test_review_task_validation():
    fake_events = [
        {"event": "message", "data": {"index": 1}},
        {"event": "message", "data": {"index": 2}},
        {"event": "end", "data": {"summary": "完成"}},
    ]
    summary = summarize_review_events(fake_events)
    assert summary["message_count"] == 2
    assert summary["event_types"]["end"] == 1
    manifest = load_sample_manifest(DEFAULT_SAMPLE_PATH)
    assert manifest["session"]["id"] == 900001
    assert resolve_contract_sample_path(manifest).name == "review_task_minimal_contract.txt"
    print("review_task validation self test passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="review_task 真实端到端联调入口")
    parser.add_argument("--sample-path", default=str(DEFAULT_SAMPLE_PATH), help="最小联调样本清单路径")
    parser.add_argument("--prepare-sample", action="store_true", help="按样本清单写入最小数据库记录")
    parser.add_argument("--use-sample", action="store_true", help="使用最小联调样本中的 session/request 配置")
    parser.add_argument("--session-id", type=int, help="待联调的 review session ID")
    parser.add_argument("--user-id", type=int, help="执行联调时使用的用户 ID")
    parser.add_argument("--stance", help="审阅立场")
    parser.add_argument("--intensity", help="审阅尺度")
    parser.add_argument("--contract-type", help="合同类型")
    parser.add_argument("--description", help="审阅说明")
    parser.add_argument("--max-concurrent", type=int, help="最大并发数")
    parser.add_argument("--max-events", type=int, help="仅消费前 N 个事件，便于快速排查")
    parser.add_argument("--self-test", action="store_true", help="执行文件内自测")
    args = parser.parse_args()

    if args.self_test:
        _main_test_review_task_validation()
    else:
        payload = asyncio.run(
            run_review_task_validation(
                sample_path=Path(args.sample_path),
                prepare_sample=args.prepare_sample,
                use_sample=args.use_sample or args.prepare_sample,
                session_id=args.session_id,
                user_id=args.user_id,
                stance=args.stance,
                intensity=args.intensity,
                contract_type=args.contract_type,
                description=args.description,
                max_concurrent=args.max_concurrent,
                max_events=args.max_events,
            )
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
