"""
RAG 配置模型。
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RagEmbeddingConfig(BaseModel):
    provider_mode: Literal["local", "remote"] = Field(
        "local",
        description="Embedding 提供方式。",
    )
    local_model_name: str = Field(
        "BAAI/bge-small-zh-v1.5",
        description="本地轻量 embedding 模型名称。",
    )
    local_device: str = Field(
        "cpu",
        description="本地 embedding 模型运行设备。",
    )
    local_batch_size: int = Field(
        32,
        description="本地 embedding 生成批大小。",
    )

    remote_provider: str = Field(
        "openai_compatible",
        description="远程 embedding provider 类型。",
    )
    remote_model: str = Field(
        "",
        description="远程 embedding 模型名称。",
    )
    remote_base_url: str = Field(
        "",
        description="远程 embedding 服务基地址。",
    )
    remote_api_key: str = Field(
        "",
        description="远程 embedding 服务 API Key。",
    )
    remote_timeout: int = Field(
        30,
        description="远程 embedding 请求超时时间（秒）。",
    )


class RagRerankConfig(BaseModel):
    enabled: bool = Field(
        True,
        description="是否启用 rerank。",
    )
    provider_mode: Literal["remote"] = Field(
        "remote",
        description="首版仅允许远程 rerank。",
    )
    remote_provider: str = Field(
        "siliconflow",
        description="远程 reranker provider 类型。",
    )
    remote_model: str = Field(
        "Qwen/Qwen3-Reranker-8B",
        description="远程 reranker 模型名称。",
    )
    remote_base_url: str = Field(
        "https://api.siliconflow.com/v1",
        description="远程 reranker 服务基地址。",
    )
    remote_path: str = Field(
        "/rerank",
        description="远程 reranker 接口路径。",
    )
    remote_api_key: str = Field(
        "",
        description="远程 reranker 服务 API Key。",
    )
    remote_timeout: int = Field(
        30,
        description="远程 reranker 请求超时时间（秒）。",
    )
    top_n: int = Field(
        8,
        description="rerank 后保留的结果数量。",
    )


class RagQdrantConfig(BaseModel):
    host: str = Field(
        "localhost",
        description="Qdrant 主机地址。",
    )
    port: int = Field(
        6333,
        description="Qdrant HTTP 端口。",
    )
    grpc_port: int = Field(
        6334,
        description="Qdrant gRPC 端口。",
    )
    api_key: Optional[str] = Field(
        None,
        description="可选的 Qdrant API Key。",
    )
    dense_vector_size: int = Field(
        512,
        description="Qdrant 中 dense 向量维度，创建 collection 时使用。",
    )
    external_collection: str = Field(
        "external_legal_kb",
        description="外部法律知识库 collection 名称。",
    )
    internal_collection: str = Field(
        "internal_review_rules",
        description="内部审阅规则库 collection 名称。",
    )
    prefer_grpc: bool = Field(
        False,
        description="是否优先使用 gRPC。",
    )
    timeout: int = Field(
        10,
        description="Qdrant 请求超时时间（秒）。",
    )


class RagStartupConfig(BaseModel):
    enabled: bool = Field(
        True,
        description="应用启动时是否执行 RAG 健康检查。",
    )
    ensure_qdrant_collections: bool = Field(
        True,
        description="启动时是否检查并补齐默认 Qdrant collections。",
    )
    fail_fast: bool = Field(
        False,
        description="启动检查失败时是否中断应用启动。",
    )


class RagRetrievalConfig(BaseModel):
    enabled: bool = Field(
        True,
        description="是否启用检索。",
    )
    enable_dense: bool = Field(
        True,
        description="是否启用 dense 检索。",
    )
    enable_sparse: bool = Field(
        True,
        description="是否启用 sparse 检索。",
    )
    enable_multi_query: bool = Field(
        True,
        description="是否启用多路 query 检索。",
    )
    per_route_top_k: int = Field(
        10,
        description="每路初召 top-k。",
    )
    fused_top_k: int = Field(
        20,
        description="融合后候选 top-k。",
    )
    final_external_top_k: int = Field(
        6,
        description="最终外部法律知识注入 top-k。",
    )
    final_internal_top_k: int = Field(
        4,
        description="最终内部规则注入 top-k。",
    )
    external_weight: float = Field(
        1.0,
        description="外部法律知识默认权重。",
    )
    internal_weight: float = Field(
        1.1,
        description="内部规则默认权重。",
    )
    route_raw_chunk_weight: float = Field(
        1.0,
        description="原始 chunk query 路由权重。",
    )
    route_legal_issue_weight: float = Field(
        1.1,
        description="法律问题 query 路由权重。",
    )
    route_risk_tag_weight: float = Field(
        1.0,
        description="风险标签 query 路由权重。",
    )
    score_threshold: Optional[float] = Field(
        None,
        description="可选分数阈值。",
    )
    max_context_chars: int = Field(
        5000,
        description="注入 prompt 的最大字符数。",
    )


class RagFilterConfig(BaseModel):
    default_region: Optional[str] = Field(
        None,
        description="默认地区过滤条件。",
    )
    default_industry: Optional[str] = Field(
        None,
        description="默认行业过滤条件。",
    )
    exclude_invalid_regulations: bool = Field(
        True,
        description="默认过滤失效或无效法规。",
    )
    internal_rules_enabled_only: bool = Field(
        True,
        description="默认仅检索启用中的内部规则。",
    )


class RagConfig(BaseModel):
    enabled: bool = Field(
        True,
        description="RAG 总开关。",
    )
    embedding: RagEmbeddingConfig = Field(
        default_factory=RagEmbeddingConfig,
        description="Embedding 提供方配置。",
    )
    rerank: RagRerankConfig = Field(
        default_factory=RagRerankConfig,
        description="Rerank 配置。",
    )
    qdrant: RagQdrantConfig = Field(
        default_factory=RagQdrantConfig,
        description="Qdrant 连接配置。",
    )
    startup: RagStartupConfig = Field(
        default_factory=RagStartupConfig,
        description="RAG 启动检查配置。",
    )
    retrieval: RagRetrievalConfig = Field(
        default_factory=RagRetrievalConfig,
        description="检索策略配置。",
    )
    filters: RagFilterConfig = Field(
        default_factory=RagFilterConfig,
        description="默认过滤配置。",
    )


DEFAULT_RAG_CONFIG = RagConfig()


def _main_test_config():
    config = RagConfig()
    assert config.enabled is True
    assert config.embedding.provider_mode in {"local", "remote"}
    assert config.qdrant.dense_vector_size > 0
    assert config.qdrant.external_collection == "external_legal_kb"
    assert config.qdrant.internal_collection == "internal_review_rules"
    print("RagConfig self test passed")


if __name__ == "__main__":
    _main_test_config()
