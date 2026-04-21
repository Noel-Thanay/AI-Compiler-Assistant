"""
Optimization Hints Engine — ported from _80 project.
Combines rule-based regex patterns with an ML classifier (Decision Tree / Random Forest)
trained on optimization_train.csv to detect performance anti-patterns in Mini-C code.
"""
import re
import os
import sys
import warnings
import numpy as np

warnings.filterwarnings("ignore")

# ── Rule-Based Patterns ──────────────────────────────────────────────────────
RULES = {
    "nested_loop":    (r"while\s*\([^)]+\)\s*\{[^}]*while", "high",
                       "Nested while-loops → O(n²). Consider refactoring."),
    "dead_code":      (r"return\s+\w+\s*;\s*\n\s*\w+\s*=", "medium",
                       "Code after return is unreachable. Remove it."),
    "magic_number":   (r"(?<!['\"\\w])[3-9]\\d{2,}\\b", "low",
                       "Replace magic number with a named constant."),
    "const_condition":(r"while\s*\(\s*(true|false)\s*\)", "medium",
                       "Constant condition in while — potential infinite loop."),
    "print_in_loop":  (r"while[^{]*\{[^}]*\bprint\s*\(", "medium",
                       "Avoid print() inside while-loop body (performance)."),
}


def rule_check(src: str):
    hints = []
    for name, (pat, sev, msg) in RULES.items():
        flags = re.MULTILINE if name == "dead_code" else 0
        for m in re.finditer(pat, src, flags):
            ln = src[: m.start()].count("\n") + 1
            code_line = src.splitlines()[ln - 1].strip()
            hints.append({
                "rule": name, "line": ln, "code": code_line,
                "severity": sev, "hint": msg, "src": "rule",
            })
    return hints


# ── ML Feature Extraction ────────────────────────────────────────────────────
def _feat(s: str):
    return [
        1 if re.search(r'\bwhile\b', s) else 0,
        1 if s.count("while") > 1 else 0,
        1 if re.search(r'while\s*\(\s*(true|false)\s*\)', s) else 0,
        1 if re.search(r'\bprint\s*\(', s) else 0,
        1 if re.search(r'(?<!\w)[3-9]\d{2,}\b', s) else 0,
        1 if re.search(r'\breturn\s+\w+\s*;', s) else 0,
        1 if re.search(r'\bwhile\b.*\bwhile\b', s, re.DOTALL) else 0,
        1 if re.search(r'\b(true|false)\b', s) else 0,
        1 if re.search(r'\bprint\s*\(\s*\)', s) else 0,
        min(len(s.strip()), 200),
    ]


# ── Model Loading / Training ─────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "..", "..", "data")
_CSV_PATH = os.path.join(_DATA_DIR, "optimization_train.csv")
_MODEL_PATH = os.path.join(_DATA_DIR, "optimization_model.pkl")

_MODEL = None
_LE = None


def _ensure_model():
    global _MODEL, _LE
    if _MODEL is not None:
        return

    import joblib

    # Try loading pre-trained model
    if os.path.exists(_MODEL_PATH):
        try:
            data = joblib.load(_MODEL_PATH)
            _MODEL, _LE = data["model"], data["le"]
            return
        except Exception:
            pass

    # Train from CSV if model file is missing or corrupt
    if not os.path.exists(_CSV_PATH):
        _MODEL = None
        return

    try:
        import pandas as pd
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
        from sklearn.metrics import accuracy_score
        from sklearn.preprocessing import LabelEncoder

        df = pd.read_csv(_CSV_PATH)
        le = LabelEncoder()
        y = le.fit_transform(df["label"])
        X = np.array([_feat(str(r)) for r in df["code"]])

        X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)
        X_train, X_val, y_train, y_val = train_test_split(X_tv, y_tv, test_size=0.176, random_state=42, stratify=y_tv)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        dt = DecisionTreeClassifier(class_weight="balanced", random_state=42)
        dt_params = {"max_depth": [2, 3, 4, 5, None], "min_samples_split": [2, 3], "criterion": ["gini", "entropy"]}
        dt_grid = GridSearchCV(dt, dt_params, cv=cv, scoring="accuracy", n_jobs=-1)
        dt_grid.fit(X_train, y_train)

        rf = RandomForestClassifier(class_weight="balanced", random_state=42)
        rf_params = {"n_estimators": [50, 100], "max_depth": [3, 5, None], "min_samples_split": [2, 3]}
        rf_grid = GridSearchCV(rf, rf_params, cv=cv, scoring="accuracy", n_jobs=-1)
        rf_grid.fit(X_train, y_train)

        dt_acc = accuracy_score(y_val, dt_grid.predict(X_val))
        rf_acc = accuracy_score(y_val, rf_grid.predict(X_val))
        best = dt_grid.best_estimator_ if dt_acc >= rf_acc else rf_grid.best_estimator_

        os.makedirs(_DATA_DIR, exist_ok=True)
        joblib.dump({"model": best, "le": le}, _MODEL_PATH)
        _MODEL, _LE = best, le
    except Exception as e:
        print(f"[OptimizationEngine] Training failed: {e}")
        _MODEL = None


# ── ML Check ─────────────────────────────────────────────────────────────────
_SAFE_PAT = re.compile(
    r'^\s*((int|float|bool|char|string|array)\s+\w+\s*;|\w+\s*=\s*[^;/\n]+;'
    r'|print\s*\([^)]+\)\s*;|return\s+\w+\s*;|\s*[\{\}]|\s*$|//.*)\s*$'
)


def ml_check(src: str):
    _ensure_model()
    if _MODEL is None:
        return []

    hints = []
    for i, line in enumerate(src.splitlines()):
        ln = i + 1
        if _SAFE_PAT.match(line):
            continue
        feat_arr = np.array(_feat(line)).reshape(1, -1)
        pred = _MODEL.predict(feat_arr)
        lbl = _LE.inverse_transform(pred)[0]
        if lbl != "none":
            sev = RULES[lbl][1] if lbl in RULES else "medium"
            msg = RULES[lbl][2] if lbl in RULES else f"ML detected: {lbl}"
            hints.append({"rule": lbl, "line": ln, "code": line.strip(), "severity": sev, "hint": msg, "src": "ml"})
    return hints


# ── Public API ────────────────────────────────────────────────────────────────
def get_optimization_hints(src: str):
    """Returns a deduplicated, severity-sorted list of optimization hints."""
    seen = set()
    out = []
    for h in rule_check(src) + ml_check(src):
        key = f"{h['line']}_{h['rule']}"
        if key not in seen:
            seen.add(key)
            out.append(h)
    sev_order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda x: sev_order.get(x["severity"], 3))
    return out
