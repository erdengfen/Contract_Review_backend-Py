"""MinerU Agent 轻量解析客户端。

本文件封装免 Token 的 MinerU Agent 轻量解析调用；主解析流程默认不联网，只有显式传入客户端时才调用。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class MinerULightResult:
    """MinerU 轻量解析结果。"""

    state: str
    markdown: str | None = None
    result_url: str | None = None
    task_id: str | None = None
    warnings: list[str] = field(default_factory=list)


class MinerULightClient:
    """MinerU Agent 轻量解析 HTTP 客户端。"""

    def __init__(
        self,
        base_url: str = "https://mineru.net/api/v1/agent",
        timeout_seconds: int = 30,
        poll_interval_seconds: float = 1.5,
        max_poll_attempts: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_attempts = max_poll_attempts

    def parse_file(self, file_path: str, *, language: str = "ch") -> MinerULightResult:
        """提交本地文件到 MinerU 轻量解析，并返回 Markdown。"""

        path = Path(file_path).expanduser().resolve()
        submit_data = self._build_submit_data(path, language)
        response = requests.post(f"{self.base_url}/parse/file", json=submit_data, timeout=self.timeout_seconds)
        payload = response.json()
        direct = self._try_direct_result(payload)
        if direct:
            return direct
        task_id, file_url = self._extract_upload_task(payload)
        self._upload_file(file_url, path)
        return self._poll_result(task_id)

    def _build_submit_data(self, path: Path, language: str) -> dict[str, Any]:
        """构建 MinerU 轻量解析提交参数。"""

        return {
            "file_name": path.name,
            "language": language,
            "enable_table": True,
            "is_ocr": False,
            "enable_formula": True,
        }

    def _try_direct_result(self, payload: dict[str, Any]) -> MinerULightResult | None:
        """兼容直接返回 text/result 的轻量响应。"""

        text = payload.get("text")
        result_url = payload.get("result")
        if text:
            return MinerULightResult(state=payload.get("state", "done"), markdown=text, result_url=result_url)
        if result_url:
            return MinerULightResult(state=payload.get("state", "done"), markdown=self._download_markdown(result_url), result_url=result_url)
        return None

    def _extract_upload_task(self, payload: dict[str, Any]) -> tuple[str, str]:
        """从签名上传响应中提取任务 ID 和上传 URL。"""

        data = payload.get("data") or {}
        task_id = data.get("task_id")
        file_url = data.get("file_url")
        if not task_id or not file_url:
            raise RuntimeError("mineru_light_submit_failed")
        return task_id, file_url

    def _upload_file(self, file_url: str, path: Path) -> None:
        """使用签名 URL 上传 PDF 文件。"""

        with path.open("rb") as file_obj:
            response = requests.put(file_url, data=file_obj, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            raise RuntimeError("mineru_light_upload_failed")

    def _poll_result(self, task_id: str) -> MinerULightResult:
        """轮询 MinerU 轻量解析结果。"""

        for _ in range(self.max_poll_attempts):
            payload = self._get_task_payload(task_id)
            result = self._result_from_task_payload(task_id, payload)
            if result.state == "done" or result.state == "failed":
                return result
            time.sleep(self.poll_interval_seconds)
        return MinerULightResult(state="timeout", task_id=task_id, warnings=["mineru_light_timeout"])

    def _get_task_payload(self, task_id: str) -> dict[str, Any]:
        """查询 MinerU 任务状态。"""

        response = requests.get(f"{self.base_url}/parse/{task_id}", timeout=self.timeout_seconds)
        return response.json()

    def _result_from_task_payload(self, task_id: str, payload: dict[str, Any]) -> MinerULightResult:
        """把任务查询响应转换为统一结果。"""

        data = payload.get("data") or payload
        state = data.get("state", "unknown")
        result_url = _extract_result_url(data)
        if state == "done" and result_url:
            markdown = self._download_markdown(result_url)
            return MinerULightResult(state=state, markdown=markdown, result_url=result_url, task_id=task_id)
        return MinerULightResult(state=state, result_url=result_url, task_id=task_id)

    def _download_markdown(self, result_url: str) -> str:
        """下载 MinerU 返回的 Markdown 文本。"""

        response = requests.get(result_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text


def _extract_result_url(data: dict[str, Any]) -> str | None:
    """兼容不同字段名中的 Markdown 下载链接。"""

    for key in ("result", "md_url", "markdown_url", "download_url", "url"):
        value = data.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def _main_test_mineru_light_client() -> None:
    """执行 MinerU 客户端纯结构自检，不访问网络。"""

    client = MinerULightClient(base_url="https://example.invalid/api")
    payload = {"state": "done", "text": "# 标题"}
    result = client._try_direct_result(payload)
    assert result is not None
    assert result.markdown == "# 标题"


if __name__ == "__main__":
    _main_test_mineru_light_client()
