"""
Agentic Debugger — Real ReAct-style Plan → Act → Observe → Re-Fix loop.

Each iteration:
  1. PLAN    — LLM receives structured symbolic facts (JSON) + source code
  2. ACT     — LLM produces a fix plan + corrected Mini-C code block
  3. OBSERVE — Corrected code is fed through the real compiler pipeline
  4. RE-FIX  — Loop continues if errors remain (up to max_iter times)

Convergence:  error count reaches 0, OR stops decreasing (stale).
Result:       structured dict with per-iteration log, fixed code, and summary.
"""

import re

from src.agent.neuro_symbolic_analyzer import NeuroSymbolicAnalyzer


class AgenticDebugger:
    """
    ReAct-style agentic loop that iteratively fixes Mini-C source code by
    compiling, observing errors, and re-planning with LLM assistance.
    """

    def __init__(self, max_iter: int = 3):
        self.max_iter = max_iter
        self._nsa = NeuroSymbolicAnalyzer()

    # ── Internal Compiler Pipeline ────────────────────────────────────────────

    def _run_pipeline(self, source: str):
        """
        Run the full compiler + analysis pipeline on *source*.
        Returns (ast_or_None, diagnostics_list).
        This mirrors exactly what app_streamlit does on "Run & Analyze".
        """
        from src.compiler.parser import parse as compiler_parse
        from src.compiler.semantic_analyzer import SemanticAnalyzer
        from src.compiler.diagnostics_engine import DiagnosticsEngine
        from src.agent.security_analyzer import SecurityAnalyzer
        from src.agent.ast_optimization_analyzer import ASTOptimizationAnalyzer
        from src.agent.ml_security_checker import run_security_check

        diag = DiagnosticsEngine()

        try:
            ast = compiler_parse(source, diag=diag)
        except Exception as e:
            diag.report("InternalError", "E000", str(e))
            ast = None

        if ast:
            try:
                SemanticAnalyzer(diag).visit(ast)
            except Exception as e:
                diag.report("SemanticError", "S000", str(e))

            try:
                SecurityAnalyzer(diag).visit(ast)
            except Exception:
                pass

            try:
                for f in run_security_check(source):
                    diag.report(
                        "Security", f["id"],
                        f"[{f['severity']}] {f['msg']} (CWE: {f['cwe']})",
                        line=f["line"],
                    )
            except Exception:
                pass

            try:
                ASTOptimizationAnalyzer(diag).analyze(ast)
            except Exception:
                pass

        return ast, diag.get_all()

    # ── Code Extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_code(llm_response: str):
        """
        Pull Mini-C source from an LLM response.
        Tries fenced code blocks first, then any block that looks like Mini-C.
        Returns the extracted string, or None if nothing found.
        """
        patterns = [
            r"```(?:c|cpp|c_cpp|mini[-_]?c)?\s*\n(.*?)```",
            r"```\s*\n(.*?)```",
            r"```(.*?)```",
        ]
        for pat in patterns:
            m = re.search(pat, llm_response, re.DOTALL)
            if m:
                candidate = m.group(1).strip()
                # Sanity-check: must look like Mini-C code
                if "{" in candidate or ";" in candidate:
                    return candidate
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def debug_and_fix(
        self,
        source_code: str,
        diagnostics: list,
        model_name: str = None,
    ) -> dict:
        """
        Run the agentic Plan→Act→Observe→Re-Fix loop.

        Returns a dict:
          converged          bool   — True if all errors were eliminated
          iterations         int    — number of loop iterations run
          log                list   — per-iteration detail dicts
          fixed_code         str    — best corrected source found
          final_diagnostics  list   — diagnostics after final iteration
          summary            str    — human-readable markdown summary
        """
        if not diagnostics:
            return {
                "converged": True,
                "iterations": 0,
                "log": [],
                "fixed_code": source_code,
                "final_diagnostics": [],
                "summary": "✅ Code looks clean — no issues to fix.",
            }

        current_code = source_code
        current_diag = diagnostics
        log: list = []
        converged = False
        prior_plan: str | None = None

        for iteration in range(1, self.max_iter + 1):

            step = {
                "iteration":         iteration,
                "input_error_count": len(current_diag),
                "llm_response":      None,
                "extracted_code":    None,
                "output_error_count": None,
                "new_diagnostics":   [],
                "status":            "running",
                "error":             None,
            }

            # ── PHASE 1 & 2 : PLAN + ACT ─────────────────────────────────────
            try:
                llm_response = self._nsa.analyze_for_agent(
                    current_code,
                    current_diag,
                    [],
                    iteration=iteration,
                    prior_plan=prior_plan,
                )
                step["llm_response"] = llm_response
            except Exception as e:
                step["status"] = "llm_error"
                step["error"] = str(e)
                log.append(step)
                break

            # ── PHASE 3 : EXTRACT FIXED CODE ─────────────────────────────────
            extracted = self._extract_code(llm_response)
            step["extracted_code"] = extracted

            if not extracted:
                step["status"] = "no_code_extracted"
                log.append(step)
                break

            # ── PHASE 3 : OBSERVE — re-compile ───────────────────────────────
            try:
                _, new_diag = self._run_pipeline(extracted)
                step["new_diagnostics"]   = new_diag
                step["output_error_count"] = len(new_diag)
            except Exception as e:
                step["status"] = "compile_error"
                step["error"] = str(e)
                log.append(step)
                break

            # ── PHASE 4 : RE-PLAN / CONVERGE ─────────────────────────────────
            if len(new_diag) == 0:
                # All errors resolved — done
                step["status"] = "converged"
                current_code = extracted
                current_diag = new_diag
                log.append(step)
                converged = True
                break

            elif len(new_diag) >= len(current_diag):
                # Fix made things worse or equal — stop (stale)
                step["status"] = "stale"
                log.append(step)
                break

            else:
                # Improved but not done — keep looping
                step["status"] = "improved"
                current_code = extracted
                current_diag = new_diag
                prior_plan = llm_response
                log.append(step)

        return {
            "converged":         converged,
            "iterations":        len(log),
            "log":               log,
            "fixed_code":        current_code,
            "final_diagnostics": current_diag,
            "summary":           self._build_summary(log, converged),
        }

    # ── Summary Builder ───────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(log: list, converged: bool) -> str:
        if not log:
            return "⚠️ Agent could not start — LLM may be unavailable."

        STATUS_ICONS = {
            "converged":         "✅",
            "improved":          "🔄",
            "stale":             "⚠️",
            "no_code_extracted": "❌",
            "llm_error":         "❌",
            "compile_error":     "❌",
        }

        lines = ["### 🤖 Agentic Loop Summary\n"]
        for step in log:
            icon  = STATUS_ICONS.get(step["status"], "⚪")
            in_c  = step["input_error_count"]
            out_c = step.get("output_error_count", "N/A")
            lines.append(
                f"{icon} **Iteration {step['iteration']}**: "
                f"{in_c} errors → {out_c} errors `[{step['status']}]`"
            )

        lines.append("")
        if converged:
            lines.append("✅ **Converged** — all compiler issues resolved!")
        else:
            lines.append("⚠️ **Max iterations reached** — best partial fix applied.")

        return "\n".join(lines)
