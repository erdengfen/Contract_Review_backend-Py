"""
外部法律知识库入库服务。
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
from app.rag.ingest.chunkers import LegalTextChunker, batched
from app.rag.schemas import ExternalLegalRecord


class ExternalLegalIngestService:
    """
    外部法律库入库服务。

    首版固定以 JSON / JSONL 作为输入格式，按条级结构切分后写入
    `external_legal_kb` collection。
    """

    def __init__(
        self,
        *,
        config: RagConfig,
        qdrant_client: Any | None = None,
        embedding_client: Any | None = None,
        chunker: LegalTextChunker | None = None,
    ):
        self.config = config
        self.qdrant_client = qdrant_client or RagQdrantClient(config.qdrant)
        self.embedding_client = embedding_client or LocalEmbeddingClient(config.embedding)
        self.chunker = chunker or LegalTextChunker()

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
        raise ValueError("仅支持 JSON 或 JSONL 格式的外部法律数据文件。")

    def normalize_record(self, raw_record: dict[str, Any]) -> ExternalLegalRecord:
        payload = dict(raw_record.get("payload", {}))
        known_keys = {
            "doc_id",
            "source_type",
            "source_level",
            "title",
            "article_no",
            "content",
            "region",
            "industry",
            "effective_status",
            "contract_type_tags",
            "risk_tags",
            "payload",
        }
        for key, value in raw_record.items():
            if key not in known_keys:
                payload[key] = value
        return ExternalLegalRecord(
            doc_id=str(raw_record["doc_id"]),
            source_type=raw_record["source_type"],
            source_level=raw_record["source_level"],
            title=str(raw_record["title"]),
            article_no=str(raw_record["article_no"]),
            content=str(raw_record["content"]),
            region=str(raw_record["region"]),
            industry=list(raw_record.get("industry", [])),
            effective_status=str(raw_record["effective_status"]),
            contract_type_tags=list(raw_record.get("contract_type_tags", [])),
            risk_tags=list(raw_record.get("risk_tags", [])),
            payload=payload,
        )

    def chunk_record(self, record: ExternalLegalRecord) -> list[ExternalLegalRecord]:
        chunks = self.chunker.split(record.content)
        if not chunks:
            return [record]

        normalized_chunks: list[ExternalLegalRecord] = []
        for idx, chunk in enumerate(chunks, start=1):
            chunk_article_no = chunk["article_no"] or record.article_no
            chunk_doc_id = f"{record.doc_id}#chunk-{idx}"
            payload = {
                **record.payload,
                "parent_doc_id": record.doc_id,
                "chunk_index": idx,
                "chunk_title": chunk["title"],
            }
            normalized_chunks.append(
                ExternalLegalRecord(
                    doc_id=chunk_doc_id,
                    source_type=record.source_type,
                    source_level=record.source_level,
                    title=record.title,
                    article_no=chunk_article_no,
                    content=chunk["content"],
                    region=record.region,
                    industry=record.industry,
                    effective_status=record.effective_status,
                    contract_type_tags=record.contract_type_tags,
                    risk_tags=record.risk_tags,
                    payload=payload,
                )
            )
        return normalized_chunks

    def build_payload(self, record: ExternalLegalRecord) -> dict[str, Any]:
        return {
            "doc_id": record.doc_id,
            "source_type": record.source_type,
            "source_level": record.source_level,
            "title": record.title,
            "article_no": record.article_no,
            "content": record.content,
            "region": record.region,
            "industry": record.industry,
            "effective_status": record.effective_status,
            "contract_type_tags": record.contract_type_tags,
            "risk_tags": record.risk_tags,
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

    def build_point(self, record: ExternalLegalRecord, dense_vector: list[float]):
        sparse_indices, sparse_values = self.build_sparse_vector(record.content)
        return self.qdrant_client.build_point(
            point_id=record.doc_id,
            dense_vector=dense_vector,
            payload=self.build_payload(record),
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
        )

    def ingest_records(self, raw_records: list[dict[str, Any]], batch_size: int = 16) -> dict[str, Any]:
        normalized_records: list[ExternalLegalRecord] = []
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
            self.config.qdrant.external_collection,
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


def _main_test_external_legal_ingest():
    service = ExternalLegalIngestService(
        config=RagConfig(),
        qdrant_client=_FakeQdrantClient(),
        embedding_client=_FakeEmbeddingClient(),
    )
    raw_records = [
        {
            "doc_id": "law-civil-code",
            "source_type": "law",
            "source_level": "national",
            "title": "中华人民共和国民法典",
            "article_no": "第五百零九条",
            "content": "第一条 合同应遵循平等原则。\n\n第二条 当事人应全面履行义务。",
            "region": "CN",
            "industry": ["general"],
            "effective_status": "effective",
            "contract_type_tags": ["通用合同"],
            "risk_tags": ["履约义务"],
        }
    ]
    result = service.ingest_records(raw_records, batch_size=2)
    assert result["input_count"] == 1
    assert result["chunk_count"] == 2
    assert result["upserted_points"] == 2
    assert service.qdrant_client.upsert_calls[0]["collection_name"] == "external_legal_kb"
    print("ExternalLegalIngestService self test passed")


if __name__ == "__main__":
    _main_test_external_legal_ingest()
