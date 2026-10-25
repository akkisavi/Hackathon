"""Read and verify the repository-owned water evidence bundle."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "deployment/water"

@lru_cache(maxsize=1)
def manifest():
    return json.loads((BUNDLE / "manifest.json").read_text())

def read_array(site, day):
    record = manifest()["observations"].get(f"{site}/{day}")
    if record is None:
        raise FileNotFoundError("Observation absent from deployment bundle")
    with np.load(BUNDLE / record["file"], allow_pickle=False) as archive:
        return archive["water"]

def verify_bundle():
    from app.api.v1.water import SITES, bundle, load_model, MODEL_DIR
    data = manifest()
    for name, digest in data["files"].items():
        path = ROOT / name if name.startswith("ml/") else BUNDLE / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Evidence checksum mismatch: {name}")
    for site in SITES:
        model = bundle(site["id"])
        artifact = load_model(site["id"], (MODEL_DIR / f"{site['id']}.joblib").stat().st_mtime_ns)
        if artifact["model_id"] != model["model_id"]:
            raise RuntimeError("Model identity mismatch")
        for row in model["observations"]:
            key = f"{site['id']}/{row['date']}"
            record = data["observations"][key]
            array = read_array(site["id"], row["date"])
            if list(array.shape) != record["shape"] or hashlib.sha256(array.tobytes()).hexdigest() != record["array_sha256"]:
                raise RuntimeError(f"Invalid observation: {key}")
