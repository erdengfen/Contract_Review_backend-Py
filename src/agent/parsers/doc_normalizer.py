"""DOC 格式归一化执行入口。

本文件只负责把旧 DOC 文件转换为临时 DOCX，供解析层继续处理；不负责原始文件存储或入库。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class DocNormalizationError(RuntimeError):
    """DOC 归一化失败时使用的解析层异常。"""


def normalize_doc_to_docx(source_path: str, output_dir: str) -> Path:
    """使用本机 LibreOffice 将 DOC 转为 DOCX。"""

    source = Path(source_path).expanduser().resolve()
    target_dir = Path(output_dir).expanduser().resolve()
    _validate_doc_source(source)
    executable = _find_libreoffice_executable()
    target_dir.mkdir(parents=True, exist_ok=True)
    _run_libreoffice_convert(executable, source, target_dir)
    target_path = target_dir / f"{source.stem}.docx"
    if not target_path.exists():
        raise DocNormalizationError("docx_output_missing")
    return target_path


def _validate_doc_source(source: Path) -> None:
    """校验 DOC 源文件可被解析层读取。"""

    if not source.exists():
        raise DocNormalizationError("doc_source_missing")
    if source.suffix.lower() != ".doc":
        raise DocNormalizationError("doc_source_type_invalid")


def _find_libreoffice_executable() -> str:
    """查找可用的 LibreOffice 命令。"""

    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise DocNormalizationError("libreoffice_not_available")
    return executable


def _run_libreoffice_convert(executable: str, source: Path, target_dir: Path) -> None:
    """执行 DOC 到 DOCX 的转换命令。"""

    command = [
        executable,
        "--headless",
        "--convert-to",
        "docx",
        "--outdir",
        str(target_dir),
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        raise DocNormalizationError("libreoffice_convert_failed")


def _main_test_doc_normalizer() -> None:
    """执行 DOC 归一化入口的本文件自检。"""

    try:
        normalize_doc_to_docx("/tmp/missing.doc", "/tmp")
    except DocNormalizationError as error:
        assert str(error) == "doc_source_missing"
    else:
        raise AssertionError("缺失 DOC 文件必须报错")


if __name__ == "__main__":
    _main_test_doc_normalizer()
