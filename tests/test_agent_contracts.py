"""Agent 契约结构测试。

本测试验证 Step 3 契约字段、默认值、序列化和禁止字段，不连接外部服务。
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.agent.contracts import (
    AgentError,
    ChatDonePayload,
    ChatMessage,
    ChatRequest,
    ChatResponseChunk,
    ContractFileSnapshot,
    ContractInfoExtraction,
    DocumentBlock,
    DocumentContentRef,
    DocumentIntakeRequest,
    DocumentIntakeResponse,
    KnowledgeHit,
    ParsedDocument,
    ReviewExecutionOptions,
    ReviewRequest,
    ReviewResponse,
    ReviewRiskItem,
    ReviewStreamEvent,
    ReviewTaskSnapshot,
    SessionSnapshot,
    SourceLocation,
)


def _build_session() -> SessionSnapshot:
    """构造旧版会话字段快照。"""

    return SessionSnapshot(
        session_id=10,
        file_id=20,
        user_id=30,
        title="合同审阅会话",
        session_type="review",
        created_at=datetime(2026, 5, 10, 10, 0, 0),
        updated_at=datetime(2026, 5, 10, 10, 1, 0),
    )


def _build_contract() -> ContractFileSnapshot:
    """构造旧版合同文件字段快照。"""

    return ContractFileSnapshot(
        file_id=20,
        user_id=30,
        type="parsed",
        title="服务合同.docx",
        file_path="/uploads/30/service.docx",
        file_type="docx",
        upload_time=datetime(2026, 5, 10, 9, 0, 0),
        status="uploaded",
        party_a="甲方公司",
        party_b="乙方公司",
        amount=100000.0,
        is_accepted=0,
        contract_content_path="/oss/service.txt",
        contract_type_id=1,
        review_position=1,
        file_url="/static/30/service.docx",
    )


def _build_task() -> ReviewTaskSnapshot:
    """构造旧版审阅任务字段快照。"""

    return ReviewTaskSnapshot(
        task_id=100,
        session_id=10,
        file_id=20,
        user_id=30,
        type="review",
        stance="甲方",
        intensity="严格",
        effective_intensity="标准",
        contract_type="服务类合同",
        description="关注付款和违约责任",
        status="processing",
        max_concurrent=20,
    )


def test_review_contract_carries_legacy_business_fields() -> None:
    """审阅契约应完整承接旧审阅链路中的业务字段。"""

    block = DocumentBlock(
        block_id="20-1-1",
        text="付款条款",
        source_location=SourceLocation(file_path="/uploads/30/service.docx", page_number=1),
    )
    request = ReviewRequest(
        task=_build_task(),
        session=_build_session(),
        contract=_build_contract(),
        document=DocumentContentRef(
            file_path="/uploads/30/service.docx",
            file_type="docx",
            contract_content_path="/oss/service.txt",
            filename="服务合同.docx",
            title="服务合同.docx",
            content_source="contract_content_path",
        ),
        options=ReviewExecutionOptions(
            max_concurrent=20,
            requested_intensity="严格",
            effective_intensity="标准",
            stance="甲方",
            contract_type="服务类合同",
            description="关注付款和违约责任",
        ),
        prebuilt_blocks=[block],
    )

    data = request.model_dump()
    assert data["task"]["effective_intensity"] == "标准"
    assert data["contract"]["party_a"] == "甲方公司"
    assert data["document"]["content_source"] == "contract_content_path"
    assert data["prebuilt_blocks"][0]["source_location"]["page_number"] == 1


def test_review_response_preserves_db_fields_and_extra_fields() -> None:
    """审阅结果应保留当前落库字段，并承接旧解析器扩展字段。"""

    item = ReviewRiskItem(
        index=1,
        position="修改点1",
        original_content="付款条款",
        risk_analysis="付款条件不明确",
        risk_level="中",
        suggested_content="明确付款条件和期限。",
        reason="减少履约争议",
        risk_type="付款条款",
        source_block_ids=["20-1-1"],
        knowledge_hit_ids=["external_legal_kb:law-1"],
    )
    response = ReviewResponse(task_id=100, session_id=10, file_id=20, items=[item])
    event = ReviewStreamEvent(event="message", data=item.model_dump(), sequence=1)

    assert response.items[0].original_content == "付款条款"
    assert response.items[0].risk_type == "付款条款"
    assert event.data["suggested_content"] == "明确付款条件和期限。"


def test_chat_contract_accepts_optional_user_and_history() -> None:
    """聊天契约应兼容旧版可选登录用户和历史消息结构。"""

    request = ChatRequest(
        session_id=11,
        user_id=None,
        file_id=20,
        content="请说明付款条款风险",
        parent_id=5,
        session=SessionSnapshot(session_id=11, file_id=20, user_id=None, session_type="chat"),
        contract=_build_contract(),
        history=[
            ChatMessage(role="user", content="请说明付款条款风险"),
            ChatMessage(role="assistant", content="存在付款期限不明确的问题"),
        ],
    )
    chunk = ChatResponseChunk(content="存在", sequence=1)
    done = ChatDonePayload(full_content="存在付款期限不明确的问题")

    assert request.user_id is None
    assert request.context_window_messages == 10
    assert request.history[0].role == "user"
    assert chunk.role == "assistant"
    assert done.full_content.endswith("问题")


def test_document_intake_contract_matches_upload_flow() -> None:
    """文件感知契约应承接上传保存路径、解析正文和合同信息抽取结果。"""

    intake_request = DocumentIntakeRequest(
        user_id=30,
        filename="服务合同.docx",
        file_type="docx",
        save_path="/uploads/30/service.docx",
        expected_contract_content_path="/oss/service.txt",
    )
    parsed = ParsedDocument(
        filename="服务合同.docx",
        file_type="docx",
        file_path="/uploads/30/service.docx",
        contract_content="付款条款",
        contract_content_path="/oss/service.txt",
        blocks=[DocumentBlock(block_id="20-1-1", text="付款条款")],
    )
    response = DocumentIntakeResponse(
        parsed_document=parsed,
        contract_info=ContractInfoExtraction(party_a="甲方公司", party_b="乙方公司", amount=100000.0),
    )

    assert intake_request.save_path == "/uploads/30/service.docx"
    assert response.parsed_document.contract_content_path == "/oss/service.txt"
    assert response.contract_info.amount == 100000.0


def test_knowledge_hit_has_current_rag_fields_without_version() -> None:
    """RAG 契约只承接当前命中字段，不引入知识库版本字段。"""

    hit = KnowledgeHit(
        source_collection="external_legal_kb",
        record_id="law-1",
        title="民法典",
        content="测试条文",
        score=0.91,
        article_no="第五百零九条",
        source_type="law",
    )

    assert hit.hit_id == "external_legal_kb:law-1"
    assert "knowledge_version" not in KnowledgeHit.model_fields
    with pytest.raises(ValidationError):
        KnowledgeHit(
            source_collection="external_legal_kb",
            record_id="law-1",
            title="民法典",
            content="测试条文",
            score=0.91,
            knowledge_version="v1",
        )


def test_forbidden_backend_and_model_fields_are_rejected() -> None:
    """契约层应拒绝 backend 内部对象和模型调用字段。"""

    with pytest.raises(ValidationError):
        ReviewRequest(
            task=_build_task(),
            session=_build_session(),
            contract=_build_contract(),
            document=DocumentContentRef(contract_content_path="/oss/service.txt"),
            api_key="secret",
        )

    with pytest.raises(ValidationError):
        AgentError(code="E", message="错误", stage="review", model_config={"name": "x"})


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
