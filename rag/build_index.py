"""
Construit l'index vectoriel à partir des documents markdown dans data/documents/.
Pipeline : lecture -> découpage (chunking) -> embeddings -> stockage ChromaDB.

À relancer chaque fois que tu ajoutes/modifies un document.
    python rag/build_index.py
"""
from pathlib import Path
import shutil

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "data" / "documents"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def extract_crop_and_disease(text: str, filename: str):
    """Récupère des métadonnées simples depuis le contenu du fichier."""
    crop = filename.split("_")[0]
    class_label = None
    for line in text.splitlines():
        if line.strip().startswith("crop:"):
            crop = line.split(":", 1)[1].strip()
        if line.strip().startswith("class_label:"):
            class_label = line.split(":", 1)[1].strip()
    return crop, class_label


def main():
    docs = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        loader = TextLoader(str(path), encoding="utf-8")
        loaded = loader.load()
        crop, class_label = extract_crop_and_disease(loaded[0].page_content, path.stem)
        for d in loaded:
            d.metadata["source"] = path.name
            d.metadata["crop"] = crop
            if class_label:
                d.metadata["class_label"] = class_label
        docs.extend(loaded)

    print(f"📄 {len(docs)} document(s) chargé(s) depuis {DOCS_DIR}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"✂️  {len(chunks)} chunk(s) généré(s)")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="agri_diseases",
    )
    print(f"✅ Index vectoriel créé dans {CHROMA_DIR} ({vectordb._collection.count()} vecteurs)")


if __name__ == "__main__":
    main()
