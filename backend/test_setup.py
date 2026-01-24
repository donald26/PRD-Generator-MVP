#!/usr/bin/env python3
"""
Quick test script to verify backend setup
"""
import sys
from pathlib import Path

print("🧪 Testing PRD Generator Backend Setup\n")
print("=" * 50)

# Test 1: Import prdgen modules
print("\n1. Testing prdgen imports...")
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prdgen.model import load_llama
    from prdgen.generator import generate_from_folder
    from prdgen.config import GenerationConfig
    from prdgen.ingest import ingest_folder
    print("   ✅ prdgen modules imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import prdgen: {e}")
    print("   💡 Make sure you've installed requirements.txt")
    sys.exit(1)

# Test 2: Import FastAPI
print("\n2. Testing FastAPI imports...")
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    import uvicorn
    print("   ✅ FastAPI imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import FastAPI: {e}")
    print("   💡 Run: pip install fastapi uvicorn python-multipart aiofiles")
    sys.exit(1)

# Test 3: Check directories
print("\n3. Checking directories...")
temp_dir = Path(__file__).parent / "temp"
outputs_dir = Path(__file__).parent / "outputs"

temp_dir.mkdir(exist_ok=True)
outputs_dir.mkdir(exist_ok=True)

print(f"   ✅ temp/ directory: {temp_dir}")
print(f"   ✅ outputs/ directory: {outputs_dir}")

# Test 4: Check example data
print("\n4. Checking example data...")
examples_dir = Path(__file__).parent.parent / "examples" / "loan_underwriting_docs"
if examples_dir.exists():
    files = list(examples_dir.glob("*"))
    print(f"   ✅ Found example data with {len(files)} files")
else:
    print(f"   ⚠️  Example data not found at {examples_dir}")

print("\n" + "=" * 50)
print("✅ All checks passed! Backend is ready.")
print("\nTo start the server, run:")
print("   uvicorn app.main:app --reload")
print("\nOr use the run script:")
print("   ./run.sh")
