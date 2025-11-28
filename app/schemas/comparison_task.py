"""
合同比对相关 Schema
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    file_id: int = Field(..., description="文件ID")
    title: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_path: str = Field(..., description="服务器存储路径")
    download_url: str = Field(..., description="下载接口")


class ComparisonDiffDetail(BaseModel):
    operation: str = Field(..., description="diff 操作类型")
    std_text: str = Field("", description="标准文档片段")
    cmp_text: str = Field("", description="比对文档片段")
    std_range: Optional[List[int]] = Field(
        default=None, description="标准文档内字符区间"
    )
    cmp_range: Optional[List[int]] = Field(
        default=None, description="比对文档内字符区间"
    )


class ComparisonParagraphDiff(BaseModel):
    operation: str = Field(..., description="段落级操作")
    std_index: Optional[int] = Field(default=None, description="标准文档段落索引")
    cmp_index: Optional[int] = Field(default=None, description="比对文档段落索引")
    standard_text: str = Field("", description="标准文档文本")
    comparison_text: str = Field("", description="比对文档文本")
    char_diff: Optional[List[ComparisonDiffDetail]] = Field(
        default=None, description="字符级差异"
    )


class ComparisonSummary(BaseModel):
    standard_paragraphs: int = Field(..., description="标准文档段落数")
    comparison_paragraphs: int = Field(..., description="比对文档段落数")
    difference_count: int = Field(..., description="差异段落总数")


class ComparisonTaskCreateRequest(BaseModel):
    standard_file_id: int = Field(..., description="标准文档ID")
    comparison_file_id: int = Field(..., description="比对文档ID")
    session_id: Optional[int] = Field(
        default=None, description="已有会话ID（可选）"
    )
    title: Optional[str] = Field(
        default=None, description="会话标题（仅新建时生效）"
    )


class ComparisonTaskResponse(BaseModel):
    task_id: int = Field(..., description="比对任务ID")
    session_id: int = Field(..., description="会话ID")
    diff_summary: ComparisonSummary = Field(..., description="差异摘要")
    diffs: List[ComparisonParagraphDiff] = Field(..., description="差异详情")
    standard_file: FileInfo = Field(..., description="标准文档信息")
    comparison_file: FileInfo = Field(..., description="比对文档信息")


class ComparisonHistoryResponse(BaseModel):
    task_id: int = Field(..., description="比对任务ID")
    session_id: int = Field(..., description="会话ID")
    diff_summary: ComparisonSummary = Field(..., description="差异摘要")
    diffs: List[ComparisonParagraphDiff] = Field(..., description="差异详情")
    standard_file: FileInfo = Field(..., description="标准文档信息")
    comparison_file: FileInfo = Field(..., description="比对文档信息")

