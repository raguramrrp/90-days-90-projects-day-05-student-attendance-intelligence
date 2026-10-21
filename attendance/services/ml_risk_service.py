"""
Optional Machine Learning Risk Prediction Service.
Implements a Decision Tree Classifier as an evaluable extension alongside the rule-based baseline.
Includes documented synthetic feature engineering, train/test evaluation, confusion matrix calculation,
and safe fallback to the deterministic rule engine.
"""

import os
import joblib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / 'ml_models'
MODEL_PATH = MODEL_DIR / 'attendance_decision_tree.joblib'
METRICS_PATH = MODEL_DIR / 'evaluation_metrics.json'

FEATURE_NAMES = [
    'attendance_percentage',
    'consecutive_absences',
    'absence_velocity_14d',
    'past_leave_count',
    'past_correction_count',
    'period_of_day_mode',  # 1 (morning) to 8 (evening)
]


def is_ml_model_available() -> bool:
    """Checks whether the trained Decision Tree artifact exists on disk."""
    return MODEL_PATH.exists()


def extract_student_features(student, percentage: float = None, trend: dict = None) -> np.ndarray:
    """
    Extracts numerical feature vector for inference from a student profile.
    """
    if percentage is None:
        percentage = student.cached_attendance_percentage

    if trend is None:
        from .risk_engine import analyze_recent_absence_trend
        trend = analyze_recent_absence_trend(student, limit=10)

    consecutive = trend.get('consecutive_absences', 0)
    velocity_14d = trend.get('recent_14_days_absence_rate', 0.0)

    # Historical engagement indicators
    past_leaves = getattr(student, 'leave_requests', None)
    leave_count = past_leaves.count() if past_leaves else 0

    past_corrections = getattr(student, 'correction_requests', None)
    correction_count = past_corrections.count() if past_corrections else 0

    # Default period of day mode
    period_mode = 2.0

    features = np.array([
        percentage,
        consecutive,
        velocity_14d,
        leave_count,
        correction_count,
        period_mode
    ]).reshape(1, -1)

    return features


def predict_attendance_risk_ml(student, percentage: float = None) -> Dict[str, Any]:
    """
    Performs inference with the Decision Tree Classifier if available,
    otherwise falls back to rule-based classification.
    """
    if not is_ml_model_available():
        from .risk_engine import classify_risk_level
        pct = percentage if percentage is not None else student.cached_attendance_percentage
        rule_risk = classify_risk_level(pct)
        return {
            'predicted_risk': rule_risk,
            'confidence': 1.0,
            'source': 'RULE_ENGINE_FALLBACK',
            'model_available': False,
            'explanation': 'Inference handled via primary deterministic rule engine (ML model artifact not loaded).'
        }

    try:
        model_data = joblib.load(MODEL_PATH)
        clf = model_data['classifier']
        class_names = model_data.get('class_names', ['CRITICAL', 'SAFE', 'WARNING'])

        X = extract_student_features(student, percentage=percentage)
        pred_idx = clf.predict(X)[0]
        probabilities = clf.predict_proba(X)[0]

        pred_label = class_names[pred_idx] if isinstance(pred_idx, (int, np.integer)) else str(pred_idx)
        confidence = float(np.max(probabilities))

        return {
            'predicted_risk': pred_label,
            'confidence': round(confidence * 100, 1),
            'probabilities': {class_names[i]: round(float(probabilities[i]) * 100, 1) for i in range(len(class_names))},
            'source': 'DECISION_TREE_ML',
            'model_available': True,
            'features_used': dict(zip(FEATURE_NAMES, X[0].tolist())),
            'explanation': f"Decision Tree predicted '{pred_label}' with {round(confidence * 100, 1)}% leaf probability."
        }
    except Exception as exc:
        from .risk_engine import classify_risk_level
        pct = percentage if percentage is not None else student.cached_attendance_percentage
        return {
            'predicted_risk': classify_risk_level(pct),
            'confidence': 1.0,
            'source': 'RULE_ENGINE_FALLBACK_ON_ERROR',
            'model_available': False,
            'error': str(exc)
        }


