import re


def split_content(content: str, target_size: int = 1400, overlap: int = 180) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", content).strip()
    if not normalized:
        return []
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= target_size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= target_size:
            prefix = current[-overlap:] if current else ""
            current = f"{prefix}\n\n{paragraph}".strip()
            continue
        start = 0
        while start < len(paragraph):
            piece = paragraph[start : start + target_size].strip()
            if piece:
                chunks.append(piece)
            start += max(1, target_size - overlap)
        current = ""
    if current:
        chunks.append(current)
    return chunks
