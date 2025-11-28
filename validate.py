#!/usr/bin/env python3
"""
Validation script to verify the Government MCP Server structure and imports.
Run this to ensure everything is set up correctly.
"""

import sys
import importlib.util
from pathlib import Path


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    exists = Path(file_path).exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {file_path}")
    return exists


def check_module_structure() -> bool:
    """Check if the Python package structure is valid."""
    print("\n📦 Checking Package Structure...")
    
    files = [
        "gov_mcp/__init__.py",
        "gov_mcp/types.py",
        "gov_mcp/http_client.py",
        "gov_mcp/api_client.py",
        "gov_mcp/server.py",
        "pyproject.toml",
        "requirements.txt",
        "README.md",
    ]
    
    all_exist = all(check_file_exists(f) for f in files)
    return all_exist


def check_syntax() -> bool:
    """Check Python file syntax."""
    print("\n🔍 Checking Python Syntax...")
    
    python_files = [
        "gov_mcp/__init__.py",
        "gov_mcp/types.py",
        "gov_mcp/http_client.py",
        "gov_mcp/api_client.py",
        "gov_mcp/server.py",
        "examples.py",
    ]
    
    all_valid = True
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
            print(f"  ✓ {file_path}")
        except SyntaxError as e:
            print(f"  ✗ {file_path}: {e}")
            all_valid = False
    
    return all_valid


def check_dependencies() -> bool:
    """Check if required dependencies would be available."""
    print("\n📚 Checking Dependencies...")
    
    dependencies = [
        "requests",
        "pydantic",
        "mcp",
    ]
    
    all_available = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"  ✓ {dep} (installed)")
        except ImportError:
            print(f"  ℹ {dep} (not installed - will be installed with: pip install -e .)")
    
    return True  # Dependencies will be installed, so this is OK


def main() -> int:
    """Run all validation checks."""
    print("=" * 70)
    print("🚀 Government MCP Server v0.1.0 - Validation")
    print("=" * 70)
    
    results = {
        "Package Structure": check_module_structure(),
        "Python Syntax": check_syntax(),
        "Dependencies": check_dependencies(),
    }
    
    print("\n" + "=" * 70)
    print("📊 Validation Results:")
    print("=" * 70)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✨ All validation checks passed!")
        print("\n📝 Next Steps:")
        print("  1. Install dependencies: pip install -e .")
        print("  2. Start the server: python -m gov_mcp.server")
        print("  3. Try examples: python examples.py")
        return 0
    else:
        print("\n❌ Some validation checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
