class DiagnosticsEngine:
    def __init__(self):
        self.diagnostics = []

    def report(self, type_, code, message, line=None, column=None):
        self.diagnostics.append({
            'type': type_,
            'code': code,
            'message': message,
            'line': line,
            'column': column
        })

    def get_all(self):
        return self.diagnostics

    def clear(self):
        self.diagnostics = []
