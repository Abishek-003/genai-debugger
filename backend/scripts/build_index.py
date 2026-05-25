import os
import shutil
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag.vector_store import build_index, INDEX_PATH


def main() -> None:
    index_path = os.path.abspath(INDEX_PATH)

    if not index_path or index_path in {"/", "\\"}:
        raise RuntimeError(f"Refusing to delete unsafe index path: {index_path}")

    if os.path.exists(index_path):
        if not os.path.isdir(index_path):
            raise RuntimeError(f"INDEX_PATH exists but is not a directory: {index_path}")

        shutil.rmtree(index_path)
        print(f"Deleted old index at {index_path}")

    build_index()
    print("Index rebuilt successfully")


if __name__ == "__main__":
    main()