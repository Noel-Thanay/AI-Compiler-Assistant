import math
import random
import re
import os
import joblib
from collections import defaultdict, Counter
from typing import List, Tuple, Dict, Optional

KEYWORDS = ["int", "float", "bool", "char", "string", "true", "false", "null", "print", "func", "return", "if", "else", "while", "array", "void"]
OPERATORS = ["+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!"]
SYMBOLS = [";", "(", ")", "{", "}", "[", "]", ","]
ALL_VOCAB = KEYWORDS + OPERATORS + SYMBOLS

CORPUS = [
    ["void", "main", "(", ")", "{", "int", "x", "=", "0", ";", "return", "x", ";", "}"],
    ["int", "x", "=", "10", ";", "int", "y", "=", "20", ";", "int", "z", "=", "x", "+", "y", ";"],
    ["if", "(", "x", ">", "0", ")", "{", "print", "(", "x", ")", ";", "}"],
    ["if", "(", "x", ">", "0", ")", "{", "print", "(", "x", ")", ";", "}", "else", "{", "print", "(", "0", ")", ";", "}"],
    ["while", "(", "x", "<", "10", ")", "{", "x", "=", "x", "+", "1", ";", "}"],
    ["int", "add", "(", "int", "a", ",", "int", "b", ")", "{", "return", "a", "+", "b", ";", "}"],
    ["bool", "flag", "=", "true", ";", "if", "(", "flag", ")", "{", "print", "(", "flag", ")", ";", "}"],
    ["float", "pi", "=", "3.14", ";", "float", "area", "=", "pi", "*", "r", "*", "r", ";"],
    ["int", "n", "=", "0", ";", "if", "(", "n", "<", "0", ")", "{", "return", ";", "}"],
    ["int", "factorial", "(", "int", "n", ")", "{", "if", "(", "n", "==", "0", ")", "{", "return", "1", ";", "}", "return", "n", "*", "factorial", "(", "n", "-", "1", ")", ";", "}"],
    ["array", "int", "arr", "[", "10", "]", ";"],
    ["string", "name", "=", "null", ";", "print", "(", "name", ")", ";"],
    ["char", "c", "=", "null", ";"],
    ["while", "(", "true", ")", "{", "int", "x", "=", "0", ";", "if", "(", "x", "==", "0", ")", "{", "return", ";", "}", "}"],
    ["void", "swap", "(", "int", "a", ",", "int", "b", ")", "{", "int", "tmp", "=", "a", ";", "a", "=", "b", ";", "b", "=", "tmp", ";", "}"]
]

SNIPPETS = {
    "func": "void my_func() {\n    // code\n}",
    "if": "if (true) {\n    // code\n}",
    "else": "else {\n    // code\n}",
    "while": "while (false) {\n    // code\n}",
    "return": "return 0;",
    "int": "int x = 0;",
    "float": "float f = 0.0;",
    "bool": "bool b = true;",
    "string": "string s = \"\";",
    "array": "int arr[10];",
    "print": "print(x);"
}

def suggest_snippet(token: str) -> Optional[str]:
    return SNIPPETS.get(token)

def extract_symbols(source: str):
    symbols = []
    seen = set()
    
    def add_sym(name, kind):
        if name not in seen and name not in KEYWORDS:
            seen.add(name)
            symbols.append((name, kind))

    try:
        from src.compiler.lexer import lexer
        lexer.input(source)
        prev_tok = None
        while True:
            tok = lexer.token()
            if not tok: break
            if tok.type == 'ID':
                kind = "symbol"
                if prev_tok:
                    if prev_tok.type in ["INT", "FLOAT", "BOOL", "STRING_TYPE", "VOID", "ARRAY"]:
                        kind = "variable"
                add_sym(tok.value, kind)
            prev_tok = tok
    except Exception:
        pass
        
    return symbols

class NgramModel:
    def __init__(self, n: int = 3, k: float = 0.1):
        self.n = n
        self.k = k
        self.counts = defaultdict(Counter)
        self.vocab = set(ALL_VOCAB)

    def train(self, corpus):
        for sent in corpus:
            padded = ["<s>"] * (self.n - 1) + sent + ["</s>"]
            for t in sent:
                self.vocab.add(t)
            for i in range(len(padded) - self.n + 1):
                ctx = tuple(padded[i : i + self.n - 1])
                nxt = padded[i + self.n - 1]
                self.counts[ctx][nxt] += 1

    def top_k(self, ctx: Tuple, k: int = 10):
        ctx = ctx[-(self.n - 1):]
        V = len(self.vocab)
        total = sum(self.counts[ctx].values())
        scores = {}
        for t in self.vocab:
            cnt = self.counts[ctx][t]
            scores[t] = (cnt + self.k) / (total + self.k * V)
            
        items = list(scores.items())
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:k]

