# Intégration du modèle d'images

Le pipeline YOLOv8 est maintenant disponible dans `vision/inference.py`.
Dépose les poids entraînés dans `weights/best.pt` ou configure le chemin :

```powershell
$env:YOLO_WEIGHTS = "C:\chemin\vers\best.pt"
```

Le modèle doit être un modèle de classification ou de détection dont les noms
de classes correspondent exactement aux `class_label` de PostgreSQL.

1. YOLOv8 reçoit le chemin d'une image via `POST /diagnostic/image`.
2. Il produit `predicted_class`, `confidence` et la culture détectée.
3. Le service enregistre la prédiction, puis interroge le RAG :

```json
{
  "crop": "pomme de terre",
  "predicted_class": "potato_mildiou",
  "confidence": 0.91,
  "file_path": "data/images/parcelle_01.jpg",
  "model_name": "yolov8"
}
```

L'API vérifie que `predicted_class` appartient bien à la culture, enregistre
la prédiction dans PostgreSQL, interroge le RAG, puis enregistre le conseil.

Les noms de classes du futur modèle doivent donc correspondre exactement aux
valeurs `diseases.class_label` dans PostgreSQL et aux fiches de
`data/documents/`.

Avant un usage réel, vérifie les classes sur un jeu de validation séparé et
mesure la précision, le rappel et la matrice de confusion du modèle. Le
dataset d'images reste dans le pipeline d'entraînement vision ; ses images ne
sont pas indexées dans ChromaDB.