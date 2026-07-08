"""
Neuro-Symbolic Analyzer — True fusion of symbolic AST analysis + LLM neural reasoning.

Pipeline:
  SymbolicKnowledgeExtractor  →  extracts typed, severity-weighted facts from diagnostics
  NeuralReasoner              →  queries Llama 3 (Ollama) over those structured facts
  NeuroSymbolicFuser          →  combines scores: 60% symbolic + 40% neural

The Fuser produces a single fused confidence score and verdict with full provenance
from both the symbolic (deterministic) and neural (probabilistic) sources.
"""

import re
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


# ── Symbolic Layer ─────────────────────────────────────────────────────────────

class SymbolicKnowledgeExtractor:
    """
    Converts compiler diagnostics (from DiagnosticsEngine) into a typed,
    severity-weighted JSON-serializable symbolic fact-sheet.

    The symbolic_score (0.0–1.0) measures how severe the overall issue set is,
    weighted by diagnostic type (syntax errors weigh more than hints).
    """

    # How much each diagnostic type contributes to the symbolic severity score
    SEVERITY_WEIGHTS = {
        "SyntaxError":      1.00,
        "InternalError":    0.95,
        "SemanticError":    0.90,
        "Security":         0.85,
        "OptimizationHint": 0.30,
    }

    def extract(self, diagnostics: list, security_warnings: list) -> dict:
        errors        = [d for d in diagnostics if "Error" in d.get("type", "")]
        security      = [d for d in diagnostics if d.get("type") == "Security"]
        optimizations = [d for d in diagnostics if d.get("type") == "OptimizationHint"]

        # Severity-weighted score — higher means more/worse issues
        total_weight = sum(
            self.SEVERITY_WEIGHTS.get(d.get("type", ""), 0.5)
            for d in diagnostics
        )
        max_possible  = len(diagnostics) * 1.0 if diagnostics else 1.0
        symbolic_score = min(total_weight / max_possible, 1.0) if diagnostics else 0.0

        return {
            "error_count":        len(errors),
            "security_count":     len(security),
            "optimization_count": len(optimizations),
            "errors": [
                {
                    "type": d["type"],
                    "code": d.get("code", "?"),
                    "line": d.get("line", "?"),
                    "msg":  d["message"],
                }
                for d in errors
            ],
            "security_issues": [
                {
                    "code": d.get("code", "?"),
                    "line": d.get("line", "?"),
                    "msg":  d["message"],
                }
                for d in security
            ],
            "optimization_hints": [
                {
                    "code": d.get("code", "?"),
                    "line": d.get("line", "?"),
                    "msg":  d["message"],
                }
                for d in optimizations
            ],
            "symbolic_score":  round(symbolic_score, 3),
            "severity_label":  self._label(symbolic_score),
        }

    @staticmethod
    def _label(score: float) -> str:
        if score >= 0.80: return "CRITICAL"
        if score >= 0.60: return "HIGH"
        if score >= 0.40: return "MEDIUM"
        return "LOW"


# ── Neural Layer ───────────────────────────────────────────────────────────────

