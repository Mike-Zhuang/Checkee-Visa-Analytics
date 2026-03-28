from __future__ import annotations

import re
from collections import Counter
from typing import Any

MAJOR_CATEGORY_L1_OPTIONS = [
    "STEM",
    "Business",
    "Health",
    "Arts&Humanities",
    "Law&Policy",
    "Social Science",
    "Education",
    "Other",
]

MAJOR_NOT_APPLICABLE_L1 = "Other"
MAJOR_NOT_APPLICABLE_L2 = "Not Applicable"

MAJOR_SOURCE_MANUAL = "manual"
MAJOR_SOURCE_AUTO = "auto"
MAJOR_SOURCE_UNKNOWN = "unknown"
MAJOR_SOURCE_NOT_APPLICABLE = "not_applicable"

NOT_APPLICABLE_MAJOR_TOKENS = {
    "n a",
    "na",
    "none",
    "null",
    "nil",
    "not applicable",
    "not available",
}

DEFAULT_MAJOR_TAXONOMY_RULES: list[dict[str, Any]] = [
    {"l1": "STEM", "l2": "AI & Data", "keywords": ["artificial intelligence", "machine learning", "deep learning", "data science", "data analytics", "computer science", "ai", "ml", "ds", "nlp", "algorithm", "statistics", "statistical", "stats"]},
    {"l1": "STEM", "l2": "Software & Systems", "keywords": ["software", "computer engineering", "information technology", "information systems", "cyber", "network", "cloud", "cse", "cs"]},
    {"l1": "STEM", "l2": "Engineering", "keywords": ["engineering", "electrical", "electronics", "electrical engineering", "electronics engineering", "mechanical", "civil", "industrial", "materials", "robotics", "aerospace", "biomedical engineering", "ece", "ee"]},
    {"l1": "STEM", "l2": "Natural Science", "keywords": ["physics", "chemistry", "biology", "biotechnology", "mathematics", "math", "applied math", "geology", "environmental science"]},
    {"l1": "Business", "l2": "Management & Operations", "keywords": ["business", "management", "mba", "operations", "supply chain", "entrepreneurship", "project management"]},
    {"l1": "Business", "l2": "Finance & Accounting", "keywords": ["finance", "financial", "accounting", "tax", "audit", "banking", "investment", "econometrics"]},
    {"l1": "Business", "l2": "Marketing & Commerce", "keywords": ["marketing", "market", "commerce", "e-commerce", "advertising", "brand", "retail"]},
    {"l1": "Health", "l2": "Clinical & Medicine", "keywords": ["medicine", "medical", "pharmacy", "nursing", "clinical", "dentistry", "public health", "epidemiology"]},
    {"l1": "Health", "l2": "Life & Nutrition", "keywords": ["nutrition", "food science", "kinesiology", "rehabilitation", "healthcare", "health science"]},
    {"l1": "Arts&Humanities", "l2": "Language & Literature", "keywords": ["literature", "linguistics", "language", "translation", "writing", "journalism"]},
    {"l1": "Arts&Humanities", "l2": "Arts & Design", "keywords": ["design", "art", "music", "film", "drama", "theatre", "animation", "media arts"]},
    {"l1": "Arts&Humanities", "l2": "History & Philosophy", "keywords": ["history", "philosophy", "religion", "classics", "humanities"]},
    {"l1": "Law&Policy", "l2": "Law", "keywords": ["law", "legal", "jurisprudence", "llm", "jd", "paralegal"]},
    {"l1": "Law&Policy", "l2": "Public Policy & International Affairs", "keywords": ["public policy", "policy", "international affairs", "governance", "public administration", "diplomacy"]},
    {"l1": "Social Science", "l2": "Economics", "keywords": ["economics", "economy", "macro", "micro"]},
    {"l1": "Social Science", "l2": "Psychology & Behavior", "keywords": ["psychology", "behavior", "behavioral", "cognitive science"]},
    {"l1": "Social Science", "l2": "Society & Communication", "keywords": ["sociology", "anthropology", "communication", "media studies", "political science", "geography"]},
    {"l1": "Education", "l2": "Teaching & Curriculum", "keywords": ["education", "teaching", "curriculum", "instruction", "pedagogy", "tesol", "educational"]},
]


