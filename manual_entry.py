"""
V0 - Saisie manuelle d'un diagnostic (en attendant l'intégration de YOLOv8).

Simule exactement ce que fera le modèle plus tard :
    Photo -> [YOLOv8] -> predicted_class + confidence -> RAG -> Conseil

Ici, tu remplaces juste le bloc [YOLOv8] par une saisie au clavier.
Le reste du pipeline (DB + RAG + conseil) est identique à la version finale,
donc tu ne perdras aucun code quand tu brancheras le vrai modèle : il te
suffira de remplacer `ask_manual_prediction()` par `run_yolo(image_path)`.

Usage :
    python manual_entry.py
"""
from datetime import datetime

from db import get_conn
from rag.query_rag import answer_question


def get_diseases(conn):
    cur = conn.cursor()
    cur.execute(
        """SELECT d.class_label, d.name, c.name AS crop
           FROM diseases d JOIN crops c ON d.crop_id = c.id"""
    )
    return [
        (row["class_label"], row["name"], row["crop"])
        for row in cur.fetchall()
    ]


def ask_manual_prediction(conn):
    """Remplace ici la vraie inférence YOLOv8 (v0 = saisie clavier)."""
    diseases = get_diseases(conn)
    print("\nMaladies disponibles dans la base :")
    for i, (class_label, name, crop) in enumerate(diseases, 1):
        print(f"  {i}. {name} ({crop}) -> class_label = {class_label}")

    choice = input("\nChoisis le numéro de la maladie détectée (simulation) : ").strip()
    idx = int(choice) - 1
    class_label, disease_name, crop = diseases[idx]

    confidence = input("Confiance simulée (ex: 0.91) [défaut 0.90] : ").strip()
    confidence = float(confidence) if confidence else 0.90

    file_path = input("Chemin de l'image (laisser vide si pas encore de photo) : ").strip()

    return crop, class_label, disease_name, confidence, file_path


def save_prediction(conn, crop: str, class_label: str, confidence: float, file_path: str):
    cur = conn.cursor()

    cur.execute("SELECT id FROM crops WHERE name = %s", (crop,))
    row = cur.fetchone()
    crop_id = row["id"] if row else None

    cur.execute(
        "INSERT INTO images (crop_id, file_path, uploaded_at) VALUES (%s,%s,%s) RETURNING image_id",
        (crop_id, file_path or None, datetime.now()),
    )
    image_id = cur.fetchone()["image_id"]

    cur.execute(
        """INSERT INTO predictions
           (image_id, model_name, predicted_class, confidence, prediction_date)
            VALUES (%s,%s,%s,%s,%s) RETURNING prediction_id""",
        (image_id, "manual_entry", class_label, confidence, datetime.now()),
    )
    prediction_id = cur.fetchone()["prediction_id"]

    conn.commit()
    return prediction_id


def save_advice(conn, prediction_id: int, question: str, answer: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO advices (prediction_id, question, answer) VALUES (%s,%s,%s)",
        (prediction_id, question, answer),
    )
    conn.commit()


def main():
    with get_conn() as conn:
        crop, class_label, disease_name, confidence, file_path = ask_manual_prediction(conn)
        prediction_id = save_prediction(conn, crop, class_label, confidence, file_path)
        print(f"\n💾 Prédiction enregistrée (id={prediction_id}) : "
              f"{disease_name} sur {crop} (confiance {confidence:.2f})")

        question = f"Quels sont les symptômes, causes et traitements du {disease_name.lower()} sur {crop} ?"
        print(f"\n🔎 Interrogation du RAG : {question}")
        result = answer_question(question, crop=crop)
        save_advice(conn, prediction_id, question, result["answer"])

        print("\n🌱 Conseil généré pour l'agriculteur :\n")
        print(result["answer"])

if __name__ == "__main__":
    main()
