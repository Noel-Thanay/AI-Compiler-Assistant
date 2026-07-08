import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.compiler.parser import parse as compiler_parse
from src.compiler.diagnostics_engine import DiagnosticsEngine
from src.runtime.interpreter import Interpreter

# Utility to count AST nodes
def count_ast_nodes(node):
    if node is None:
        return 0
    count = 1
    if hasattr(node, 'statements'):
        for stmt in node.statements:
            count += count_ast_nodes(stmt)
    if hasattr(node, 'values') and node.values:
        for val in node.values:
            count += count_ast_nodes(val)
    if hasattr(node, 'value') and isinstance(node.value, object) and hasattr(node.value, '__class__'):
        count += count_ast_nodes(node.value)
    if hasattr(node, 'left'):
        count += count_ast_nodes(node.left)
    if hasattr(node, 'right'):
        count += count_ast_nodes(node.right)
    if hasattr(node, 'operand'):
        count += count_ast_nodes(node.operand)
    if hasattr(node, 'condition'):
        count += count_ast_nodes(node.condition)
    if hasattr(node, 'then_branch'):
        for stmt in node.then_branch:
            count += count_ast_nodes(stmt)
    if hasattr(node, 'else_branch') and node.else_branch:
        for stmt in node.else_branch:
            count += count_ast_nodes(stmt)
    if hasattr(node, 'body'):
        for stmt in node.body:
            count += count_ast_nodes(stmt)
    if hasattr(node, 'expression'):
        count += count_ast_nodes(node.expression)
    return count


test_cases = [
    # 1. Trivial
    """
    void main() {
        int a = 1;
    }
    """,
    # 2. Simple assignment and arithmetic
    """
    void main() {
        int a = 1;
        int b = 2;
        int c = a + b;
    }
    """,
    # 3. Multiple variable declarations
    """
    void main() {
        int a = 1;
        int b = 2;
        int c = 3;
        int d = 4;
        int e = a + b + c + d;
    }
    """,
    # 4. Simple loop
    """
    void main() {
        int i = 0;
        while (i < 5) {
            i = i + 1;
        }
    }
    """,
    # 5. Loop with arithmetic
    """
    void main() {
        int a = 0;
        int i = 0;
        while (i < 5) {
            a = a + i * 2;
            i = i + 1;
        }
    }
    """,
    # 6. If condition
    """
    void main() {
        int a = 10;
        int b = 20;
        int max = 0;
        if (a > b) {
            max = a;
        } else {
            max = b;
        }
    }
    """,
    # 7. If condition inside loop
    """
    void main() {
        int a = 0;
        int i = 0;
        while (i < 10) {
            if (i > 5) {
                a = a + 1;
            } else {
                a = a + 2;
            }
            i = i + 1;
        }
    }
    """,
    # 8. Nested loops
    """
    void main() {
        int count = 0;
        int i = 0;
        while (i < 3) {
            int j = 0;
            while (j < 3) {
                count = count + 1;
                j = j + 1;
            }
            i = i + 1;
        }
    }
    """,
    # 9. Nested loops with if
    """
    void main() {
        int count = 0;
        int i = 0;
        while (i < 3) {
            int j = 0;
            while (j < 3) {
                if (i == j) {
                    count = count + 1;
                }
                j = j + 1;
            }
            i = i + 1;
        }
    }
    """,
    # 10. Deeply nested loops
    """
    void main() {
        int count = 0;
        int i = 0;
        while (i < 2) {
            int j = 0;
            while (j < 2) {
                int k = 0;
                while (k < 2) {
                    count = count + 1;
                    k = k + 1;
                }
                j = j + 1;
            }
            i = i + 1;
        }
    }
    """,
    # 11. Complex arithmetic inside loops
    """
    void main() {
        int val = 0;
        int i = 0;
        while (i < 10) {
            val = val + (i * 2) - (i / 1) + 5;
            i = i + 1;
        }
    }
    """,
    # 12. Multiple if-else branches inside loop
    """
    void main() {
        int x = 0;
        int i = 0;
        while (i < 10) {
            if (i == 1) { x = x + 1; }
            else {
                if (i == 2) { x = x + 2; }
                else {
                    if (i == 3) { x = x + 3; }
                    else { x = x + 4; }
                }
            }
            i = i + 1;
        }
    }
    """,
    # 13. High AST node count linear
    """
    void main() {
        int a = 1; int b = 2; int c = 3; int d = 4; int e = 5;
        int f = 6; int g = 7; int h = 8; int i = 9; int j = 10;
        int sum = a+b+c+d+e+f+g+h+i+j;
        int prod = a*b*c*d*e;
        int sub = j-i-h-g-f;
    }
    """,
    # 14. Nested block scopes (simulated with while loops with 1 iteration)
    """
    void main() {
        int a = 1;
        while (a < 2) {
            int b = 2;
            while (b < 3) {
                int c = 3;
                while (c < 4) {
                    int d = a + b + c;
                    c = c + 1;
                }
                b = b + 1;
            }
            a = a + 1;
        }
    }
    """,
    # 15. The complex beast (combined)
    """
    void main() {
        int a = 0;
        int i = 0;
        while (i < 5) {
            int j = 0;
            while (j < 5) {
                if (i > j) {
                    a = a + (i * j);
                } else {
                    if (i == j) {
                        a = a + 1;
                    } else {
                        a = a - 1;
                    }
                }
                j = j + 1;
            }
            i = i + 1;
        }
    }
    """
]

