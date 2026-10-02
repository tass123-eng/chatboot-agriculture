"""
API FastAPI - Version 0

Lancement :
    uvicorn app:app --reload

Endpoints :
    GET  /diseases                -> liste des maladies connues
    POST /ask                     -> question libre au chatbot (RAG)
    POST /images/upload           -> stocke une image
    POST /diagnostic/image        -> YOLOv8 + conseil RAG
    POST /diagnostic/manual       -> enregistre une "prédiction" manuelle
                                      (en attendant YOLOv8) + génère un conseil
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import psycopg

from db import get_conn
from rag.query_rag import answer_question
from vision.inference import predict_image

app = FastAPI(title="Agri Chatbot API", version="0.1")

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.exception_handler(psycopg.Error)
async def postgres_error_handler(_request, _exc):
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Base PostgreSQL indisponible. Demarrez PostgreSQL et verifiez "
                "DATABASE_URL avant d'analyser une image."
            )
        },
    )


@app.get("/", include_in_schema=False)
def chat_interface():
    return FileResponse(BASE_DIR / "templates" / "index.html")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    crop: Optional[str] = Field(default=None, max_length=100)


class ManualDiagnosticRequest(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    predicted_class: str = Field(..., min_length=1, max_length=100)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    file_path: Optional[str] = Field(default=None, max_length=500)
    model_name: str = Field(default="manual_entry", min_length=1, max_length=100)


@app.get("/diseases")
def list_diseases():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT d.id, d.name, d.class_label, c.name AS crop,
                      d.symptoms, d.causes, d.prevention, d.treatment, d.severity
               FROM diseases d JOIN crops c ON d.crop_id = c.id"""
        ).fetchall()
    return rows


async def _store_upload(file: UploadFile) -> dict:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Format accepté : JPEG, PNG ou WebP.",
        )

    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="L'image ne doit pas dépasser 10 Mo.",
        )

    stored_name = f"{uuid4().hex}{ALLOWED_IMAGE_TYPES[file.content_type]}"
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)

    return {
        "filename": file.filename or stored_name,
        "file_path": str(destination.relative_to(BASE_DIR)),
        "url": f"/uploads/{stored_name}",
    }


@app.post("/images/upload")
async def upload_image(file: UploadFile = File(...)):
    return await _store_upload(file)


@app.post("/diagnostic/image")
async def image_diagnostic(file: UploadFile = File(...)):
    try:
        upload = await _store_upload(file)
        prediction = predict_image(BASE_DIR / upload["file_path"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with get_conn() as conn:
        disease_row = conn.execute(
            """SELECT d.name, c.id AS crop_id, c.name AS crop
               FROM diseases d JOIN crops c ON d.crop_id = c.id
               WHERE d.class_label = %s""",
            (prediction["predicted_class"],),
        ).fetchone()
        if not disease_row:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Classe YOLO inconnue dans la base : "
                    f"{prediction['predicted_class']}"
                ),
            )

        image_id = conn.execute(
            """INSERT INTO images (crop_id, file_path, uploaded_at)
               VALUES (%s,%s,%s) RETURNING image_id""",
            (disease_row["crop_id"], upload["file_path"], datetime.now()),
        ).fetchone()["image_id"]
        prediction_id = conn.execute(
            """INSERT INTO predictions
               (image_id, model_name, predicted_class, confidence, prediction_date)
               VALUES (%s,%s,%s,%s,%s) RETURNING prediction_id""",
            (
                image_id,
                prediction["model_name"],
                prediction["predicted_class"],
                prediction["confidence"],
                datetime.now(),
            ),
        ).fetchone()["prediction_id"]
        conn.commit()

    question = (
        f"Quels sont les symptômes, causes et traitements du "
        f"{disease_row['name'].lower()} sur {disease_row['crop']} ?"
    )
    result = answer_question(question, crop=disease_row["crop"])

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO advices (prediction_id, question, answer) VALUES (%s,%s,%s)",
            (prediction_id, question, result["answer"]),
        )
        conn.commit()

    return {
        "prediction_id": prediction_id,
        "disease": disease_row["name"],
        "crop": disease_row["crop"],
        "predicted_class": prediction["predicted_class"],
        "confidence": prediction["confidence"],
        "model_name": prediction["model_name"],
        "image_url": upload["url"],
        "advice": result["answer"],
        "sources": result["sources"],
        "used_llm": result["used_llm"],
    }


@app.post("/ask")
def ask(req: AskRequest):
    result = answer_question(req.question, crop=req.crop)
    return result


@app.post("/diagnostic/manual")
def manual_diagnostic(req: ManualDiagnosticRequest):
    with get_conn() as conn:
        crop_row = conn.execute(
            "SELECT id FROM crops WHERE name = %s", (req.crop,)
        ).fetchone()
        if not crop_row:
            raise HTTPException(status_code=404, detail=f"Culture inconnue : {req.crop}")

        disease_row = conn.execute(
            """SELECT d.name
               FROM diseases d JOIN crops c ON d.crop_id = c.id
               WHERE d.class_label = %s AND c.name = %s""",
            (req.predicted_class, req.crop),
        ).fetchone()
        if not disease_row:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"class_label inconnue pour la culture {req.crop} : "
                    f"{req.predicted_class}"
                ),
            )
        disease_name = disease_row["name"]

        image_id = conn.execute(
            """INSERT INTO images (crop_id, file_path, uploaded_at)
               VALUES (%s,%s,%s) RETURNING image_id""",
            (crop_row["id"], req.file_path, datetime.now()),
        ).fetchone()["image_id"]

        prediction_id = conn.execute(
            """INSERT INTO predictions
               (image_id, model_name, predicted_class, confidence, prediction_date)
               VALUES (%s,%s,%s,%s,%s) RETURNING prediction_id""",
            (image_id, req.model_name, req.predicted_class, req.confidence, datetime.now()),
        ).fetchone()["prediction_id"]
        conn.commit()

    question = (
        f"Quels sont les symptômes, causes et traitements du "
        f"{disease_name.lower()} sur {req.crop} ?"
    )
    result = answer_question(question, crop=req.crop)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO advices (prediction_id, question, answer) VALUES (%s,%s,%s)",
            (prediction_id, question, result["answer"]),
        )
        conn.commit()

    return {
        "prediction_id": prediction_id,
        "disease": disease_name,
        "model_name": req.model_name,
        "confidence": req.confidence,
        "advice": result["answer"],
        "sources": result["sources"],
    }
