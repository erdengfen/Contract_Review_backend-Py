"""方案 B 的 Router 规则。"""

from __future__ import annotations

import re
from collections import Counter

from .graph_state import IndexedChunk, RouterTask


SPECIALIST_PAYMENT = "付款 specialist"
SPECIALIST_LIABILITY = "违约 specialist"
SPECIALIST_DISPUTE = "争议 specialist"
SPECIALIST_DEFINITION = "定义 specialist"

ROUTER_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("payment", SPECIALIST_PAYMENT, ("付款", "预付款", "进度款", "结算", "价款", "验收")),
    ("liability", SPECIALIST_LIABILITY, ("违约", "赔偿", "免责", "责任", "索赔", "违约金")),
    ("dispute", SPECIALIST_DISPUTE, ("争议", "仲裁", "法院", "通知", "解除", "终止")),
    ("definition", SPECIALIST_DEFINITION, ("定义", "系指", "是指", "附件", "附表", "空白", "留空")),
]

REFERENCE_PATTERN = re.compile(
    r"(第[一二三四五六七八九十0-9]+条|附件[一二三四五六七八九十0-9A-Za-z]+|附表[一二三四五六七八九十0-9A-Za-z]+)"
)


def infer_chunk_tags(text: str) -> list[str]:
    """抽取 chunk 主题标签。"""
    tags: list[str] = []
    for topic, _, keywords in ROUTER_RULES:
        if any(keyword in text for keyword in keywords):
            tags.append(topic)
    return _unique(tags)


def extract_reference_tokens(text: str) -> list[str]:
    """抽取条款和附件引用。"""
    return _unique(list(REFERENCE_PATTERN.findall(text)))


def build_router_tasks(chunks: list[IndexedChunk]) -> tuple[list[RouterTask], dict]:
    """根据 chunk 信号构造路由任务。"""
    tasks: list[RouterTask] = []
    specialist_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()

    for chunk in chunks:
        route_topics: list[str] = []
        target_specialists: list[str] = []
        route_reasons: list[str] = []

        for topic, specialist_name, keywords in ROUTER_RULES:
            matched = [keyword for keyword in keywords if keyword in chunk["text"]]
            if not matched:
                continue
            route_topics.append(topic)
            target_specialists.append(specialist_name)
            route_reasons.append(f"{topic} 命中关键词：{'/'.join(matched[:3])}")

        if not target_specialists:
            route_topics = ["definition"]
            target_specialists = [SPECIALIST_DEFINITION]
            route_reasons = ["未命中明确主题，回退到定义/异常路由"]

        for topic in route_topics:
            topic_counter[topic] += 1
        for specialist_name in target_specialists:
            specialist_counter[specialist_name] += 1

        tasks.append(
            RouterTask(
                task_id=f"{chunk['chunk_id']}-router-task",
                chunk_id=chunk["chunk_id"],
                route_topics=_unique(route_topics),
                target_specialists=_unique(target_specialists),
                priority="high" if len(target_specialists) >= 2 else "normal",
                context_handles=_unique([chunk["chunk_id"], *chunk["reference_tokens"]]),
                rag_query_keys=_unique(
                    [*chunk["keyword_tags"], *chunk["reference_tokens"]]
                ),
                route_reasons=_unique(route_reasons),
            )
        )

    routing_summary = {
        "task_count": len(tasks),
        "topic_distribution": dict(topic_counter),
        "specialist_distribution": dict(specialist_counter),
    }
    return tasks, routing_summary


def _unique(items: list[str]) -> list[str]:
    """保持顺序去重。"""
    result: list[str] = []
    for item in items:
        value = str(item).strip()
        if value and value not in result:
            result.append(value)
    return result
