"""Build the lossless, versioned showcase evidence from collected rasters."""
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deployment/water"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "observations": {}, "files": {}}
    for model in sorted((ROOT / "ml/models/water").glob("*.json")):
        data = json.loads(model.read_text())
        if "observations" not in data:
            continue
        for row in data["observations"]:
            day = row["date"]
            source = ROOT / "data/water" / model.stem / f"{day}.tif"
            with rasterio.open(source) as src:
                array = src.read(1)
            name = f"{model.stem}-{day}.npz"
            np.savez_compressed(OUT / name, water=array)
            metadata = source.with_suffix(".json")
            manifest["observations"][f"{model.stem}/{day}"] = {
                "file": name, "shape": list(array.shape),
                "array_sha256": hashlib.sha256(array.tobytes()).hexdigest(),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "provenance": json.loads(metadata.read_text()),
            }
    for file in sorted(OUT.glob("*.npz")):
        assert file.stat().st_size <= 20 * 1024 * 1024
        manifest["files"][file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    for model in sorted((ROOT / "ml/models/water").glob("*.joblib")):
        manifest["files"][str(model.relative_to(ROOT))] = hashlib.sha256(model.read_bytes()).hexdigest()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packaged {len(manifest['observations'])} observations")

if __name__ == "__main__":
    main()
