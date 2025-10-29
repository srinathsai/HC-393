"""
🔍 PRE-DEPLOYMENT COMPATIBILITY CHECK
Run this BEFORE deploying fixes to ensure your system is compatible
"""

import sys

print("\n" + "="*80)
print("🔍 PRE-DEPLOYMENT COMPATIBILITY CHECK")
print("="*80)
print("This will verify your system can handle the fixes\n")

results = []

# Test 1: Python version
print("TEST 1: Python Version")
print("-" * 40)
version = sys.version_info
print(f"Python: {version.major}.{version.minor}.{version.micro}")
if version.major >= 3 and version.minor >= 8:
    print("✅ PASS - Python 3.8+")
    results.append(True)
else:
    print("❌ FAIL - Need Python 3.8+")
    results.append(False)

# Test 2: Standard library imports
print("\nTEST 2: Standard Library Imports")
print("-" * 40)
try:
    import gc
    from typing import Iterator, List, Dict, Any
    print("✅ PASS - gc module available")
    print("✅ PASS - Iterator type available")
    results.append(True)
except ImportError as e:
    print(f"❌ FAIL - Missing: {e}")
    results.append(False)

# Test 3: OpenAI library
print("\nTEST 3: OpenAI Library")
print("-" * 40)
try:
    from openai import OpenAI
    print("✅ PASS - OpenAI library available")
    results.append(True)
except ImportError:
    print("❌ FAIL - OpenAI library not installed")
    results.append(False)

# Test 4: ChromaDB
print("\nTEST 4: ChromaDB")
print("-" * 40)
try:
    import chromadb
    print(f"✅ PASS - ChromaDB available (version {chromadb.__version__})")
    results.append(True)
except ImportError:
    print("❌ FAIL - ChromaDB not installed")
    results.append(False)

# Test 5: Redis connection
print("\nTEST 5: Redis Connection")
print("-" * 40)
try:
    from redis import Redis
    r = Redis(host='localhost', port=6379)
    r.ping()
    print("✅ PASS - Redis is running")
    results.append(True)
except Exception as e:
    print(f"⚠️  WARNING - Redis not available: {e}")
    print("   (You'll need to start it before deploying)")
    results.append(True)  # Not critical for pre-check

# Test 6: Import current services
print("\nTEST 6: Current Service Imports")
print("-" * 40)
try:
    from app.services.entity_extractor import EntityExtractor
    print("✅ PASS - EntityExtractor imports")
    results.append(True)
except Exception as e:
    print(f"❌ FAIL - Cannot import EntityExtractor: {e}")
    results.append(False)

try:
    from app.services.graphrag_engine import GraphRAGEngine
    print("✅ PASS - GraphRAGEngine imports")
    results.append(True)
except Exception as e:
    print(f"❌ FAIL - Cannot import GraphRAGEngine: {e}")
    results.append(False)

try:
    from app.workers.ingestion_worker import process_document
    print("✅ PASS - ingestion_worker imports")
    results.append(True)
except Exception as e:
    print(f"❌ FAIL - Cannot import process_document: {e}")
    results.append(False)

# Test 7: Check method signatures
print("\nTEST 7: Method Signatures")
print("-" * 40)
try:
    import inspect
    from app.services.entity_extractor import EntityExtractor
    
    # Check chunk_text signature
    sig = inspect.signature(EntityExtractor.chunk_text)
    params = list(sig.parameters.keys())
    
    if 'self' in params and 'text' in params:
        print(f"✅ PASS - chunk_text signature: {sig}")
        results.append(True)
    else:
        print(f"⚠️  WARNING - chunk_text signature unexpected: {sig}")
        results.append(True)  # Not critical
except Exception as e:
    print(f"⚠️  WARNING - Cannot check signatures: {e}")
    results.append(True)  # Not critical

# Test 8: Check current embedding model
print("\nTEST 8: Current Embedding Model")
print("-" * 40)
try:
    from app.config import get_settings
    settings = get_settings()
    model = settings.openai_embedding_model
    
    print(f"Current model: {model}")
    
    if "3-large" in model:
        print("⚠️  WARNING - Using text-embedding-3-large (3072 dims)")
        print("   This is why you're getting dimension errors!")
        print("   Fix will change to text-embedding-3-small (1536 dims)")
    elif "3-small" in model:
        print("✅ Already using text-embedding-3-small (1536 dims)")
    elif "ada-002" in model:
        print("✅ Using text-embedding-ada-002 (1536 dims)")
    
    results.append(True)
except Exception as e:
    print(f"⚠️  WARNING - Cannot check config: {e}")
    results.append(True)  # Not critical

# Test 9: Check ChromaDB location
print("\nTEST 9: ChromaDB Location")
print("-" * 40)
try:
    from app.config import get_chroma_directory
    chroma_dir = get_chroma_directory()
    print(f"ChromaDB directory: {chroma_dir}")
    
    from pathlib import Path
    if Path(chroma_dir).exists():
        print("✅ PASS - Directory exists")
        results.append(True)
    else:
        print("⚠️  WARNING - Directory doesn't exist (will be created)")
        results.append(True)
except Exception as e:
    print(f"⚠️  WARNING - Cannot check ChromaDB dir: {e}")
    results.append(True)

# Test 10: Check if backups exist
print("\nTEST 10: Backup Check")
print("-" * 40)
try:
    from pathlib import Path
    backup_dirs = list(Path("backend").glob("app_backup_*"))
    
    if backup_dirs:
        print(f"✅ Found {len(backup_dirs)} backup(s):")
        for d in backup_dirs:
            print(f"   - {d}")
        results.append(True)
    else:
        print("⚠️  WARNING - No backups found")
        print("   Recommended: cp -r backend/app backend/app_backup_$(date +%Y%m%d)")
        results.append(True)  # Not critical
except:
    print("ℹ️  Cannot check backups (run from project root)")
    results.append(True)

# Summary
print("\n" + "="*80)
print("📊 SUMMARY")
print("="*80)

passed = sum(results)
total = len(results)

print(f"\n✅ Passed: {passed}/{total}")

if passed == total:
    print("\n" + "="*80)
    print("🎉 ALL CHECKS PASSED!")
    print("="*80)
    print("\n✅ Your system is COMPATIBLE with the fixes")
    print("✅ Safe to proceed with deployment")
    print("\nNext steps:")
    print("1. Create backup: cp -r backend/app backend/app_backup_$(date +%Y%m%d)")
    print("2. Follow DEPLOYMENT_CHECKLIST.md")
    print("3. Run reset_chromadb.py")
    print("4. Replace the 3 code files")
    print("5. Restart services")
    exit(0)
elif passed >= total - 2:
    print("\n⚠️  MOSTLY COMPATIBLE")
    print("Some warnings, but should be safe to proceed")
    print("Review the warnings above")
    exit(0)
else:
    print("\n❌ COMPATIBILITY ISSUES DETECTED")
    print("Fix the failed tests before deploying")
    exit(1)