def normalize_major(raw_major: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", raw_major.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def is_not_applicable_major(major_norm: str) -> bool:
    if not major_norm:
        return False

    compact = major_norm.replace(" ", "")
    if major_norm in NOT_APPLICABLE_MAJOR_TOKENS:
        return True
    if compact in {"na", "notapplicable", "notavailable", "none", "null", "nil"}:
        return True
    return False


def taxonomy_l2_options(rules: list[dict[str, Any]]) -> list[str]:
    values = sorted({str(rule.get("l2") or "").strip() for rule in rules if str(rule.get("l2") or "").strip()})
    if "Unspecified" not in values:
        values.append("Unspecified")
    if MAJOR_NOT_APPLICABLE_L2 not in values:
        values.append(MAJOR_NOT_APPLICABLE_L2)
    return values


def taxonomy_l1_options(rules: list[dict[str, Any]]) -> list[str]:
    dynamic = [str(rule.get("l1") or "").strip() for rule in rules if str(rule.get("l1") or "").strip()]
    merged = list(dict.fromkeys([*MAJOR_CATEGORY_L1_OPTIONS, *dynamic]))
    return merged


def _auto_classify_major(major_norm: str, rules: list[dict[str, Any]]) -> tuple[str, str, str]:
    if not major_norm:
        return "Other", "Unspecified", MAJOR_SOURCE_UNKNOWN

    if is_not_applicable_major(major_norm):
        return MAJOR_NOT_APPLICABLE_L1, MAJOR_NOT_APPLICABLE_L2, MAJOR_SOURCE_NOT_APPLICABLE

    best_rule: dict[str, Any] | None = None
    best_score = -1

    for rule in rules:
        keywords = [str(item).strip().lower() for item in (rule.get("keywords") or []) if str(item).strip()]
        if not keywords:
            continue

        score = 0
        for keyword in keywords:
            if keyword in major_norm:
                score += len(keyword)

        if score > best_score:
            best_score = score
            best_rule = rule

    if best_rule is None or best_score <= 0:
        return "Other", "Unspecified", MAJOR_SOURCE_UNKNOWN

    l1 = str(best_rule.get("l1") or "Other").strip() or "Other"
    l2 = str(best_rule.get("l2") or "Unspecified").strip() or "Unspecified"
    return l1, l2, MAJOR_SOURCE_AUTO


def apply_major_classification(
    rows: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
    rules: list[dict[str, Any]],
) -> dict[str, int]:
    manual_count = 0
    auto_count = 0
    unknown_count = 0
    not_applicable_count = 0

    for row in rows:
        major = str(row.get("major") or "").strip()
        major_norm = normalize_major(major)

        auto_l1, auto_l2, auto_source = _auto_classify_major(major_norm, rules)

        if auto_source == MAJOR_SOURCE_NOT_APPLICABLE:
            row["major_category_l1"] = auto_l1
            row["major_category_l2"] = auto_l2
            row["major_classification_source"] = MAJOR_SOURCE_NOT_APPLICABLE
            not_applicable_count += 1
            continue

        if major_norm and major_norm in overrides:
            override = overrides[major_norm]
            row["major_category_l1"] = str(override.get("category_l1") or "Other")
            row["major_category_l2"] = str(override.get("category_l2") or "Unspecified")
            row["major_classification_source"] = MAJOR_SOURCE_MANUAL
            manual_count += 1
            continue

        row["major_category_l1"] = auto_l1
        row["major_category_l2"] = auto_l2
        row["major_classification_source"] = auto_source

        if auto_source == MAJOR_SOURCE_AUTO:
            auto_count += 1
        else:
            unknown_count += 1

    return {
        "major_classification_manual_count": manual_count,
        "major_classification_auto_count": auto_count,
        "major_classification_unknown_count": unknown_count,
        "major_classification_not_applicable_count": not_applicable_count,
    }


def major_classification_items(
    rows: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        major = str(row.get("major") or "").strip()
        major_norm = normalize_major(major)
        if not major_norm:
            continue
        grouped.setdefault(major_norm, []).append(row)

    items: list[dict[str, Any]] = []
    for major_norm, bucket in grouped.items():
        raw_counter = Counter(str(item.get("major") or "").strip() for item in bucket)
        major_display = raw_counter.most_common(1)[0][0] if raw_counter else major_norm

        auto_l1, auto_l2, auto_source = _auto_classify_major(major_norm, rules)
        override = None if auto_source == MAJOR_SOURCE_NOT_APPLICABLE else overrides.get(major_norm)
        has_manual = override is not None

        effective_l1 = str(override.get("category_l1") if override else auto_l1)
        effective_l2 = str(override.get("category_l2") if override else auto_l2)
        source = MAJOR_SOURCE_MANUAL if has_manual else auto_source

        items.append(
            {
                "major": major_display,
                "major_normalized": major_norm,
                "count": len(bucket),
                "auto_category_l1": auto_l1,
                "auto_category_l2": auto_l2,
                "effective_category_l1": effective_l1,
                "effective_category_l2": effective_l2,
                "source": source,
                "has_manual_override": has_manual,
                "override_updated_at": str(override.get("updated_at") or "") if override else None,
            }
        )

    items.sort(key=lambda item: (-int(item["count"]), str(item["major"])))
    return items
