import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import time

CHUNKS_FILE = "chunks.jsonl"
PERSIST_DIR = "chroma_db"
MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"  # Cloud-based sentence transformer model
)


def main():
    # Load the embedding model
    model = SentenceTransformer(MODEL_NAME)

    # Initialize Chroma client with persistence directory
    settings = Settings(
        persist_directory=PERSIST_DIR, anonymized_telemetry=False, is_persistent=True
    )
    client = chromadb.Client(settings)

    print(f"[INFO] ChromaDB client initialized with persistence to: {PERSIST_DIR}")

    # Get or create collection
    try:
        collection = client.get_collection("ismt_docs")
    except Exception:
        collection = client.create_collection("ismt_docs")

    # Check if chunks file exists
    if not Path(CHUNKS_FILE).exists():
        print(f"ERROR: {CHUNKS_FILE} not found.")
        return

    # Load documents and metadata
    documents = []
    metadatas = []
    ids = []
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            ids.append(str(i))
            documents.append(d["text"])
            metadatas.append({"url": d.get("url", "")})

    print(f"Generating embeddings for {len(documents)} chunks with {MODEL_NAME}...")
    t0 = time.time()
    embeddings = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)
    t1 = time.time()
    print(f"Embeddings done in {t1 - t0:.1f}s")

    # Delete old embeddings if any
    try:
        collection.delete(delete_all=True)
    except Exception:
        pass

    # Add embeddings in batches
    BATCH = 256
    for i in range(0, len(documents), BATCH):
        batch_ids = ids[i : i + BATCH]
        batch_docs = documents[i : i + BATCH]
        batch_emb = embeddings[i : i + BATCH].tolist()
        batch_meta = metadatas[i : i + BATCH]
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_emb,
            metadatas=batch_meta,
        )

    # [INFO] Persistence is automatic, no need to call client.persist()
    print(f"[DONE] Stored embeddings in Chroma persistent directory: {PERSIST_DIR}")


if __name__ == "__main__":
    main()
