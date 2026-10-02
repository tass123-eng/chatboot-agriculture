# Agri Chatbot — Version 0

Version 0 du projet : RAG fonctionnel + base PostgreSQL + diagnostic d'image
avec le modèle YOLOv8 fourni.

## Structure

```
agri_rag_v0/
├── data/
│   ├── documents/        # fiches maladies (source du RAG) — à enrichir au fur et à mesure
│   ├── db/schema.sql      # schéma de la base relationnelle
│   └── chroma_db/         # créé automatiquement par build_index.py
├── rag/
│   ├── build_index.py     # construit l'index vectoriel (à relancer si tu ajoutes des docs)
│   └── query_rag.py       # pipeline Question -> RAG -> LLM -> Réponse
├── init_db.py             # crée les tables et insère les maladies de départ
├── manual_entry.py        # CLI : simule une prédiction YOLOv8 (saisie manuelle)
├── app.py                 # API FastAPI (chatbot + diagnostic manuel)
└── requirements.txt
```

## Installation

```bash
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration PostgreSQL et Gemini

L'application utilise PostgreSQL. Crée une base `agri_rag`, puis configure la
connexion avant l'initialisation :

```powershell
$env:DATABASE_URL = "postgresql://postgres:mot_de_passe@localhost:5432/agri_rag"
$env:GEMINI_API_KEY = "ta_cle_gemini"
python init_db.py
```

`GEMINI_API_KEY` n'est jamais stockée dans le code. Si Gemini est indisponible
ou si la clé est absente, l'API renvoie automatiquement les passages RAG
trouvés au lieu de produire une erreur HTTP 500.

## Ordre de mise en route

```bash
# 1. Crée les tables PostgreSQL + insère les 4 maladies de départ
python init_db.py

# 2. Construit l'index vectoriel à partir des fiches markdown
python rag/build_index.py

# 3. Teste le RAG seul, en ligne de commande
python rag/query_rag.py "Quels sont les symptômes du mildiou de la tomate ?"

# 4. Teste le pipeline complet avec une saisie manuelle
python manual_entry.py

# 5. Lance l'API et l'interface web du chatbot
uvicorn app:app --reload
```

Ouvre ensuite http://127.0.0.1:8000/ dans le navigateur. L'interface appelle
directement `POST /ask`, affiche les sources retrouvées dans ChromaDB et
indique si la réponse vient de Gemini ou du fallback RAG.

Pour vérifier le RAG et les filtres par culture :

```powershell
venv310\Scripts\python.exe -m unittest discover -s tests -v
```

## Endpoints de l'API (étape 5)

- `GET  /` — interface web du chatbot
- `GET  /diseases` — liste des maladies en base
- `POST /images/upload` — upload d'une image JPEG, PNG ou WebP (10 Mo maximum)
- `POST /diagnostic/image` — upload, prédiction YOLOv8 et conseil RAG
- `POST /ask` — `{"question": "...", "crop": "tomate"}` → réponse RAG
- `POST /diagnostic/manual` — `{"crop": "tomate", "predicted_class": "tomato_mildiou", "confidence": 0.91}`
  → enregistre la prédiction (comme le fera YOLOv8) et renvoie un conseil généré par le RAG

Le modèle chargé par défaut est `agri_yolov8-3/weights/best.pt`. Une autre
version peut être utilisée avec la variable `YOLO_WEIGHTS`.

## Pour ajouter une nouvelle maladie/culture

1. Ajoute une fiche markdown dans `data/documents/` (même format que les
   existantes, avec une ligne `class_label: xxx`).
2. Ajoute la ligne correspondante dans `DISEASES` (`init_db.py`) et relance
   `python init_db.py`.
3. Relance `python rag/build_index.py` pour réindexer.

## YOLOv8 et évaluation RAG

Le modèle fourni est un classifieur PlantVillage de 38 classes. Les classes
doivent avoir une fiche correspondante dans `data/documents/` et une ligne dans
PostgreSQL pour obtenir un conseil RAG. Les classes non documentées sont
refusées explicitement par `POST /diagnostic/image`.

Le RAG ignore les passages dont le score de pertinence est inférieur à `0.05`.
Ce seuil peut être ajusté avec `RAG_MIN_RELEVANCE_SCORE`.

Pour mesurer la qualité des sources et la couverture des mots-clés attendus :

```powershell
venv310\Scripts\python.exe evaluation\evaluate_rag.py
```
