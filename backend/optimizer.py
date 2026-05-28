"""
TokenForge optimization engine — the 5 distillation pillars condensed
into a single deterministic, regex-driven Python module.

Pillar 1: Sub-Byte Lexical Compression & Vocabulary Alignment
Pillar 2: Logit-Level Constrained Grammars / Boilerplate Stripping
Pillar 3: Non-Linear Compressed Struct Serialization
Pillar 4: Cross-Attention Semantic Cache Layer (cosine on hashed bag-of-words)
Pillar 5: Autonomous Multi-Tier Routing Network
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------------
# Token estimation (tiktoken-style heuristic: ~1 token / 4 chars or
# ~0.75 tokens / word — we use a hybrid).
# ------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    char_estimate = len(text) / 4.0
    word_estimate = max(1, len(text.split())) * 1.33
    return max(1, int(round((char_estimate + word_estimate) / 2)))


# ------------------------------------------------------------------
# Pillar 1: Lexical compression dictionary.
# Verbose phrases -> compact synonyms. Word boundaries enforced.
# ------------------------------------------------------------------
LEXICAL_MAP: Dict[str, str] = {
    # verbose phrases
    r"\bin order to\b": "to",
    r"\bdue to the fact that\b": "because",
    r"\bat this point in time\b": "now",
    r"\bin the event that\b": "if",
    r"\bin spite of the fact that\b": "although",
    r"\bwith regard to\b": "re",
    r"\bwith reference to\b": "re",
    r"\bin reference to\b": "re",
    r"\bas a matter of fact\b": "actually",
    r"\bin the near future\b": "soon",
    r"\bat the present time\b": "now",
    r"\bfor the purpose of\b": "for",
    r"\bin the process of\b": "while",
    r"\bon a regular basis\b": "regularly",
    r"\bprior to\b": "before",
    r"\bsubsequent to\b": "after",
    r"\bin addition to\b": "and",
    r"\ba large number of\b": "many",
    r"\ba majority of\b": "most",
    r"\ba small number of\b": "few",
    r"\bthe vast majority of\b": "most",
    r"\bas well as\b": "and",
    r"\bin terms of\b": "for",
    r"\bin order for\b": "for",
    r"\bso as to\b": "to",
    r"\bin the case of\b": "for",
    r"\bin connection with\b": "with",
    r"\bat the time of\b": "when",
    r"\bin the absence of\b": "without",
    r"\bwith the exception of\b": "except",
    r"\bnotwithstanding the fact that\b": "although",
    r"\bowing to the fact that\b": "because",
    r"\bgiven the fact that\b": "since",
    r"\bdespite the fact that\b": "although",
    # conversational filler
    r"\bplease note that\b": "note:",
    r"\bit should be noted that\b": "",
    r"\bit is important to note that\b": "note:",
    r"\bit is worth noting that\b": "",
    r"\bi would like to\b": "i'll",
    r"\bi would like you to\b": "",
    r"\bcould you please\b": "",
    r"\bwould you please\b": "",
    r"\bif you could\b": "",
    r"\bif possible\b": "",
    r"\bif you don't mind\b": "",
    r"\bthank you in advance\b": "",
    r"\bthanks in advance\b": "",
    r"\bappreciate it\b": "",
    r"\bfeel free to\b": "",
    # padding
    r"\bvery\s+(very\s+)+": "very ",
    r"\breally really\b": "really",
    r"\bquite\s+": "",
    r"\bsomewhat\s+": "",
    r"\brather\s+": "",
    r"\bbasically\b": "",
    r"\bessentially\b": "",
    r"\bactually\b": "",
    r"\bliterally\b": "",
    r"\bbasic\s+fundamental\b": "fundamental",
    # technical synonyms
    r"\bartificial intelligence\b": "AI",
    r"\bmachine learning\b": "ML",
    r"\blarge language model\b": "LLM",
    r"\bapplication programming interface\b": "API",
    r"\buser interface\b": "UI",
    r"\buser experience\b": "UX",
    r"\bsoftware as a service\b": "SaaS",
    r"\bdatabase\b": "DB",
    r"\binformation\b": "info",
    r"\bdocumentation\b": "docs",
    r"\bapplication\b": "app",
    r"\bperformance\b": "perf",
    r"\bconfiguration\b": "config",
    r"\bimplementation\b": "impl",
    r"\bdevelopment\b": "dev",
    r"\benvironment\b": "env",
    r"\brepository\b": "repo",
    r"\bdirectory\b": "dir",
    r"\bparameter\b": "param",
    r"\barguments\b": "args",
    r"\bvariables\b": "vars",
    r"\bfunctions\b": "fns",
    r"\boperation\b": "op",
    r"\bnumber\b": "num",
    r"\bmaximum\b": "max",
    r"\bminimum\b": "min",
    r"\baverage\b": "avg",
    r"\boptimization\b": "opt",
    r"\boptimize\b": "opt",
    r"\bconfiguration file\b": "config",
}

_LEXICAL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE), rep) for pat, rep in LEXICAL_MAP.items()
]


def pillar1_lexical_compress(text: str) -> str:
    """Replace verbose phrases with compact tokens."""
    out = text
    for pat, rep in _LEXICAL_PATTERNS:
        out = pat.sub(rep, out)
    # collapse multi-space
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n[ \t]+", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


# ------------------------------------------------------------------
# Pillar 2: Boilerplate / conversational wrapper stripping.
# Removes politeness padding, hedging, and "please respond with..." style
# preambles. Keeps actual instructions.
# ------------------------------------------------------------------
BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*(hello|hi|hey)[\s,!.]+", re.IGNORECASE),
    re.compile(r"\b(please|kindly)\s+", re.IGNORECASE),
    re.compile(r"\bthank(s| you)\b[.!]?", re.IGNORECASE),
    re.compile(r"\bi hope (this|you).{0,40}\b", re.IGNORECASE),
    re.compile(r"\bi'm (just |simply )?(trying to|wondering|hoping to)\b", re.IGNORECASE),
    re.compile(r"\bcan you (help me|please)?\b", re.IGNORECASE),
    re.compile(r"\bi was wondering if\b", re.IGNORECASE),
    re.compile(r"\bif it's not too much trouble\b", re.IGNORECASE),
    re.compile(r"\bjust wanted to (ask|know|see)\b", re.IGNORECASE),
    re.compile(r"\bas an? (ai|assistant|llm)\b.{0,60}[,.]", re.IGNORECASE),
    re.compile(r"\bi understand that\b", re.IGNORECASE),
    re.compile(r"\bsorry (to bother|for the trouble)\b", re.IGNORECASE),
]


def pillar2_strip_boilerplate(text: str) -> str:
    out = text
    for pat in BOILERPLATE_PATTERNS:
        out = pat.sub(" ", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    return out.strip()


# ------------------------------------------------------------------
# Pillar 3: Struct serialization — if input contains JSON/XML blocks,
# minify them.
# ------------------------------------------------------------------
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def pillar3_compress_structs(text: str) -> str:
    def minify_json(match: re.Match) -> str:
        raw = match.group(1)
        try:
            parsed = json.loads(raw)
            compact = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            return f"```json\n{compact}\n```"
        except Exception:
            return match.group(0)

    out = JSON_BLOCK_RE.sub(minify_json, text)
    # also try to detect a bare JSON object spanning entire string
    stripped = out.strip()
    if stripped and stripped[0] in "{[" and stripped[-1] in "}]":
        try:
            parsed = json.loads(stripped)
            return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            pass
    return out


# ------------------------------------------------------------------
# Pillar 4: Semantic cache. Lightweight embedding via hashed
# bag-of-words tf-idf-ish vector, cosine similarity.
# ------------------------------------------------------------------
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _embed(text: str, dim: int = 256) -> List[float]:
    vec = [0.0] * dim
    tokens = _WORD_RE.findall(text.lower())
    if not tokens:
        return vec
    counts = Counter(tokens)
    for tok, cnt in counts.items():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        idx = h % dim
        sign = 1.0 if (h >> 31) & 1 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(cnt))
    # l2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# ------------------------------------------------------------------
# Pillar 5: Multi-tier routing classification.
# ------------------------------------------------------------------
TIER1_REGEX_HINTS = [
    re.compile(r"^\s*(echo|reverse|uppercase|lowercase|trim|count\s+(words|chars))\b", re.IGNORECASE),
    re.compile(r"^\s*\d+[\s+\-*/]\d+\s*$"),
]
TIER2_HINTS = [
    re.compile(r"\b(extract|parse|classify|tag|label|categori[sz]e|summari[sz]e in \d+)\b", re.IGNORECASE),
    re.compile(r"\b(json|yaml|csv)\s+output\b", re.IGNORECASE),
]


def pillar5_route(text: str) -> str:
    """Return tier label: 'algorithmic', 'extractive', 'cognitive'."""
    if any(p.search(text) for p in TIER1_REGEX_HINTS):
        return "algorithmic"
    if any(p.search(text) for p in TIER2_HINTS):
        return "extractive"
    # default
    return "cognitive"


TIER_MODEL_HINT = {
    "algorithmic": "no-model (handled by deterministic pipeline)",
    "extractive": "gemini-3-flash-preview",
    "cognitive": "claude-sonnet-4-6",
}


# ------------------------------------------------------------------
# Public optimization API
# ------------------------------------------------------------------
@dataclass
class OptimizationResult:
    original_text: str
    optimized_text: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    percent_saved: float
    tier: str
    recommended_model: str
    pillars_applied: List[str] = field(default_factory=list)
    cache_hit: bool = False
    cache_similarity: float = 0.0


def optimize(text: str) -> OptimizationResult:
    original = text or ""
    original_tokens = estimate_tokens(original)
    pillars: List[str] = []

    step = original
    after1 = pillar1_lexical_compress(step)
    if after1 != step:
        pillars.append("lexical_compression")
        step = after1

    after2 = pillar2_strip_boilerplate(step)
    if after2 != step:
        pillars.append("boilerplate_strip")
        step = after2

    after3 = pillar3_compress_structs(step)
    if after3 != step:
        pillars.append("struct_serialization")
        step = after3

    tier = pillar5_route(step)
    pillars.append(f"routing:{tier}")

    optimized_tokens = estimate_tokens(step)
    saved = max(0, original_tokens - optimized_tokens)
    pct = (saved / original_tokens * 100.0) if original_tokens else 0.0

    return OptimizationResult(
        original_text=original,
        optimized_text=step,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        tokens_saved=saved,
        percent_saved=round(pct, 2),
        tier=tier,
        recommended_model=TIER_MODEL_HINT[tier],
        pillars_applied=pillars,
    )


def to_dict(r: OptimizationResult) -> dict:
    return asdict(r)
