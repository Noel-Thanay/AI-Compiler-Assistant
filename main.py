import sys
import subprocess

def main():
    print("🚀 Launching Agentic AI Compiler Assistant...")
    cmd = [sys.executable, "-m", "streamlit", "run", "src/ui/app_streamlit.py"]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutdown complete.")

if __name__ == "__main__":
    main()
