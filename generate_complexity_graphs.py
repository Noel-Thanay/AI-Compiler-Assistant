import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

def get_python_files(directory):
    return glob.glob(f"{directory}/**/*.py", recursive=True)

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

    filename = os.path.basename(filepath)
    if filename == "__init__.py" and not source.strip():
        return None # skip empty __init__.py

    try:
        # Raw metrics
        raw_metrics = analyze(source)
        loc = raw_metrics.loc
        sloc = raw_metrics.sloc

        # Cyclomatic complexity
        cc_blocks = cc_visit(source)
        # Calculate average cyclomatic complexity
        if cc_blocks:
            avg_cc = sum(block.complexity for block in cc_blocks) / len(cc_blocks)
            max_cc = max(block.complexity for block in cc_blocks)
        else:
            avg_cc = 1
            max_cc = 1

        # Maintainability Index
        mi = mi_visit(source, multi=False)

        # Halstead metrics
        # For simplicity, calculate Halstead on the whole module using h_visit
        halstead_report = h_visit(source)
        # h_visit returns a report containing Halstead metrics
        # We can extract effort, volume, etc.
        try:
            h_volume = halstead_report.total.volume
            h_effort = halstead_report.total.effort
        except AttributeError:
            h_volume = 0
            h_effort = 0

        return {
            'Filename': filename,
            'Filepath': filepath,
            'LOC': loc,
            'SLOC': sloc,
            'Avg_Cyclomatic_Complexity': avg_cc,
            'Max_Cyclomatic_Complexity': max_cc,
            'Maintainability_Index': mi,
            'Halstead_Volume': h_volume,
            'Halstead_Effort': h_effort
        }
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def main():
    project_dir = "."
    files = get_python_files(project_dir)
    # Ignore env, venv, hidden dirs
    files = [f for f in files if "env" not in f and "\\." not in f and "scratch" not in f and "data" not in f]

    results = []
    for f in files:
        res = analyze_file(f)
        if res:
            results.append(res)

    df = pd.DataFrame(results)

    if df.empty:
        print("No data collected.")
        return

    # Set style
    sns.set_theme(style="whitegrid")
    
    os.makedirs("complexity_graphs", exist_ok=True)

    # 1. LOC vs SLOC
    plt.figure(figsize=(12, 6))
    df_loc = df.sort_values(by='LOC', ascending=False)
    sns.barplot(data=df_loc, x='Filename', y='LOC', color='lightblue', label='Total LOC')
    sns.barplot(data=df_loc, x='Filename', y='SLOC', color='darkblue', label='Source LOC')
    plt.xticks(rotation=45, ha='right')
    plt.title('Lines of Code (LOC) vs Source Lines of Code (SLOC) per File')
    plt.ylabel('Lines')
    plt.legend()
    plt.tight_layout()
    plt.savefig('complexity_graphs/loc_sloc.png')
    plt.close()

    # 2. Cyclomatic Complexity
    plt.figure(figsize=(12, 6))
    df_cc = df.sort_values(by='Max_Cyclomatic_Complexity', ascending=False)
    sns.barplot(data=df_cc, x='Filename', y='Max_Cyclomatic_Complexity', color='salmon', label='Max CC')
    sns.barplot(data=df_cc, x='Filename', y='Avg_Cyclomatic_Complexity', color='darkred', label='Avg CC')
    plt.xticks(rotation=45, ha='right')
    plt.title('Cyclomatic Complexity (Max and Avg) per File')
    plt.ylabel('Complexity Score')
    plt.legend()
    plt.tight_layout()
    plt.savefig('complexity_graphs/cyclomatic_complexity.png')
    plt.close()

    # 3. Maintainability Index
    plt.figure(figsize=(12, 6))
    df_mi = df.sort_values(by='Maintainability_Index', ascending=True)
    # Color code MI: green > 20, yellow 10-20, red < 10
    colors = ['red' if x < 10 else 'orange' if x < 20 else 'green' for x in df_mi['Maintainability_Index']]
    sns.barplot(data=df_mi, x='Filename', y='Maintainability_Index', palette=colors)
    plt.xticks(rotation=45, ha='right')
    plt.title('Maintainability Index per File (Higher is better)')
    plt.ylabel('Maintainability Index (0-100)')
    plt.axhline(y=20, color='r', linestyle='--', label='Highly Maintainable Threshold')
    plt.axhline(y=10, color='r', linestyle=':', label='Moderately Maintainable Threshold')
    plt.tight_layout()
    plt.savefig('complexity_graphs/maintainability_index.png')
    plt.close()

    # 4. Halstead Effort
    plt.figure(figsize=(12, 6))
    df_he = df.sort_values(by='Halstead_Effort', ascending=False)
    sns.barplot(data=df_he, x='Filename', y='Halstead_Effort', color='purple')
    plt.xticks(rotation=45, ha='right')
    plt.title('Halstead Effort per File')
    plt.ylabel('Effort')
    plt.tight_layout()
    plt.savefig('complexity_graphs/halstead_effort.png')
    plt.close()

    # 5. Scatter Plot: SLOC vs Max Cyclomatic Complexity
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=df, x='SLOC', y='Max_Cyclomatic_Complexity', size='Halstead_Effort', sizes=(50, 500), hue='Maintainability_Index', palette='viridis')
    for i in range(df.shape[0]):
        plt.text(df['SLOC'][i]+1, df['Max_Cyclomatic_Complexity'][i], df['Filename'][i], fontsize=9)
    plt.title('Complexity Landscape: SLOC vs Max Cyclomatic Complexity')
    plt.tight_layout()
    plt.savefig('complexity_graphs/complexity_landscape_scatter.png')
    plt.close()

    print("Graphs generated successfully in 'complexity_graphs' folder.")
    # Also save the data to csv for record
    df.to_csv('complexity_graphs/complexity_metrics.csv', index=False)

if __name__ == "__main__":
    main()
