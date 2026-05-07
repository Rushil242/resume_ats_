"""
Lightweight ATS scorer — keyword extraction & match scoring.
No external model needed; works fully offline.

Inspired by:
- github.com/Saanvi26/ATS-Scorer
- github.com/miteshgupta07/ATS-Scoring-System
"""
import re
from collections import Counter
from typing import Tuple, List

STOP_WORDS = {
    "a","an","the","and","or","but","in","on","at","to","for",
    "of","with","as","by","from","is","are","was","were","be",
    "been","being","have","has","had","do","does","did","will",
    "would","could","should","may","might","shall","can","need",
    "we","our","your","their","this","that","these","those",
    "it","its","you","he","she","they","i","my","me","us",
    "not","no","nor","so","yet","both","either","neither",
    "than","then","when","where","which","who","whom","how","what"
}


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#\.]*", text)
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]


def _ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def score_resume(resume_text: str, jd_text: str) -> Tuple[float, List[str], List[str]]:
    """
    Returns:
        score (0–100 float),
        matched_keywords (list),
        missing_keywords (list)
    """
    jd_tokens = _tokenize(jd_text)
    resume_tokens = _tokenize(resume_text)

    # Unigrams + bigrams
    jd_terms = set(jd_tokens) | set(_ngrams(jd_tokens, 2))
    resume_terms = set(resume_tokens) | set(_ngrams(resume_tokens, 2))

    # Filter JD terms by frequency (keep only terms appearing 2+ times OR single mentions of bigrams)
    jd_freq = Counter(jd_tokens)
    important_jd = {
        t for t in jd_terms
        if (len(t.split()) == 1 and jd_freq[t] >= 2)
        or (len(t.split()) == 2)  # all bigrams are important
    }

    if not important_jd:
        important_jd = jd_terms  # fallback

    matched = important_jd & resume_terms
    missing = important_jd - resume_terms

    # Score = (matched / important) * 100, capped at 100
    score = round(min(len(matched) / max(len(important_jd), 1) * 100, 100), 1)

    # Sort for display
    matched_sorted = sorted(matched, key=lambda x: len(x.split()), reverse=True)[:30]
    missing_sorted = sorted(missing, key=lambda x: len(x.split()), reverse=True)[:30]

    return score, matched_sorted, missing_sorted
