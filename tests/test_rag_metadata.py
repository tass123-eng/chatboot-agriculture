import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document

from rag.build_index import extract_crop_and_disease
from rag.query_rag import normalize_crop, retrieve_scored
from vision.inference import _class_label


BASE_DIR = Path(__file__).parent.parent
DOCUMENTS_DIR = BASE_DIR / "data" / "documents"


class RagMetadataTests(unittest.TestCase):
    def test_documents_have_required_metadata(self):
        documents = list(DOCUMENTS_DIR.glob("*.md"))
        self.assertTrue(documents)

        for path in documents:
            if path.name.startswith("_"):
                continue
            text = path.read_text(encoding="utf-8")
            crop, class_label = extract_crop_and_disease(text, path.stem)
            self.assertTrue(crop, path.name)
            self.assertTrue(class_label, path.name)

    def test_crop_aliases_are_normalized(self):
        self.assertEqual(normalize_crop("Pomme_terre"), "pomme de terre")
        self.assertEqual(normalize_crop(" pommes de terre "), "pomme de terre")
        self.assertEqual(normalize_crop("Tomate"), "tomate")

    def test_yolo_labels_are_normalized_to_database_labels(self):
        self.assertEqual(_class_label("Tomato___Late_blight"), "tomato_mildiou")
        self.assertEqual(
            _class_label("Cucumber___Powdery_mildew"),
            "cucumber_powdery_mildew",
        )

    def test_retrieve_scored_discards_weak_matches(self):
        class FakeVectorDb:
            def similarity_search_with_relevance_scores(self, question, **kwargs):
                self.question = question
                self.kwargs = kwargs
                return [
                    (Document(page_content="fort"), 0.8),
                    (Document(page_content="faible"), 0.01),
                ]

        fake_db = FakeVectorDb()
        with patch("rag.query_rag._vectordb", fake_db):
            results = retrieve_scored("symptomes", crop="Tomate")

        self.assertEqual([doc.page_content for doc, _score in results], ["fort"])
        self.assertEqual(fake_db.kwargs["filter"], {"crop": "tomate"})


if __name__ == "__main__":
    unittest.main()