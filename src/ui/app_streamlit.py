import streamlit as st
import sys
import os

# ── Path setup ──────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streamlit_ace import st_ace
from src.compiler.parser import parse as compiler_parse
from src.compiler.semantic_analyzer import SemanticAnalyzer
from src.compiler.diagnostics_engine import DiagnosticsEngine
from src.runtime.interpreter import Interpreter
from src.agent.agentic_debugger import AgenticDebugger
from src.agent.autocomplete import AutoCompleteEngine, suggest_snippet
from src.agent.security_analyzer import SecurityAnalyzer
from src.agent.optimization_hints import get_optimization_hints
from src.agent.ast_optimization_analyzer import ASTOptimizationAnalyzer
from src.ui.ast_visualizer import visualize_ast

st.set_page_config(page_title="AI Compiler Assistant", layout="wide", page_icon="🤖")

# ── Persistent State ─────────────────────────────────────────────────────────
DEFAULT_CODE = """\
void main() {
    // 1. AST OPTIMIZATION HINTS
    int unused_var = 100;           // O001: Declared but never used
    int a = 5;
    int b = a * 1;                  // O003: Redundant multiplication by 1
    int d = a + 0;                  // O003: Redundant addition
    
    if (1) {                        // O002: Redundant branch condition
        int redundant = 1;
    }
    
    if (a == a) {                   // O002: Redundant condition (always true)
        int logic = 1;
    }

   
    // 2. ML OPTIMIZATION HINTS (Random Forest)
    while (a < 10) {
        while (b < 10) {            // Nested while-loops -> ML flags as O(n^2)
            b = b + 1;
            print(b);               // ML Warning: Avoid print inside loop body
        }
        a = a + 1;
    }

   
    // 3. AST & ML SECURITY AUDIT WARNINGS
    int password = 12345;           // Hardcoded sensitive variable name
    string secret = "admin_key";    // Hardcoded sensitive string content
    int c = a / 0;                  // Division by zero detected
    
    // Dangerous Identifiers (Buffer Overflow / Command Injection Risks)
    int gets = 10;                  // Dangerous identifier 'gets'
    int system = 99;                // Dangerous identifier 'system'
    
    while (1) {                     // Infinite loop detected (while true)
        int loop = 1;
    }

    // 4. AGENTIC AI DEBUGGER DEMO (Self-Healing)
    
    // undefined_variable = 999;
}
"""

if 'code' not in st.session_state:
    st.session_state.code = DEFAULT_CODE
if 'run_result' not in st.session_state:
    st.session_state.run_result = None
if 'agent_fix' not in st.session_state:
    st.session_state.agent_fix = None
if 'ac_engine' not in st.session_state:
    with st.spinner("Initialising autocomplete engine..."):
        engine = AutoCompleteEngine()
        engine.train()
        st.session_state.ac_engine = engine

# ── Page Header ──────────────────────────────────────────────────────────────
st.markdown("## 🤖 Agentic AI Compiler Assistant")
st.caption("Mini-C Compiler  ·  AST Visualiser  ·  Neuro-Symbolic AI Debugger")
st.divider()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    ai_model = st.selectbox("AI Brain", ["llama3"], index=0)
    st.caption("Select the AI engine for Agentic Self-Healing.")
    agentic_on = st.toggle("Agentic Self-Healing", value=True)
    security_on = st.toggle("Security Audit", value=True)
    st.divider()
    if st.button("🗑️ Reset Editor", use_container_width=True):
        st.session_state.code = DEFAULT_CODE
        st.session_state.run_result = None
        st.session_state.agent_fix = None
        st.rerun()
    st.divider()
    st.markdown("**📋 Capabilities**")
    st.markdown("-  Mini-C Lexer & Parser\n-  Semantic Analysis\n-  AST Generation\n-  Code Execution\n-  Security Audit\n-  AI Autocomplete\n-  Agentic Debugger")

