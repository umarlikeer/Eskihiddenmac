"""Quick smoke test for the bundled calculation engine. Run from app/src/main/python."""
import json
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(ROOT, "app", "src", "main", "python")
sys.path.insert(0, PYTHON_DIR)
from mobile_api import run_optimization

DATA = os.path.join(ROOT, "app", "src", "main", "assets", "DATA_Q14.txt")

def main():
    for mode in ("baseline", "q", "taps", "combined"):
        result = json.loads(run_optimization(DATA, mode, population=10, generations=1))
        assert result.get("ok"), f"{mode}: {result.get('error')}"
        assert result["initial_losses"] >= 0
        assert len(result["final_voltages"]) == 13
        print(f"{mode}: initial={result['initial_losses']:.6f} MW; final={result['final_losses']:.6f} MW")
    print("Smoke test passed. This is a software test, not engineering validation.")

if __name__ == "__main__":
    main()
