"""
Pipeline complet :
Question -> recherche RAG -> Gemini -> Réponse

Utilisable en ligne de commande :

    python rag/query_rag.py "Quels sont les symptômes du mildiou de la tomate ?"

Ou importé depuis un autre script :

    from rag.query_rag import answer_question
"""

import sys
import os
from pathlib import Path

from google import genai
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).parent.parent

CHROMA_DIR = BASE_DIR / "data" / "chroma_db"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
MIN_RELEVANCE_SCORE = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.05"))
_client = None


# ============================================================
# ChromaDB
# ============================================================

_embeddings = None
_vectordb = None


def normalize_crop(crop: str | None) -> str | None:
    if not crop:
        return None

    normalized = " ".join(crop.strip().lower().replace("_", " ").split())
    aliases = {
        "pomme": "pomme de terre",
        "pommes de terre": "pomme de terre",
        "pomme terre": "pomme de terre",
    }
    return aliases.get(normalized, normalized)


def get_vectordb():
    global _embeddings, _vectordb

    if _vectordb is None:

        if not CHROMA_DIR.exists():
            raise RuntimeError(
                "Index vectoriel introuvable. "
                "Lance d'abord : python rag/build_index.py"
            )

        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )

        _vectordb = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=_embeddings,
            collection_name="agri_diseases",
        )

    return _vectordb


# ============================================================
# Recherche RAG
# ============================================================

def retrieve_scored(
    question: str,
    k: int = 4,
    crop: str | None = None
):
    vectordb = get_vectordb()
    crop = normalize_crop(crop)

    search_kwargs = {
        "k": k
    }

    if crop:
        search_kwargs["filter"] = {
            "crop": crop
        }

    results = vectordb.similarity_search_with_relevance_scores(
        question,
        **search_kwargs
    )

    return [
        (doc, score)
        for doc, score in results
        if score >= MIN_RELEVANCE_SCORE
    ]


def retrieve(
    question: str,
    k: int = 4,
    crop: str | None = None
):
    return [doc for doc, _score in retrieve_scored(question, k=k, crop=crop)]


# ============================================================
# Construction du prompt
# ============================================================

def build_prompt(
    question: str,
    passages: list[str]
) -> str:

    context = "\n\n---\n\n".join(passages)

    return f"""
Tu es un assistant agricole expert.

Réponds à la question de l'agriculteur UNIQUEMENT
à partir du contexte fourni ci-dessous.

Règles :
- Utilise uniquement les informations présentes dans le contexte.
- N'invente aucune information.
- Si le contexte ne contient pas la réponse, dis-le honnêtement.
- Sois clair, précis et concis.
- Réponds en français.

Contexte :
{context}

Question :
{question}

Réponse :
"""


# ============================================================
# Gemini
# ============================================================

def call_gemini(
    prompt: str
) -> str | None:
    global _client

    if os.getenv("RAG_DISABLE_LLM") == "1" or not GEMINI_API_KEY:
        print("GEMINI_API_KEY absente : utilisation du fallback RAG")
        return None

    try:
        if _client is None:
            _client = genai.Client(api_key=GEMINI_API_KEY)

        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        if response.text:
            return response.text.strip()

        return None

    except Exception as e:

        print(f"Erreur Gemini, fallback RAG utilisé : {e}")

        return None


# ============================================================
# Pipeline RAG complet
# ============================================================

def answer_question(
    question: str,
    crop: str | None = None,
    k: int = 4
) -> dict:

    crop = normalize_crop(crop)

    # 1. Recherche dans ChromaDB
    scored_docs = retrieve_scored(
        question=question,
        k=k,
        crop=crop
    )
    docs = [doc for doc, _score in scored_docs]

    # 2. Récupération des passages
    passages = [
        doc.page_content
        for doc in docs
    ]

    # 3. Récupération des sources
    sources = [
        {
            "source": doc.metadata.get("source"),
            "crop": doc.metadata.get("crop"),
            "relevance": round(score, 3),
        }
        for doc, score in scored_docs
    ]

    # 4. Aucun résultat
    if not passages:
        return {
            "answer": (
                "Aucune information trouvée dans "
                "la base de connaissances pour cette question."
            ),
            "sources": [],
            "used_llm": False
        }

    # 5. Construction du prompt
    prompt = build_prompt(
        question=question,
        passages=passages
    )

    # 6. Appel Gemini
    llm_answer = call_gemini(prompt)

    # 7. Réponse Gemini
    if llm_answer:
        return {
            "answer": llm_answer,
            "sources": sources,
            "used_llm": True
        }

    # 8. Fallback
    fallback = (
        "[Gemini indisponible]\n\n"
        "Voici les passages les plus pertinents "
        "trouvés dans la base de connaissances :\n\n"
        + "\n\n---\n\n".join(passages)
    )

    return {
        "answer": fallback,
        "sources": sources,
        "used_llm": False
    }


# ============================================================
# Exécution depuis le terminal
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            'Usage : python rag/query_rag.py '
            '"ta question"'
        )

        sys.exit(1)

    question = " ".join(sys.argv[1:])

    result = answer_question(
        question=question
    )

    print("\n==============================")
    print("RÉPONSE")
    print("==============================\n")

    print(result["answer"])

    print("\n==============================")
    print("SOURCES")
    print("==============================\n")

    print(result["sources"])

    print("\n==============================")
    print("GEMINI UTILISÉ")
    print("==============================\n")

    print(result["used_llm"])