# ── Main 2-Column Layout ─────────────────────────────────────────────────────
col_editor, col_assist = st.columns([3, 1])

with col_editor:
    st.subheader("💻 Source Code Editor")
    new_code = st_ace(
        value=st.session_state.code,
        language="c_cpp",
        theme="monokai",
        key="ace_editor",
        auto_update=True,
        min_lines=22,
        font_size=14,
    )
    # Immediately sync + rerun so autocomplete sees the latest code
    if new_code != st.session_state.code:
        st.session_state.code = new_code
        st.session_state.agent_fix = None
        st.rerun()

    run_clicked = st.button("▶️ Run & Analyze", type="primary", use_container_width=True, key="run_btn")

with col_assist:
    st.subheader("💡 Suggestions")
    # Track cursor by finding where the text changed
    old_code = st.session_state.get('last_code', '')
    live_code = st.session_state.code
    
    # Find the index of the first difference
    cursor_pos = len(live_code)
    for i in range(min(len(old_code), len(live_code))):
        if old_code[i] != live_code[i]:
            # The cursor is right after the newly inserted character
            cursor_pos = i + (len(live_code) - len(old_code))
            break

    st.session_state.last_code = live_code
    
    try:
        suggestions, _, prefix = st.session_state.ac_engine.complete_from_source(
            live_code, cursor_pos, top_k=10
        )
    except Exception:
        suggestions, prefix = [], ""

    with st.container(height=320):
        if suggestions:
            # Create two columns to fit 10 items nicely
            col1, col2 = st.columns(2)
            for i, (tok, score) in enumerate(suggestions):
                snip = suggest_snippet(tok)
                help_text = snip if snip else f"Insert '{tok}'"
                
                # Alternate between columns
                target_col = col1 if i % 2 == 0 else col2
                
                with target_col:
                    if st.button(f" {tok}", key=f"ac_{i}", use_container_width=True, help=help_text):
                        base = live_code
                        insert = base[:-len(prefix)] + tok if prefix else base + tok
                        st.session_state.code = insert
                        st.rerun()
        else:
            st.info("Type code to see suggestions")

# ── Compilation & Analysis ────────────────────────────────────────────────────
if run_clicked:
    diag = DiagnosticsEngine()
    source = st.session_state.code

    with st.spinner("Compiling..."):
        try:
            ast = compiler_parse(source, diag=diag)
        except Exception as e:
            diag.report("InternalError", "E000", str(e))
            ast = None

    if ast:
        # Semantic Analysis
        try:
            sem = SemanticAnalyzer(diag)
            sem.visit(ast)
        except Exception as e:
            diag.report("SemanticError", "S000", f"Semantic analysis crashed: {e}")

        # Security Audit
        sec_warnings = []
        if security_on:
            # 1. AST-based Security Checks (from _20)
            try:
                sec = SecurityAnalyzer(diag)
                sec.visit(ast)
                if sec.has_warnings:
                    sec_warnings.append("AST Security Violation")
            except Exception:
                pass
                
            # 2. ML/Regex Security Checks (from _80)
            try:
                from src.agent.ml_security_checker import run_security_check
                ml_findings = run_security_check(source)
                for f in ml_findings:
                    msg = f"[{f['severity']}] {f['msg']} (CWE: {f['cwe']})"
                    diag.report("Security", f["id"], msg, line=f["line"])
                    sec_warnings.append(msg)
            except Exception:
                pass

        # AST-based Optimization Hints
        try:
            ast_opt = ASTOptimizationAnalyzer(diag)
            ast_opt.analyze(ast)
        except Exception:
            pass

        # Optimization Hints (rule-based + ML)
        opt_hints = []
        try:
            opt_hints = get_optimization_hints(source)
        except Exception:
            pass

        # Execution
        try:
            interp = Interpreter()
            output = interp.execute(ast)
        except Exception as e:
            output = f"Runtime Error: {e}"

        st.session_state.run_result = {
            "out": output,
            "ast": ast,
            "diag": diag.get_all(),
            "security": sec_warnings,
            "opt": opt_hints,
        }
    else:
        st.session_state.run_result = {
            "out": "⚠️ Compilation failed — see Diagnostics tab.",
            "ast": None,
            "diag": diag.get_all(),
            "security": [],
            "opt": [],
        }

