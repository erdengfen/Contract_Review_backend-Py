


def split_text_by_length(text: str, max_length: int = 4000) -> list[str]:
    """将文本按指定字符数分割为多段"""
    chunks = []
    current_pos = 0
    total_length = len(text)

    while current_pos < total_length:
        end_pos = current_pos + max_length

        # 尝试在句号、分号、换行处断开（尽量不截断句子）
        if end_pos < total_length:
            next_break = max(
                text.rfind("。", current_pos, end_pos),
                text.rfind("；", current_pos, end_pos),
                text.rfind("\n", current_pos, end_pos),
            )
            if next_break == -1 or next_break <= current_pos + 100:  # 防止太短
                next_break = end_pos
            else:
                next_break += 1  # 包含标点
        else:
            next_break = total_length

        chunks.append(text[current_pos:next_break].strip())
        current_pos = next_break

    return chunks
