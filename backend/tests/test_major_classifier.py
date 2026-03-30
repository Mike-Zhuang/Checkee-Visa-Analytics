from __future__ import annotations

from app.services import major_classifier


def test_abbreviation_rules_match_expected_categories() -> None:
    rows = [
        {"major": "EE"},
        {"major": "ECE"},
        {"major": "DS"},
    ]

    major_classifier.apply_major_classification(
        rows,
        overrides={},
        rules=major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES,
    )

    ee = rows[0]
    ece = rows[1]
    ds = rows[2]

    assert ee["major_category_l1"] == "STEM"
    assert ee["major_category_l2"] == "Engineering"
    assert ee["major_classification_source"] == major_classifier.MAJOR_SOURCE_AUTO

    assert ece["major_category_l1"] == "STEM"
    assert ece["major_category_l2"] == "Engineering"
    assert ece["major_classification_source"] == major_classifier.MAJOR_SOURCE_AUTO

    assert ds["major_category_l1"] == "STEM"
    assert ds["major_category_l2"] == "AI & Data"
    assert ds["major_classification_source"] == major_classifier.MAJOR_SOURCE_AUTO


def test_na_values_are_not_applicable_and_ignore_manual_override() -> None:
    rows = [
        {"major": "N/A"},
        {"major": "NA"},
        {"major": "Not Applicable"},
    ]

    # Even if historical override exists, N/A-like placeholders should stay read-only.
    overrides = {
        "n a": {
            "category_l1": "Business",
            "category_l2": "Finance & Accounting",
        }
    }

    metrics = major_classifier.apply_major_classification(
        rows,
        overrides=overrides,
        rules=major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES,
    )

    for row in rows:
        assert row["major_category_l1"] == major_classifier.MAJOR_NOT_APPLICABLE_L1
        assert row["major_category_l2"] == major_classifier.MAJOR_NOT_APPLICABLE_L2
        assert row["major_classification_source"] == major_classifier.MAJOR_SOURCE_NOT_APPLICABLE

    assert metrics["major_classification_manual_count"] == 0
    assert metrics["major_classification_not_applicable_count"] == 3


def test_not_applicable_items_exposed_as_read_only_group() -> None:
    rows = [{"major": "N/A"}, {"major": "CS"}]
    items = major_classifier.major_classification_items(
        rows,
        overrides={},
        rules=major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES,
    )

    by_major = {item["major_normalized"]: item for item in items}
    na_item = by_major["n a"]

    assert na_item["source"] == major_classifier.MAJOR_SOURCE_NOT_APPLICABLE
    assert na_item["has_manual_override"] is False
    assert na_item["effective_category_l2"] == major_classifier.MAJOR_NOT_APPLICABLE_L2


def test_single_level_major_maps_to_unspecified_l2() -> None:
    rows = [{"major": "STEM"}]

    major_classifier.apply_major_classification(
        rows,
        overrides={},
        rules=major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES,
    )

    row = rows[0]
    assert row["major_category_l1"] == "STEM"
    assert row["major_category_l2"] == major_classifier.MAJOR_UNSPECIFIED_L2
    assert row["major_classification_source"] == major_classifier.MAJOR_SOURCE_AUTO


def test_common_disciplines_have_auto_classification() -> None:
    rows = [
        {"major": "Architecture"},
        {"major": "Biotech"},
        {"major": "Biochem"},
        {"major": "Astronomy"},
    ]

    major_classifier.apply_major_classification(
        rows,
        overrides={},
        rules=major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES,
    )

    expected = {
        "Architecture": ("Arts&Humanities", "Arts & Design"),
        "Biotech": ("STEM", "Natural Science"),
        "Biochem": ("STEM", "Natural Science"),
        "Astronomy": ("STEM", "Natural Science"),
    }
    for row in rows:
        major = row["major"]
        assert row["major_category_l1"] == expected[major][0]
        assert row["major_category_l2"] == expected[major][1]
        assert row["major_classification_source"] == major_classifier.MAJOR_SOURCE_AUTO
