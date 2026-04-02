"""
内部规则库入库服务。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.rag.clients.embedding_local import LocalEmbeddingClient
from app.rag.clients.qdrant_client import RagQdrantClient
from app.rag.config import RagConfig
from app.rag.ingest.chunkers import InternalRuleChunker, batched
from app.rag.schemas import InternalRuleRecord


class InternalRulesIngestService:
    """
    内部规则库入库服务。

    首版固定以 JSON / JSONL 作为输入格式，默认按自然段拆分后写入
    `internal_review_rules` collection。
    """

    def __init__(
        self,
        *,
        config: RagConfig,
        qdrant_client: Any | None = None,
        embedding_client: Any | None = None,
        chunker: InternalRuleChunker | None = None,
    ):
        self.config = config
        self.qdrant_client = qdrant_client or RagQdrantClient(config.qdrant)
        self.embedding_client = embedding_client or LocalEmbeddingClient(config.embedding)
        self.chunker = chunker or InternalRuleChunker()

    def load_records_from_file(self, file_path: str | Path) -> list[dict[str, Any]]:
        path = Path(file_path)
        if path.suffix.lower() == ".jsonl":
            return [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            raise ValueError("JSON 文件必须是列表结构。")
        raise ValueError("仅支持 JSON 或 JSONL 格式的内部规则数据文件。")

    def normalize_record(self, raw_record: dict[str, Any]) -> InternalRuleRecord:
        payload = dict(raw_record.get("payload", {}))
        known_keys = {
            "rule_id",
            "rule_type",
            "title",
            "content",
            "organization_scope",
            "contract_type_tags",
            "risk_tags",
            "priority",
            "enabled",
            "payload",
        }
        for key, value in raw_record.items():
            if key not in known_keys:
                payload[key] = value
        return InternalRuleRecord(
            rule_id=str(raw_record["rule_id"]),
            rule_type=raw_record["rule_type"],
            title=str(raw_record["title"]),
            content=str(raw_record["content"]),
            organization_scope=str(raw_record["organization_scope"]),
            contract_type_tags=list(raw_record.get("contract_type_tags", [])),
            risk_tags=list(raw_record.get("risk_tags", [])),
            priority=int(raw_record["priority"]),
            enabled=bool(raw_record["enabled"]),
            payload=payload,
        )

    def chunk_record(self, record: InternalRuleRecord) -> list[InternalRuleRecord]:
        chunks = self.chunker.split(record.content)
        if not chunks:
            return [record]

        normalized_chunks: list[InternalRuleRecord] = []
        for idx, chunk in enumerate(chunks, start=1):
            payload = {
                **record.payload,
                "parent_rule_id": record.rule_id,
                "chunk_index": idx,
            }
            normalized_chunks.append(
                InternalRuleRecord(
                    rule_id=f"{record.rule_id}#chunk-{idx}",
                    rule_type=record.rule_type,
                    title=record.title,
                    content=chunk,
                    organization_scope=record.organization_scope,
                    contract_type_tags=record.contract_type_tags,
                    risk_tags=record.risk_tags,
                    priority=record.priority,
                    enabled=record.enabled,
                    payload=payload,
                )
            )
        return normalized_chunks

    def build_payload(self, record: InternalRuleRecord) -> dict[str, Any]:
        return {
            "rule_id": record.rule_id,
            "rule_type": record.rule_type,
            "title": record.title,
            "content": record.content,
            "organization_scope": record.organization_scope,
            "contract_type_tags": record.contract_type_tags,
            "risk_tags": record.risk_tags,
            "priority": record.priority,
            "enabled": record.enabled,
            **record.payload,
        }

    def build_sparse_vector(self, text: str) -> tuple[list[int], list[float]]:
        token_counts: dict[int, float] = {}
        tokens = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+", text)
        for token in tokens:
            normalized = token.strip().lower()
            if not normalized:
                continue
            index = int(hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8], 16) % 50000
            token_counts[index] = token_counts.get(index, 0.0) + 1.0
        indices = sorted(token_counts.keys())
        values = [token_counts[index] for index in indices]
        return indices, values

    def build_point(self, record: InternalRuleRecord, dense_vector: list[float]):
        sparse_indices, sparse_values = self.build_sparse_vector(record.content)
        return self.qdrant_client.build_point(
            point_id=record.rule_id,
            dense_vector=dense_vector,
            payload=self.build_payload(record),
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
        )

    def ingest_records(self, raw_records: list[dict[str, Any]], batch_size: int = 16) -> dict[str, Any]:
        normalized_records: list[InternalRuleRecord] = []
        for raw_record in raw_records:
            normalized_records.extend(self.chunk_record(self.normalize_record(raw_record)))

        if not normalized_records:
            return {"input_count": 0, "chunk_count": 0, "upserted_points": 0}

        all_points = []
        for record_batch in batched(normalized_records, batch_size):
            dense_vectors = self.embedding_client.embed_documents(
                [record.content for record in record_batch]
            )
            for record, dense_vector in zip(record_batch, dense_vectors):
                all_points.append(self.build_point(record, dense_vector))

        self.qdrant_client.upsert(
            self.config.qdrant.internal_collection,
            all_points,
        )
        return {
            "input_count": len(raw_records),
            "chunk_count": len(normalized_records),
            "upserted_points": len(all_points),
        }

    def ingest_file(self, file_path: str | Path, batch_size: int = 16) -> dict[str, Any]:
        return self.ingest_records(self.load_records_from_file(file_path), batch_size=batch_size)


class _FakeEmbeddingClient:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(idx), float(idx + 1), float(idx + 2)] for idx, _ in enumerate(texts, start=1)]


class _FakeQdrantClient:
    def __init__(self):
        self.upsert_calls: list[dict[str, Any]] = []

    def build_point(self, **kwargs):
        return kwargs

    def upsert(self, collection_name: str, points: list[Any], **kwargs):
        self.upsert_calls.append({"collection_name": collection_name, "points": points})
        return {"status": "ok", "points_count": len(points)}


def _main_test_internal_rules_ingest():
    service = InternalRulesIngestService(
        config=RagConfig(),
        qdrant_client=_FakeQdrantClient(),
        embedding_client=_FakeEmbeddingClient(),
    )
    raw_records = [
        {
            "rule_id": "rule-payment-001",
            "rule_type": "review_rule",
            "title": "付款条款审阅规则",
            "content": "付款条款必须明确付款条件。\n\n付款期限必须明确。",
            "organization_scope": "global",
            "contract_type_tags": ["服务合同"],
            "risk_tags": ["付款条款"],
            "priority": 10,
            "enabled": True,
        }
    ]
    result = service.ingest_records(raw_records, batch_size=2)
    assert result["input_count"] == 1
    assert result["chunk_count"] == 2
    assert result["upserted_points"] == 2
    assert service.qdrant_client.upsert_calls[0]["collection_name"] == "internal_review_rules"
    print("InternalRulesIngestService self test passed")


if __name__ == "__main__":
    _main_test_internal_rules_ingest()