class NeuralReasoner:
    """
    Queries Llama 3 (via Ollama) with the symbolic fact-sheet embedded in the
    prompt as structured JSON — the LLM reasons *over* the symbolic facts, not
    just raw source code.  Parses a CONFIDENCE score from the response.
    """

    def __init__(self):
        self.ollama_url    = "http://localhost:11434/api/generate"
        self.default_model = "llama3"

    def reason(
        self,
        source_code:   str,
        symbolic_facts: dict,
        iteration:     int = 1,
        prior_plan:    str | None = None,
    ) -> tuple:
        """
        Returns (response_text: str, neural_confidence: float ∈ [0, 1]).
        On Ollama failure, returns an error string with confidence 0.0.
        """
        prompt = self._build_prompt(source_code, symbolic_facts, iteration, prior_plan)
        try:
            payload = {
                "model":  self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx":     2048,
                    "num_predict": 600,
                    "temperature": 0.1,
                },
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=180)
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                conf = self._parse_confidence(text)
                return text, conf
            return f"### ⚠️ LLM HTTP Error {resp.status_code}", 0.0
        except Exception as e:
            return f"### ❌ LLM Unavailable\n\nOllama error: {e}", 0.0

    def _build_prompt(
        self,
        source_code:   str,
        facts:         dict,
        iteration:     int,
        prior_plan:    str | None,
    ) -> str:
        facts_json    = json.dumps(facts, indent=2)
        prior_section = (
            f"\n\nPRIOR FIX ATTEMPT (Iteration {iteration - 1}):\n{prior_plan}"
            if prior_plan else ""
        )

        return (
            f"You are a Mini-C compiler expert AI. This is fix iteration {iteration}.\n\n"
            "SYMBOLIC ANALYSIS FACTS (extracted from AST + static analysis — treat as ground truth):\n"
            f"```json\n{facts_json}\n```\n\n"
            f"SOURCE CODE:\n```c\n{source_code.strip()}\n```"
            f"{prior_section}\n\n"
            "Your response must contain exactly these sections:\n"
            "1. ROOT CAUSE: Explain what causes each issue listed in the symbolic facts.\n"
            "2. FIX PLAN: Numbered concrete steps to resolve every listed issue.\n"
            "3. FIXED CODE: Complete corrected Mini-C source in a ```c code block.\n"
            "4. The final line must be: CONFIDENCE: X% "
            "(your confidence 0-100% that the fix resolves all listed issues)\n\n"
            "Rules: Output only valid Mini-C. Keep all correct logic unchanged. "
            "Do not wrap in Python/Java. Do not add imports."
        )

    @staticmethod
    def _parse_confidence(response_text: str) -> float:
        m = re.search(r"CONFIDENCE:\s*(\d+)\s*%", response_text, re.IGNORECASE)
        if m:
            return min(int(m.group(1)) / 100.0, 1.0)
        return 0.5  # conservative default when LLM omits the confidence line


# ── Fusion Layer ───────────────────────────────────────────────────────────────

class NeuroSymbolicFuser:
    """
    Combines the symbolic layer score (0.6 weight — deterministic, authoritative)
    with the neural layer confidence (0.4 weight — probabilistic) into a single
    fused score and verdict.

    Formula:
        symbolic_quality  = 1 - symbolic_score   (inverted: 1.0 = no issues)
        fused_score       = 0.6 × symbolic_quality + 0.4 × neural_confidence

    Symbolic dominates because AST analysis is exact; neural adds reasoning depth.
    """

    SYMBOLIC_WEIGHT = 0.6
    NEURAL_WEIGHT   = 0.4

    def fuse(
        self,
        symbolic_facts:    dict,
        neural_response:   str,
        neural_confidence: float,
    ) -> dict:
        symbolic_score   = symbolic_facts.get("symbolic_score", 0.0)
        symbolic_quality = round(1.0 - symbolic_score, 3)   # higher = fewer issues

        fused_score = round(
            self.SYMBOLIC_WEIGHT * symbolic_quality +
            self.NEURAL_WEIGHT   * neural_confidence,
            3,
        )

        return {
            "symbolic_score":    symbolic_score,
            "symbolic_quality":  symbolic_quality,
            "neural_confidence": round(neural_confidence, 3),
            "fused_score":       fused_score,
            "verdict":           self._verdict(fused_score, symbolic_facts),
            "neural_response":   neural_response,
            "symbolic_facts":    symbolic_facts,
        }

    @staticmethod
    def _verdict(score: float, facts: dict) -> str:
        if facts["error_count"] > 0:
            return "🔴 UNSAFE — Compilation errors must be fixed first."
        if facts["security_count"] > 0:
            return "🟠 RISKY — Security vulnerabilities detected."
        if score >= 0.80:
            return "🟢 SAFE — Code passes neuro-symbolic analysis."
        if score >= 0.55:
            return "🟡 CAUTION — Minor optimisation issues remain."
        return "🔴 UNSAFE — Significant issues detected."


# ── Public API ─────────────────────────────────────────────────────────────────

