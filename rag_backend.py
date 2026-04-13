import os
import hashlib
import time
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from openai import OpenAI

load_dotenv()

PERSIST_DIR = "chroma_db"
CHROMA_COLLECTION = "ismt_docs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 2

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"

sbert = None
client = None
collection = None
groq_client = None
_components_initialized = False
llm_available = False

_response_cache = {}
MAX_CACHE_SIZE = 500

def _get_cache_key(question):
    return hashlib.md5(question.lower().strip().encode()).hexdigest()

def initialize_components():
    global sbert, client, collection, groq_client, _components_initialized, llm_available

    if _components_initialized:
        return

    print(f"[INFO] Loading embedding model: {EMBED_MODEL} ...")
    sbert = SentenceTransformer(EMBED_MODEL)

    print(f"[INFO] Connecting to ChromaDB at '{PERSIST_DIR}' ...")
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        collection = client.get_collection(CHROMA_COLLECTION)
        print(f"[OK] Found collection '{CHROMA_COLLECTION}' with {collection.count()} items.")
    except Exception:
        print(f"[WARN] Collection '{CHROMA_COLLECTION}' not found, creating a new one.")
        collection = client.create_collection(CHROMA_COLLECTION)

    print("[INFO] Initializing Groq API client...")
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY environment variable not set")
        groq_client = None
        llm_available = False
    else:
        try:
            groq_client = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
            llm_available = True
            print("[OK] Groq API client initialized successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Groq API client: {e}")
            groq_client = None
            llm_available = False

    _components_initialized = True

def retrieve(query: str, top_k: int = TOP_K):
    initialize_components()

    if sbert is None or collection is None:
        initialize_components()

    if sbert is None or collection is None:
        return []

    q_vec = sbert.encode(query, convert_to_numpy=True, normalize_embeddings=True).tolist()
    results = collection.query(
        query_embeddings=[q_vec], n_results=top_k, include=["documents", "metadatas"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return [{"text": d, "meta": m} for d, m in zip(docs, metas)]


def build_prompt(question, retrieved):
    context_blocks = []
    for r in retrieved[:TOP_K]:
        url = r["meta"].get("url", "unknown")
        text = r["text"].strip()
        if len(text) > 150:
            text = text[:150] + "..."
        context_blocks.append(f"[{url}] {text}")
    return "\n".join(context_blocks)


def call_groq_api(user_query: str, context_text: str) -> str:
    initialize_components()

    if not llm_available or groq_client is None:
        return "[LLM unavailable. Check GROQ_API_KEY and restart.]"

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant of ISMT College. "
                        "Answer user questions concisely, politely, and base your answer only on the provided context."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nQuestion: {user_query}",
                },
            ],
            temperature=0.2,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower() or "Invalid API Key" in error_msg:
            return "API key not configured. Add it or Please contact admin."
        return f"Error: Groq API failed. Details: {error_msg}"


def generate_answer(question: str, use_llm: bool = True):
    cache_key = _get_cache_key(question)
    
    if cache_key in _response_cache and use_llm:
        return _response_cache[cache_key]

    retrieved = retrieve(question)
    if not retrieved:
        result = {
            "answer": "I could not find relevant information in ISMT resources.",
            "sources": [],
        }
        return result

    sources = [
        f'<a href="{r["meta"].get("url")}" target="_blank">{r["meta"].get("url")}</a>'
        for r in retrieved
        if r["meta"].get("url")
    ]

    if not use_llm:
        context = "\n".join(
            [
                f"[{r['meta'].get('url', 'unknown')}] {r['text'][:200]}..."
                for r in retrieved[:TOP_K]
            ]
        )
        result = {
            "answer": f"📋 Retrieved information:\n\n{context}\n\n(LLM disabled)",
            "sources": sources,
        }
        if use_llm:
            if len(_response_cache) >= MAX_CACHE_SIZE:
                _response_cache.pop(next(iter(_response_cache)))
            _response_cache[cache_key] = result
        return result

    context_text = build_prompt(question, retrieved)
    answer = call_groq_api(question, context_text)
    result = {"answer": answer, "sources": sources}
    
    if len(_response_cache) >= MAX_CACHE_SIZE:
        _response_cache.pop(next(iter(_response_cache)))
    _response_cache[cache_key] = result
    
    return result


if __name__ == "__main__":
    print("[OK] ISMT College RAG Chatbot Ready!\n")
    while True:
        q = input("You: ")
        if q.lower() in ["exit", "quit"]:
            break
        res = generate_answer(q)
        print("\nAnswer:", res["answer"])
        print("Sources:", ", ".join(res["sources"]), "\n")


# version 2 to run locally


# import os
# import json
# from dotenv import load_dotenv
# import chromadb
# from chromadb.config import Settings
# from sentence_transformers import SentenceTransformer
# from openai import OpenAI

# # Load environment variables from .env file
# load_dotenv()

# # CONFIG
# PERSIST_DIR = "chroma_db"
# CHROMA_COLLECTION = "ismt_docs"
# EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# TOP_K = 2  # Reduced from 3 for faster retrieval

# # Groq API Configuration
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# GROQ_MODEL = "llama-3.1-8b-instant"

# # Initialize globals
# sbert = None
# client = None
# collection = None
# llm_available = False
# groq_client = None
# _components_initialized = False


