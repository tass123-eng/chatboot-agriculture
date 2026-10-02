-- =========================================================
-- Version 0 : schéma minimal (users/farms retirés pour l'instant,
-- on se concentre sur cultures -> maladies -> images -> predictions)
-- =========================================================

CREATE TABLE IF NOT EXISTS crops (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,      -- ex: "tomate"
    scientific_name TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS diseases (
    id          SERIAL PRIMARY KEY,
    crop_id     INTEGER NOT NULL,
    name        TEXT NOT NULL,                 -- ex: "Mildiou"
    class_label TEXT NOT NULL UNIQUE,          -- ex: "tomato_mildiou" (= future sortie YOLOv8)
    symptoms    TEXT,
    causes      TEXT,
    prevention  TEXT,
    treatment   TEXT,
    severity    TEXT,
    doc_source  TEXT,                          -- nom du fichier markdown utilisé par le RAG
    FOREIGN KEY (crop_id) REFERENCES crops(id)
);

CREATE TABLE IF NOT EXISTS images (
    image_id    SERIAL PRIMARY KEY,
    crop_id     INTEGER,
    file_path   TEXT,                          -- peut être vide en v0 (saisie manuelle)
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crop_id) REFERENCES crops(id)
);

-- Table demandée : exactement ta structure
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id   SERIAL PRIMARY KEY,
    image_id        INTEGER,
    model_name      TEXT,                      -- "manual_entry" en v0, "yolov8" plus tard
    predicted_class TEXT,                      -- doit correspondre à diseases.class_label
    confidence      REAL,
    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(image_id)
);

-- Historique des conseils générés par le RAG pour chaque prédiction
CREATE TABLE IF NOT EXISTS advices (
    id              SERIAL PRIMARY KEY,
    prediction_id   INTEGER,
    question        TEXT,
    answer          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);