class NeuroSymbolicAnalyzer:
    """
    Top-level orchestrator for the full neuro-symbolic pipeline:

        SymbolicKnowledgeExtractor → NeuralReasoner → NeuroSymbolicFuser

    Two public methods:
      analyze()          — full pipeline, returns formatted markdown (used by UI NS panel)
      analyze_for_agent()— returns raw LLM text only (used by AgenticDebugger for code extraction)
      get_structured()   — returns raw fused dict (used by UI for metrics / confidence bars)
    """

    def __init__(self):
        self.extractor = SymbolicKnowledgeExtractor()
        self.reasoner  = NeuralReasoner()
        self.fuser     = NeuroSymbolicFuser()

    # ── Full analysis (UI Neuro-Symbolic panel) ────────────────────────────────

    def analyze(
        self,
        source_code:       str,
        diagnostics:       list,
        security_warnings: list,
        model_name:        str = None,
    ) -> str:
        """Returns formatted markdown string for Streamlit display."""
        result = self._pipeline(source_code, diagnostics, security_warnings)
        return self._format(result)

    def get_structured(
        self,
        source_code:       str,
        diagnostics:       list,
        security_warnings: list,
    ) -> dict:
        """Returns the raw fused dict — for UI confidence bars / programmatic use."""
        return self._pipeline(source_code, diagnostics, security_warnings)

    # ── Agent-facing (used by AgenticDebugger) ─────────────────────────────────

    def analyze_for_agent(
        self,
        source_code:       str,
        diagnostics:       list,
        security_warnings: list,
        iteration:         int = 1,
        prior_plan:        str | None = None,
    ) -> str:
        """
        Returns the raw LLM response text so AgenticDebugger can extract
        the fixed code block from it.
        """
        facts = self.extractor.extract(diagnostics, security_warnings)
        neural_response, _ = self.reasoner.reason(
            source_code, facts,
            iteration=iteration,
            prior_plan=prior_plan,
        )
        return neural_response

    # ── Internal ───────────────────────────────────────────────────────────────

    def _pipeline(self, source_code, diagnostics, security_warnings) -> dict:
        facts                    = self.extractor.extract(diagnostics, security_warnings)
        neural_response, conf    = self.reasoner.reason(source_code, facts)
        return self.fuser.fuse(facts, neural_response, conf)

    def _format(self, result: dict) -> str:
        facts = result["symbolic_facts"]

        lines = [
            "## 🔬 Neuro-Symbolic Analysis Report",
            "",
            "### 📐 Symbolic Layer  *(AST + Static Analysis — deterministic)*",
            f"- **Errors:** `{facts['error_count']}`  ·  "
            f"**Security:** `{facts['security_count']}`  ·  "
            f"**Optimizations:** `{facts['optimization_count']}`",
            f"- **Symbolic Severity Score:** `{facts['symbolic_score']}` → **{facts['severity_label']}**",
        ]

        if facts["errors"]:
            lines += ["", "**Compiler Errors:**"]
            for e in facts["errors"]:
                lines.append(f"  - Line `{e['line']}` `[{e['code']}]`: {e['msg']}")

        if facts["security_issues"]:
            lines += ["", "**Security Issues:**"]
            for s in facts["security_issues"]:
                lines.append(f"  - Line `{s['line']}`: {s['msg']}")

        if facts["optimization_hints"]:
            lines += ["", "**Optimization Hints:**"]
            for o in facts["optimization_hints"]:
                lines.append(f"  - Line `{o['line']}` `[{o['code']}]`: {o['msg']}")

        lines += [
            "",
            "---",
            "### 🤖 Neural Layer  *(Llama 3 — reasoning over symbolic facts)*",
            "",
            result["neural_response"],
            "",
            "---",
            "### ⚖️ Neuro-Symbolic Fusion  *(60% Symbolic + 40% Neural)*",
            "",
            "| Component | Score | Weight |",
            "|-----------|-------|--------|",
            f"| Symbolic Quality (1 − severity) | `{result['symbolic_quality']}` | 60% |",
            f"| Neural Confidence (parsed from LLM) | `{result['neural_confidence']}` | 40% |",
            f"| **Fused Score** | **`{result['fused_score']}`** | — |",
            "",
            f"**Verdict:** {result['verdict']}",
        ]

        return "\n".join(lines)