# def initialize_components():
#     """Initialize all components (called once to avoid duplicate prints)."""
#     global sbert, client, collection, llm_available, groq_client, _components_initialized

#     # Only initialize if not already done
#     if not _components_initialized:
#         print(f"[INFO] Loading embedding model: {EMBED_MODEL} ...")
#         sbert = SentenceTransformer(EMBED_MODEL)

#         print(f"[INFO] Connecting to ChromaDB at '{PERSIST_DIR}' ...")
#         client = chromadb.PersistentClient(path=PERSIST_DIR)

#         try:
#             collection = client.get_collection(CHROMA_COLLECTION)
#             print(
#                 f"[OK] Found collection '{CHROMA_COLLECTION}' with {collection.count()} items."
#             )
#         except Exception:
#             print(
#                 f"[WARN] Collection '{CHROMA_COLLECTION}' not found, creating new one."
#             )
#             collection = client.create_collection(CHROMA_COLLECTION)

#         # Initialize Groq API client
#         print("[INFO] Initializing Groq API client...")
#         llm_available = False
#         groq_client = None

#         try:
#             if not GROQ_API_KEY:
#                 raise ValueError("GROQ_API_KEY environment variable not set")

#             groq_client = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
#             llm_available = True
#             print("[OK] Groq API client initialized successfully!")
#         except Exception as e:
#             print(f"[ERROR] Groq API initialization failed: {e}")
#             print("💡 Make sure to set the GROQ_API_KEY environment variable")
#             print("   Example: export GROQ_API_KEY='your-api-key-here'")
#             groq_client = None

#         _components_initialized = True


# # FUNCTIONS
# def retrieve(query: str, top_k: int = TOP_K):
#     """Retrieve top-k relevant documents from ChromaDB."""
#     # Ensure components are initialized
#     if sbert is None or collection is None:
#         initialize_components()

#     q_vec = sbert.encode(
#         query, convert_to_numpy=True, normalize_embeddings=True
#     ).tolist()
#     res = collection.query(
#         query_embeddings=[q_vec], n_results=top_k, include=["documents", "metadatas"]
#     )
#     docs = res.get("documents", [[]])[0]
#     metas = res.get("metadatas", [[]])[0]
#     return [{"text": d, "meta": m} for d, m in zip(docs, metas)]


# def build_prompt(question, retrieved):
#     """Build context and user prompt for Groq API."""
#     context_blocks = []
#     for r in retrieved[:2]:  # Only use top 2 results
#         url = r["meta"].get("url", "unknown")
#         text = r["text"].strip()
#         if len(text) > 200:
#             text = text[:200] + "..."
#         context_blocks.append(f"[{url}] {text}")

#     context = "\n".join(context_blocks)
#     return context


# def call_groq_api(user_query: str, context_text: str) -> str:
#     """Generate a response using Groq Cloud API."""
#     # Ensure components are initialized
#     if sbert is None or collection is None:
#         initialize_components()

#     if not llm_available or groq_client is None:
#         return "[LLM unavailable. Please check API key configuration and restart.]"

#     try:
#         response = groq_client.chat.completions.create(
#             model=GROQ_MODEL,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a helpful assistant of ISMT College. "
#                         "Always respond in first-person, as if you are speaking directly to the user. "
#                         "For example, say 'I can help you find our college location' or 'I offer this course.' "
#                         "Base your answers on the provided context and keep them concise and friendly."
#                     ),
#                 },
#                 {
#                     "role": "user",
#                     "content": f"Context:\n{context_text}\n\nQuestion: {user_query}",
#                 },
#             ],
#             temperature=0.3,
#             max_tokens=512,
#         )

#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         return f"Error: Groq API failed to generate a response. Details: {str(e)}"


# def generate_answer(question: str, use_llm: bool = True):
#     """Main pipeline: retrieve context → build prompt → call LLM."""
#     retrieved = retrieve(question)
#     if not retrieved:
#         return {
#             "answer": "I could not find relevant information in ISMT resources.",
#             "sources": [],
#         }

#     if not use_llm:
#         # Fallback: return retrieval results directly for testing
#         context = "\n".join(
#             [
#                 f"[{r['meta'].get('url', 'unknown')}] {r['text'][:200]}..."
#                 for r in retrieved[:2]
#             ]
#         )
#         sources = [
#             f'<a href="{r["meta"].get("url")}" target="_blank">{r["meta"].get("url")}</a>'
#             for r in retrieved
#             if r["meta"].get("url")
#         ]
#         return {
#             "answer": f"📋 Retrieved information:\n\n{context}\n\n(LLM generation disabled - showing raw retrieval results)",
#             "sources": sources,
#         }

#     context_text = build_prompt(question, retrieved)
#     answer = call_groq_api(question, context_text)
#     sources = [
#         f'<a href="{r["meta"].get("url")}" target="_blank">{r["meta"].get("url")}</a>'
#         for r in retrieved
#         if r["meta"].get("url")
#     ]
#     return {"answer": answer, "sources": sources}


# # ---------------- CLI TEST ----------------
# if __name__ == "__main__":
#     print("[OK] ISMT College RAG Chatbot Ready!\n")
#     while True:
#         q = input("You: ")
#         if q.lower() in ["exit", "quit"]:
#             break
#         res = generate_answer(q)
#         print("\nAnswer:", res["answer"])
#         print("Sources:", ", ".join(res["sources"]), "\n")