# ── Results Tabs ─────────────────────────────────────────────────────────────
if st.session_state.run_result:
    res = st.session_state.run_result
    tab_exec, tab_ast, tab_agent = st.tabs(["📟 Execution Output", "🌳 AST Viewer", "🧠 Agentic Fix"])

    with tab_exec:
        st.markdown("#### Console Output")

        # ── Quality Gate ──────────────────────────────────────────────────
        sec_issues = [d for d in res["diag"] if d["type"] == "Security"]
        opt_issues  = [h for h in res.get("opt", []) if h["severity"] in ("high", "medium")]
        blocked     = bool(sec_issues or opt_issues)

        if blocked:
            reasons = []
            if sec_issues:
                reasons.append(f"**{len(sec_issues)} security warning(s)**")
            if opt_issues:
                reasons.append(f"**{len(opt_issues)} high/medium optimization issue(s)**")
            st.error(
                f"🚫 **Execution blocked** — {' and '.join(reasons)} must be resolved first.\n\n"
                "Fix the issues shown below and re-run the program."
            )
        else:
            st.code(res["out"], language="text")

        st.markdown("#### Diagnostics")
        diag_list = res["diag"]
        if not diag_list:
            st.success("✅ No issues found — code compiled cleanly!")
        else:
            for d in diag_list:
                line_info = f" at Line {d['line']}" if d.get('line') else ""
                if d["type"] == "Security":
                    st.warning(f"🔒 **{d['type']}** [{d['code']}]{line_info}: {d['message']}")
                elif "Error" in d["type"]:
                    st.error(f"❌ **{d['type']}** [{d['code']}]{line_info}: {d['message']}")
                else:
                    st.info(f"ℹ️ **{d['type']}** [{d['code']}]{line_info}: {d['message']}")

        st.markdown("#### ⚡ Optimization Hints")
        opt_list = res.get("opt", [])
        if not opt_list:
            st.success("✅ No optimization issues detected.")
        else:
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}
            for h in opt_list:
                icon = sev_icon.get(h["severity"], "⚪")
                src_label = "[ML]" if h["src"] == "ml" else "[Rule]"
                with st.expander(f"{icon} **{h['severity'].upper()}** — Line {h['line']} · `{h['rule']}` {src_label}", expanded=True):
                    st.code(h["code"], language="c")
                    st.info(f"💡 {h['hint']}")

    with tab_ast:
        st.markdown("#### Abstract Syntax Tree")
        if res["ast"]:
            ast_text = visualize_ast(res["ast"])
            st.code(ast_text, language="text")
        else:
            st.warning("AST could not be generated. Fix syntax errors first.")

    with tab_agent:
        st.markdown("#### Agentic AI Debugger")
        st.caption("Uses AI (Gemini / Ollama) to reason about your code and propose a corrected patch.")

        if agentic_on:
            if st.button("🚀 Run Agentic Fix Loop", key="agent_btn"):
                with st.spinner("AI Agent is reasoning..."):
                    try:
                        agent = AgenticDebugger()
                        fix = agent.debug_and_fix(
                            st.session_state.code,
                            res["diag"],
                            model_name=ai_model
                        )
                        st.session_state.agent_fix = fix
                    except Exception as e:
                        st.session_state.agent_fix = f"Agent error: {e}"

            if st.session_state.agent_fix:
                st.markdown(st.session_state.agent_fix)
        else:
            st.info("Enable 'Agentic Self-Healing' in the sidebar to use this feature.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Agentic AI Compiler Assistant · Mini-C Language · Neuro-Symbolic Engine")
