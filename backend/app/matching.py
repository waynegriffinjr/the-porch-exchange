"""Keyword matching between needs and the skills neighbors offer."""

import re

STOPWORDS = frozenset(
    "a an and are as at be by can for from has have help i in is it me my need needs of on or our so "
    "some that the their this to up us we with you your want looking someone anyone able able".split()
)


def tokenize(text: str | None) -> set[str]:
    """Lowercase keywords from text, without stopwords, with trailing plurals/-ing/-ed trimmed."""
    words = set()
    for word in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if word in STOPWORDS or len(word) < 3:
            continue
        for suffix in ("ing", "ers", "er", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        words.add(word)
    return words


def score_match(need_title: str, need_description: str | None, skill_name: str, skill_description: str | None) -> int:
    """Score how well a skill fits a need; 0 means no overlap.

    Words shared with the skill name weigh double those shared only with its details.
    """
    need_words = tokenize(need_title) | tokenize(need_description)
    name_hits = need_words & tokenize(skill_name)
    detail_hits = (need_words & tokenize(skill_description)) - name_hits
    return 2 * len(name_hits) + len(detail_hits)
