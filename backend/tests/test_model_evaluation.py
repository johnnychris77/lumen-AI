"""Model evaluation framework metrics."""
from app.analytics.model_evaluation import (
    confusion_matrix,
    binary_metrics,
    per_class_report,
    reviewer_agreement,
)


def test_confusion_matrix():
    y_true = [True, True, False, False]
    y_pred = [True, False, True, False]
    cm = confusion_matrix(y_true, y_pred)
    assert cm == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}


def test_binary_metrics():
    # 2 TP, 1 FN, 1 FP, 1 TN
    y_true = [True, True, True, False, False]
    y_pred = [True, True, False, True, False]
    m = binary_metrics(y_true, y_pred)
    assert m["precision"] == round(2 / 3, 4)
    assert m["recall"] == round(2 / 3, 4)
    assert m["false_positive_rate"] == round(1 / 2, 4)
    assert m["false_negative_rate"] == round(1 / 3, 4)
    assert m["support"] == 5


def test_perfect_prediction():
    y = [True, False, True, False]
    m = binary_metrics(y, y)
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["false_negative_rate"] == 0.0
    assert m["f1"] == 1.0


def test_per_class_report():
    rep = per_class_report(
        {"blood": [True, False], "rust": [False, True]},
        {"blood": [True, False], "rust": [True, True]},
    )
    assert rep["blood"]["recall"] == 1.0
    assert rep["rust"]["false_positive_rate"] == 1.0  # 1 FP, 0 TN


def test_reviewer_agreement():
    model = [True, True, False, False]
    reviewer = [True, False, False, False]
    a = reviewer_agreement(model, reviewer)
    assert a["percent_agreement"] == 0.75
    assert a["n"] == 4
    assert -1.0 <= a["cohen_kappa"] <= 1.0


def test_reviewer_full_agreement_kappa():
    labels = [True, False, True, True, False]
    a = reviewer_agreement(labels, labels)
    assert a["percent_agreement"] == 1.0
    assert a["cohen_kappa"] == 1.0
