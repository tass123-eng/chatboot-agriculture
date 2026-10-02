"""YOLOv8 inference adapter used by the image diagnostic endpoint."""
import os
import re
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent
DEFAULT_WEIGHTS = BASE_DIR / "agri_yolov8-3" / "weights" / "best.pt"


def _class_label(name: str) -> str:
    normalized = re.sub(r"_+", "_", name.strip().lower().replace("-", " "))
    normalized = re.sub(r"[^a-z0-9_()]+", "_", normalized)
    normalized = normalized.strip("_")
    aliases = {
        "tomato_late_blight": "tomato_mildiou",
        "potato_late_blight": "potato_mildiou",
    }
    return aliases.get(normalized, normalized)


@lru_cache(maxsize=4)
def _load_model(weights_path: str):
    from ultralytics import YOLO

    return YOLO(weights_path)


def predict_image(image_path: str | Path) -> dict:
    """Run YOLOv8 on one image and return the best class prediction.

    The ultralytics import is lazy so text-only chatbot usage does not require
    loading the vision stack. The model must expose class names matching the
    ``diseases.class_label`` values stored in PostgreSQL.
    """
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Le paquet ultralytics n'est pas installe. "
            "Installe les dependances vision avant d'utiliser le diagnostic image."
        ) from exc

    weights_path = Path(os.getenv("YOLO_WEIGHTS", str(DEFAULT_WEIGHTS)))
    if not weights_path.is_absolute():
        weights_path = BASE_DIR / weights_path
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Poids YOLO introuvables : {weights_path}. "
            "Definis YOLO_WEIGHTS ou ajoute weights/best.pt."
        )

    model = _load_model(str(weights_path))
    results = model.predict(source=str(image_path), conf=0.25, verbose=False)
    if not results:
        raise ValueError("YOLO n'a produit aucune prediction.")

    result = results[0]
    names = result.names or model.names
    prediction = None

    if result.probs is not None:
        class_id = int(result.probs.top1)
        confidence = float(result.probs.top1conf)
        prediction = class_id, confidence
    elif result.boxes is not None and len(result.boxes) > 0:
        confidence_tensor = result.boxes.conf
        best_index = int(confidence_tensor.argmax().item())
        class_id = int(result.boxes.cls[best_index].item())
        confidence = float(confidence_tensor[best_index].item())
        prediction = class_id, confidence

    if prediction is None:
        raise ValueError("YOLO n'a trouve aucune classe exploitable.")

    class_id, confidence = prediction
    class_name = names[class_id] if isinstance(names, dict) else names[class_id]
    return {
        "predicted_class": _class_label(str(class_name)),
        "confidence": confidence,
        "model_name": "yolov8",
        "weights": str(weights_path),
    }
