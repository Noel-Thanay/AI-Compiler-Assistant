import re
import os
import numpy as np
import warnings
import pandas as pd
import joblib
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

RULES = [
    ("S001", "division_by_zero", r"/\s*0\b", "CWE-369", "HIGH", "Division by zero — guard with: if(divisor != 0){ ... }"),
    ("S002", "null_dereference", r"\bnull\b[^;)]*[+\-\*\[\.=]|\bnull\s*\.\s*\w+", "CWE-476", "HIGH", "Null dereference — check: if(ptr != null){ ... } before use."),
    ("S003", "buffer_overflow", r"\b\w+\s*\[\s*([0-9]{3,}|-[0-9]+|\w+\s*[+\-]\s*[0-9]+)\s*\]", "CWE-119", "HIGH", "Buffer overflow risk — validate index bounds before array access."),
    ("S004", "infinite_loop", r"while\s*\(\s*(true|1)\s*\)\s*\{(?![^}]*break)", "CWE-835", "MEDIUM", "Infinite loop with no break — add exit condition."),
    ("S005", "uninitialized_null_use", r"\bprint\s*\(\s*null\s*\)", "CWE-457", "MEDIUM", "Printing null directly — may expose uninitialized memory."),
    ("S006", "hardcoded_magic_bound", r"\[\s*[5-9][0-9]{2,}\s*\]", "CWE-131", "MEDIUM", "Large hardcoded array bound — use a named constant."),
    ("S007", "missing_return_check", r"\bfunc\s+\w+\s*\([^)]*\)\s*\{(?![^}]*return)[^}]*\}", "CWE-252", "LOW", "Function has no return — unchecked return value risk."),
    ("S008", "command_injection", r"\b(system|exec|popen|fork)\s*\(", "CWE-78", "HIGH", "Command injection risk — use secure API instead of shell execution.")
]

def rule_check(src):
    findings = []
    lines = src.splitlines()
    for i in range(len(lines)):
        line = lines[i]
        ln = i + 1
        for rule in RULES:
            sid, name, pat, cwe, sev, msg = rule
            if re.search(pat, line):
                findings.append({"id": sid, "name": name, "line": ln, "code": line.strip(), "cwe": cwe, "severity": sev, "msg": msg, "src": "rule"})
    return findings

def _feat(s):
    f1 = 1 if bool(re.search(r'/\s*0\b', s)) else 0
    f2 = 1 if bool(re.search(r'\bnull\b', s)) else 0
    f3 = 1 if bool(re.search(r'\[\s*\d{3,}\s*\]', s)) else 0
    f4 = 1 if bool(re.search(r'while\s*\(\s*(true|1)\s*\)', s)) else 0
    f5 = 1 if bool(re.search(r'\bnull\b.*[+\-\*\[]', s)) else 0
    f6 = 1 if bool(re.search(r'if\s*\(.*!=\s*0.*\)', s)) else 0
    f7 = 1 if bool(re.search(r'if\s*\(.*!=\s*null.*\)', s)) else 0
    f8 = 1 if bool(re.search(r'if\s*\(.*<\s*\w+.*\)', s)) else 0
    f9 = 1 if bool(re.search(r'\bbreak\b', s)) else 0
    f10 = 1 if bool(re.search(r'\breturn\b', s)) else 0
    f11 = 1 if bool(re.search(r'\bfunc\b', s)) else 0
    f12 = 1 if bool(re.search(r'&&|\|\|', s)) else 0
    f13 = 1 if bool(re.search(r'-[0-9]', s)) else 0
    f14 = min(len(s.strip()), 200)
    return [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14]

def _load_and_train(csv_path, model_path):
    if os.path.exists(model_path):
        try:
            data = joblib.load(model_path)
            return data["model"], data["le"]
        except Exception:
            pass
            
    if not os.path.exists(csv_path):
        return None, None
        
    try:
        df = pd.read_csv(csv_path)
        le = LabelEncoder()
        y = le.fit_transform(df["label"])
        X = np.array([_feat(str(r)) for r in df["code"]])

        X_tv, X_te, y_tv, y_te = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)
        X_tr, X_v, y_tr, y_v = train_test_split(X_tv, y_tv, test_size=0.176, random_state=42, stratify=y_tv)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scaler = StandardScaler()
        svm = SVC(class_weight="balanced", random_state=42, probability=True)
        pipe = Pipeline([("scaler", scaler), ("svm", svm)])
        
        params = {
            "svm__C": [0.1, 1, 10, 100],
            "svm__kernel": ["rbf", "linear"],
            "svm__gamma": ["scale", "auto"]
        }
        
        grid = GridSearchCV(pipe, params, cv=cv, scoring="accuracy", n_jobs=-1, refit=True)
        grid.fit(X_tr, y_tr)
        best_model = grid.best_estimator_
        
        joblib.dump({"model": best_model, "le": le}, model_path)
        return best_model, le
    except Exception:
        return None, None

_HERE = os.path.dirname(os.path.abspath(__file__))
_CSV = os.path.join(_HERE, "..", "..", "data", "security_train.csv")
_MODEL_PATH = os.path.join(_HERE, "..", "..", "data", "security_model.pkl")

os.makedirs(os.path.join(_HERE, "..", "..", "data"), exist_ok=True)
_MODEL, _LE = _load_and_train(_CSV, _MODEL_PATH)

def ml_check(src):
    if _MODEL is None:
        return []
    findings = []
    lines = src.splitlines()
    for i in range(len(lines)):
        line = lines[i]
        ln = i + 1
        if line.strip() == "":
            continue
            
        feats = np.array(_feat(line)).reshape(1, -1)
        pred = _MODEL.predict(feats)
        lbl = _LE.inverse_transform(pred)[0]
        
        probs = _MODEL.predict_proba(feats)
        prob = probs.max()
        
        if lbl == "unsafe" and prob > 0.70:
            msg = f"ML (SVM) flagged as unsafe pattern (conf={int(prob * 100)}%)."
            findings.append({"id": "ML", "name": "ml_unsafe_pattern", "line": ln, "code": line.strip(), "cwe": "CWE-unknown", "severity": "MEDIUM", "msg": msg, "src": "ml"})
            
    return findings

def run_security_check(src):
    seen = set()
    out = []
    all_f = rule_check(src) + ml_check(src)
    
    for f in all_f:
        k = f"{f['line']}_{f['name']}"
        if k not in seen:
            seen.add(k)
            out.append(f)
            
    return out
