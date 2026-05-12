import os
import requests
from bs4 import BeautifulSoup
import time

KB_FOLDER = "knowledge_base"
os.makedirs(KB_FOLDER, exist_ok=True)

SCRAPE_SOURCES = {
    "fastapi_errors.md": [
        "https://fastapi.tiangolo.com/tutorial/handling-errors/",
        "https://fastapi.tiangolo.com/tutorial/body/",
        "https://fastapi.tiangolo.com/tutorial/response-model/",
        "https://fastapi.tiangolo.com/tutorial/middleware/",
        "https://fastapi.tiangolo.com/tutorial/cors/",
    ],
    "python_errors.md": [
        "https://docs.python.org/3/library/exceptions.html",
        "https://realpython.com/python-exceptions/",
    ],
    "pydantic_validation.md": [
        "https://docs.pydantic.dev/latest/concepts/validators/",
        "https://docs.pydantic.dev/latest/concepts/fields/",
    ],
    "langchain_rag.md": [
        "https://python.langchain.com/docs/concepts/rag/",
        "https://python.langchain.com/docs/concepts/vectorstores/",
    ],
    "asyncio_guide.md": [
        "https://docs.python.org/3/library/asyncio-task.html",
    ],
}

SO_TAGS = ["fastapi", "langchain", "ollama", "faiss", "pydantic"]
HEADERS = {"User-Agent": "Mozilla/5.0 (educational knowledge base builder)"}

def scrape_url(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines[:300])
    except Exception as e:
        return f"[Failed to scrape {url}: {e}]"

def scrape_stackoverflow_tag(tag: str) -> str:
    url = f"https://stackoverflow.com/questions/tagged/{tag}?sort=votes&pagesize=15"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        questions = soup.select(".s-post-summary--content")
        lines = [f"## {q.get_text(strip=True)[:200]}" for q in questions[:10]]
        return "\n\n".join(lines)
    except Exception as e:
        return f"[Failed to scrape SO tag {tag}: {e}]"

print("🌐 Scraping documentation sources...")
for filename, urls in SCRAPE_SOURCES.items():
    path = os.path.join(KB_FOLDER, filename)
    content = f"# {filename.replace('_', ' ').replace('.md', '').title()}\n\n"
    content += f"> Auto-generated from {len(urls)} sources\n\n"
    for url in urls:
        print(f"  Scraping: {url}")
        content += f"## Source: {url}\n\n"
        content += scrape_url(url)
        content += "\n\n---\n\n"
        time.sleep(0.5)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Saved {filename} ({len(content)} chars)")

print("\n📚 Scraping Stack Overflow...")
so_content = "# Stack Overflow — Top Questions\n\n"
for tag in SO_TAGS:
    print(f"  Scraping SO tag: {tag}")
    so_content += f"## Tag: {tag}\n\n"
    so_content += scrape_stackoverflow_tag(tag)
    so_content += "\n\n---\n\n"
    time.sleep(1)
with open(os.path.join(KB_FOLDER, "stackoverflow_qa.md"), "w", encoding="utf-8") as f:
    f.write(so_content)
print("  ✅ Saved stackoverflow_qa.md")

print("\n📂 Scanning your codebase...")
SCAN_DIRS  = ["routes", "services", "rag", "models"]
SCAN_FILES = ["main.py"]
codebase_content = "# Your Codebase — Auto-scanned\n\n"

def scan_file(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        return f"## File: {filepath}\n```python\n{code}\n```\n\n"
    except:
        return ""

for fname in SCAN_FILES:
    if os.path.exists(fname):
        codebase_content += scan_file(fname)
        print(f"  Scanned: {fname}")

for d in SCAN_DIRS:
    if os.path.exists(d):
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    fpath = os.path.join(root, file)
                    codebase_content += scan_file(fpath)
                    print(f"  Scanned: {fpath}")

with open(os.path.join(KB_FOLDER, "your_codebase.md"), "w", encoding="utf-8") as f:
    f.write(codebase_content)
print("  ✅ Saved your_codebase.md")

files = os.listdir(KB_FOLDER)
total_size = sum(os.path.getsize(os.path.join(KB_FOLDER, f)) for f in files)
print(f"\n✅ Knowledge base built! {len(files)} files, {total_size/1024:.1f} KB")
print("👉 Next: python scripts/build_index.py")