def generate_synthetic_dataset_and_train(n_samples: int = 600, random_state: int = 42) -> Dict[str, Any]:
    """
    Generates synthetic academic attendance feature data for demonstration/training,
    fits a DecisionTreeClassifier, evaluates precision/recall/F1/confusion matrix,
    and saves the model.
    """
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    import json

    np.random.seed(random_state)

    # 1. Feature Generation with realistic domain distribution
    # Class 0: CRITICAL (low attendance, high consecutive absences, high velocity)
    # Class 1: WARNING (marginal attendance 74-82%, moderate absences)
    # Class 2: SAFE (high attendance 82-100%, low consecutive absences)

    n_crit = int(n_samples * 0.25)
    n_warn = int(n_samples * 0.35)
    n_safe = n_samples - n_crit - n_warn

    # Critical samples
    crit_pct = np.random.uniform(40.0, 74.0, n_crit)
    crit_consec = np.random.randint(2, 7, n_crit)
    crit_vel = np.random.uniform(30.0, 90.0, n_crit)
    crit_leaves = np.random.poisson(1.5, n_crit)
    crit_corrections = np.random.poisson(1.0, n_crit)
    crit_period = np.random.randint(1, 8, n_crit)
    crit_labels = np.array(['CRITICAL'] * n_crit)

    # Warning samples
    warn_pct = np.random.uniform(74.0, 81.5, n_warn)
    warn_consec = np.random.randint(1, 4, n_warn)
    warn_vel = np.random.uniform(15.0, 45.0, n_warn)
    warn_leaves = np.random.poisson(1.2, n_warn)
    warn_corrections = np.random.poisson(0.8, n_warn)
    warn_period = np.random.randint(1, 8, n_warn)
    warn_labels = np.array(['WARNING'] * n_warn)

    # Safe samples
    safe_pct = np.random.uniform(81.5, 99.0, n_safe)
    safe_consec = np.random.randint(0, 2, n_safe)
    safe_vel = np.random.uniform(0.0, 18.0, n_safe)
    safe_leaves = np.random.poisson(0.5, n_safe)
    safe_corrections = np.random.poisson(0.3, n_safe)
    safe_period = np.random.randint(1, 8, n_safe)
    safe_labels = np.array(['SAFE'] * n_safe)

    # Combine
    X = np.column_stack([
        np.concatenate([crit_pct, warn_pct, safe_pct]),
        np.concatenate([crit_consec, warn_consec, safe_consec]),
        np.concatenate([crit_vel, warn_vel, safe_vel]),
        np.concatenate([crit_leaves, warn_leaves, safe_leaves]),
        np.concatenate([crit_corrections, warn_corrections, safe_corrections]),
        np.concatenate([crit_period, warn_period, safe_period]),
    ])
    y = np.concatenate([crit_labels, warn_labels, safe_labels])

    class_names = ['CRITICAL', 'SAFE', 'WARNING']

    # Train / Test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=random_state, stratify=y
    )

    clf = DecisionTreeClassifier(
        max_depth=4,
        min_samples_split=8,
        min_samples_leaf=4,
        random_state=random_state
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=class_names)

    # Save artifact
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        'classifier': clf,
        'feature_names': FEATURE_NAMES,
        'class_names': class_names,
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'trained_at': str(np.datetime64('now')),
    }, MODEL_PATH)

    metrics = {
        'accuracy': round(float(acc) * 100, 2),
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'class_labels': class_names,
        'feature_importances': dict(zip(FEATURE_NAMES, [round(float(fi), 4) for fi in clf.feature_importances_])),
        'note': 'Model trained on controlled synthetic dataset for demonstration purposes.'
    }

    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)

    return metrics