def _sig(x: float) -> float:
    val = max(-500, min(500, x))
    return 1 / (1 + math.exp(-val))

def _tanh(x: float) -> float:
    val = max(-500, min(500, x))
    return math.tanh(val)

class LSTMCell:
    def __init__(self):
        def r(): return random.uniform(-0.5, 0.5)
        self.wi, self.ui, self.bi = r(), r(), 0.0
        self.wf, self.uf, self.bf = r(), r(), 1.0
        self.wo, self.uo, self.bo = r(), r(), 0.0
        self.wg, self.ug, self.bg = r(), r(), 0.0

    def forward(self, x: float, h: float, c: float):
        i = _sig(self.wi * x + self.ui * h + self.bi)
        f = _sig(self.wf * x + self.uf * h + self.bf)
        o = _sig(self.wo * x + self.uo * h + self.bo)
        g = _tanh(self.wg * x + self.ug * h + self.bg)
        new_c = f * c + i * g
        new_h = o * _tanh(new_c)
        return new_h, new_c

class MiniLSTM:
    def __init__(self, vocab):
        random.seed(42)
        self.idx = {vocab[i]: i for i in range(len(vocab))}
        self.size = max(len(vocab), 1)
        self.cell = LSTMCell()

    def encode(self, tokens):
        h, c = 0.0, 0.0
        for t in tokens:
            val = self.idx.get(t, 0)
            h, c = self.cell.forward(val / self.size, h, c)
        return h

    def rerank(self, candidates, ctx, alpha=0.35):
        h0 = self.encode(ctx)
        out = []
        for tok, prob in candidates:
            h_new = self.encode(ctx + [tok])
            bias = (_tanh(h_new - h0) + 1) / 2
            score = (1 - alpha) * prob + alpha * bias
            out.append((tok, score))
        out.sort(key=lambda x: x[1], reverse=True)
        return out

class AutoCompleteEngine:
    def __init__(self):
        self.ngram = NgramModel(n=3, k=0.1)
        self.lstm = None
        self._ready = False

    def train(self, corpus=None):
        if corpus is None:
            corpus = CORPUS
            
        here = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(here, "..", "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        model_path = os.path.join(data_dir, "autocomplete_model_proper.pkl")
        
        if os.path.exists(model_path):
            try:
                saved = joblib.load(model_path)
                self.ngram = saved["ngram"]
                self.lstm = saved["lstm"]
                self._ready = True
                return
            except Exception:
                pass
                
        self.ngram.train(corpus)
        vocab_list = sorted(list(self.ngram.vocab))
        self.lstm = MiniLSTM(vocab_list)
        self._ready = True
        
        joblib.dump({"ngram": self.ngram, "lstm": self.lstm}, model_path)

    def _ctx(self, tokens):
        pad = ["<s>"] * (self.ngram.n - 1)
        combined = pad + tokens
        return tuple(combined[-(self.ngram.n - 1):])

    def complete_from_source(self, source, cursor, top_k=5):
        if not self._ready:
            self.train()
            
        text = source[:cursor]
        pat = re.compile(r"[A-Za-z_]\w*|[0-9]+(?:\.[0-9]+)?|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!;,(){}\[\]]")
        tokens = pat.findall(text)
        
        prefix = ""
        if len(tokens) > 0:
            last = tokens[-1]
            if re.fullmatch(r"[A-Za-z_]\w*", last):
                idx = text.rfind(last)
                if idx + len(last) == len(text):
                    prefix = tokens.pop()
                    
        cands = self.ngram.top_k(self._ctx(tokens), k=30)
        if self.lstm:
            cands = self.lstm.rerank(cands, tokens)
        
        extracted = extract_symbols(source)
        for sym, kind in extracted:
            cands.append((sym, 0.4)) 
            
        final_cands = []
        cands.sort(key=lambda x: x[1], reverse=True)
        
        seen_toks = set()
        
        try:
            from src.agent.security_analyzer import suspicious_strings, dangerous_identifiers
            banned = set(dangerous_identifiers + suspicious_strings)
        except Exception:
            banned = set()
            
        for t, s in cands:
            if prefix != "" and not t.startswith(prefix):
                continue
                
            # Security Check: do not suggest sensitive or dangerous words
            t_lower = str(t).lower()
            if any(b in t_lower for b in banned):
                continue
                
            if t not in seen_toks and t not in ["<s>", "</s>"]:
                seen_toks.add(t)
                final_cands.append((t, s))
                
        if prefix != "":
            for kw in ALL_VOCAB:
                if kw.startswith(prefix) and kw not in seen_toks:
                    seen_toks.add(kw)
                    final_cands.append((kw, 0.01))
                    
        return final_cands[:top_k], extracted, prefix
