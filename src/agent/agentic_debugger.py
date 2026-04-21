from src.agent.neuro_symbolic_analyzer import NeuroSymbolicAnalyzer

class AgenticDebugger(NeuroSymbolicAnalyzer):
    def debug_and_fix(self, source_code, diagnostics, model_name=None):
        if not diagnostics:
            return "Code looks good! No issues to fix."
        
        try:
            analysis = self.analyze(source_code, diagnostics, [], model_name=model_name)
            return analysis if analysis else "AI returned empty response."
        except Exception as e:
            return f"Agent Error: {str(e)}"
