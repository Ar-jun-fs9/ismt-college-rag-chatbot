import json
from pathlib import Path

INPUT_FILE = "crawled_pages.jsonl"
OUTPUT_FILE = "chunks.jsonl"
CHUNK_SIZE = 400  # words per chunk


def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])


def main():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"ERROR: {INPUT_FILE} not found.")
        return

    chunks = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            url = data.get("url", "")
            text = data.get("text", "").strip()
            if len(text) < 50:
                continue
            for c in chunk_text(text):
                chunks.append({"url": url, "text": c})

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in chunks:
            json.dump(c, f, ensure_ascii=False)
            f.write("\n")

    print(f"[DONE] Created {len(chunks)} chunks -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