def run_experiment():
    results = []
    
    for idx, source in enumerate(test_cases, 1):
        print(f"Running Test Case {idx}...")
        diag = DiagnosticsEngine()
        
        # 1. Parsing Time
        start_parse = time.perf_counter()
        ast = compiler_parse(source, diag=diag)
        end_parse = time.perf_counter()
        parse_time_ms = (end_parse - start_parse) * 1000
        
        # Count SLOC
        sloc = len([line for line in source.splitlines() if line.strip() != ""])
        
        ast_nodes = count_ast_nodes(ast)
        
        # 2. Execution Time
        exec_time_ms = 0
        if ast and not diag.get_all():
            interp = Interpreter()
            start_exec = time.perf_counter()
            interp.execute(ast)
            end_exec = time.perf_counter()
            exec_time_ms = (end_exec - start_exec) * 1000
        
        results.append({
            "Test_Case": f"TC{idx}",
            "SLOC": sloc,
            "AST_Nodes": ast_nodes,
            "Parse_Time_ms": parse_time_ms,
            "Exec_Time_ms": exec_time_ms,
            "Total_Time_ms": parse_time_ms + exec_time_ms
        })

    df = pd.DataFrame(results)
    
    # Save raw data
    os.makedirs("experiment_results", exist_ok=True)
    df.to_csv("experiment_results/test_case_metrics.csv", index=False)
    
    # Generate Plots
    sns.set_theme(style="whitegrid")
    
    # Plot 1: AST Nodes vs Source Lines of Code (Complexity Mapping)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="SLOC", y="AST_Nodes", s=100, color="blue")
    sns.regplot(data=df, x="SLOC", y="AST_Nodes", scatter=False, color="blue", line_kws={"linestyle":"--"})
    for i in range(df.shape[0]):
        plt.text(df['SLOC'][i]+0.2, df['AST_Nodes'][i], df['Test_Case'][i], fontsize=9)
    plt.title("Source Code Complexity: AST Nodes vs SLOC")
    plt.ylabel("AST Node Count")
    plt.xlabel("Source Lines of Code (SLOC)")
    plt.tight_layout()
    plt.savefig("experiment_results/ast_vs_sloc.png")
    plt.close()
    
    # Plot 2: Processing Time vs AST Nodes
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="AST_Nodes", y="Parse_Time_ms", s=100, color="orange", label="Parse Time")
    sns.regplot(data=df, x="AST_Nodes", y="Parse_Time_ms", scatter=False, color="orange", line_kws={"linestyle":"--"})
    for i in range(df.shape[0]):
        plt.text(df['AST_Nodes'][i]+1, df['Parse_Time_ms'][i], df['Test_Case'][i], fontsize=9)
    plt.title("Compiler Behavior: Parse Time vs AST Nodes (Complexity)")
    plt.ylabel("Parse Time (ms)")
    plt.xlabel("AST Node Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig("experiment_results/parse_vs_ast.png")
    plt.close()

    # Plot 3: Execution Time vs AST Nodes
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="AST_Nodes", y="Exec_Time_ms", s=100, color="green", label="Execution Time")
    sns.regplot(data=df, x="AST_Nodes", y="Exec_Time_ms", scatter=False, color="green", line_kws={"linestyle":"--"})
    for i in range(df.shape[0]):
        plt.text(df['AST_Nodes'][i]+1, df['Exec_Time_ms'][i], df['Test_Case'][i], fontsize=9)
    plt.title("Compiler Behavior: Execution Time vs AST Nodes (Complexity)")
    plt.ylabel("Execution Time (ms)")
    plt.xlabel("AST Node Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig("experiment_results/exec_vs_ast.png")
    plt.close()
    
    # Plot 4: Bar chart of Total Time
    plt.figure(figsize=(12, 6))
    df_sorted = df.sort_values(by="AST_Nodes")
    sns.barplot(data=df_sorted, x="Test_Case", y="Total_Time_ms", palette="viridis")
    plt.title("Total Processing Time (Parse + Exec) per Test Case (Sorted by Complexity)")
    plt.ylabel("Total Time (ms)")
    plt.tight_layout()
    plt.savefig("experiment_results/total_time_bar.png")
    plt.close()
    
    print("Experiments completed successfully!")

if __name__ == "__main__":
    run_experiment()
