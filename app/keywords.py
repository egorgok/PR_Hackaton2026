import math
import re

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9-]{1,}")
STOP_WORDS = {
    "это", "как", "что", "для", "при", "или", "его", "ее", "их", "они", "она",
    "оно", "был", "была", "были", "будет", "быть", "также", "после", "перед",
    "между", "через", "около", "который", "которая", "которые", "этот", "эта",
    "эти", "тот", "та", "там", "здесь", "всего", "более", "менее", "может",
    "могут", "сообщает", "сообщили", "рассказал", "рассказали", "край", "края",
    "красноярский", "красноярского",
}
RU_ENDINGS = (
    "иями", "ями", "ами", "ого", "ему", "ыми", "ими", "его", "ому", "ее",
    "ие", "ые", "ое", "ей", "ий", "ый", "ой", "ем", "им", "ым", "ом",
    "ах", "ях", "ия", "ья", "ию", "ью", "ая", "яя", "ую", "юю", "ам",
    "ям", "ов", "ев", "а", "я", "ы", "и", "е", "о", "у", "ю", "ь",
)


def _normalize_token(token: str) -> str:
    token = token.casefold().replace("ё", "е").strip("-")
    if len(token) < 5:
        return token
    for ending in RU_ENDINGS:
        if token.endswith(ending) and len(token) - len(ending) >= 4:
            return token[: -len(ending)]
    return token


def extract_keywords(text: str, limit: int = 20) -> list[str]:
    tokens = [_normalize_token(token) for token in TOKEN_RE.findall(text)]
    tokens = [token for token in tokens if token not in STOP_WORDS and not token.isdigit()]
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts, key=lambda token: (-counts[token], -len(token), token))
    return ranked[:limit]


def lexical_match(text: str, keywords: list[str]) -> bool:
    text_tokens = {_normalize_token(token) for token in TOKEN_RE.findall(text)}
    query_tokens = {_normalize_token(token) for token in keywords}
    query_tokens.discard("")
    if not query_tokens:
        return False
    matched_count = len(query_tokens & text_tokens)
    required_count = (
        1
        if len(query_tokens) == 1
        else max(2, math.ceil(len(query_tokens) * 0.3))
    )
    return matched_count >= required_count
