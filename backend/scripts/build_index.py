import shutil
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rag.vector_store import build_index, INDEX_PATH

if os.path.exists(INDEX_PATH):
    shutil.rmtree(INDEX_PATH)
    print(f"🗑️  Deleted old index at {INDEX_PATH}")

build_index()
print("✅ Index rebuilt successfully")