"""Download the MediaPipe hand landmarker model used by the AR trainer."""

from pathlib import Path
from urllib.request import urlretrieve


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def download_model():
    """Download the model into ``models/hand_landmarker.task``."""
    project_root = Path(__file__).resolve().parent
    model_dir = project_root / "models"
    model_path = model_dir / "hand_landmarker.task"

    model_dir.mkdir(exist_ok=True)

    print("Downloading MediaPipe hand landmarker model...")
    print(f"URL: {MODEL_URL}")
    print(f"Destination: {model_path}")

    urlretrieve(MODEL_URL, model_path)

    size_mb = model_path.stat().st_size / 1024 / 1024
    print(f"[OK] Model downloaded successfully ({size_mb:.2f} MB)")
    return model_path


if __name__ == "__main__":
    download_model()
