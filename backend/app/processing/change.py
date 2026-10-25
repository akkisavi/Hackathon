"""Local, deterministic change measurements. No database or model weights."""
from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from skimage.metrics import structural_similarity

MAX_IMAGE_BYTES = 5_000_000


def decode_image(data: bytes) -> np.ndarray:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Each image must be a PNG or JPEG under 5 MB.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG"} or image.size != (512, 512):
                raise ValueError("Use aligned 512×512 PNG or JPEG images.")
            return np.array(image.convert("RGB"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Cannot decode image. Use a valid PNG or JPEG.") from exc


def encode_png(image: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def image_url(image: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(encode_png(image)).decode()


def analyze_pair(before: np.ndarray, after: np.ndarray, threshold: float = 0.2,
                 pixel_size_m: float | None = None) -> dict:
    if before.shape != (512, 512, 3) or after.shape != before.shape:
        raise ValueError("Use aligned 512×512 RGB images.")
    if not np.isfinite(threshold) or not 0.05 <= threshold <= 0.6:
        raise ValueError("Threshold must be between 0.05 and 0.60.")
    if pixel_size_m is not None and (not np.isfinite(pixel_size_m) or pixel_size_m <= 0):
        raise ValueError("Pixel scale must be positive and finite.")

    a, b = [cv2.GaussianBlur(image, (3, 3), 0) for image in (before, after)]
    _, similarity = structural_similarity(a, b, channel_axis=2, data_range=255, full=True)
    delta = np.clip(1 - similarity.mean(axis=2), 0, 1)
    raw = cv2.morphologyEx((delta > threshold).astype(np.uint8), cv2.MORPH_OPEN,
                         np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(raw)
    mask = np.zeros_like(raw)
    regions = []
    for label in range(1, count):
        x, y, w, h, pixels = map(int, stats[label])
        if pixels < 80:
            continue
        component = (labels == label).astype(np.uint8)
        mask[component > 0] = 1
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polygon = cv2.approxPolyDP(max(contours, key=cv2.contourArea), 1.5, True)
        regions.append({"id": f"R{len(regions) + 1}", "bbox_xywh": [x, y, w, h],
                        "polygon_xy": polygon.reshape(-1, 2).tolist(), "pixels": pixels})

    overlay = after.copy()
    selection = mask.astype(bool)
    overlay[selection] = (0.6 * overlay[selection] + 0.4 * np.array([230, 93, 49])).astype(np.uint8)
    for region in regions:
        polygon = np.array(region["polygon_xy"], np.int32)
        cv2.polylines(overlay, [polygon], True, (255, 216, 125), 2)
        x, y, _, _ = region["bbox_xywh"]
        cv2.putText(overlay, region["id"], (x, max(16, y)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 2)
    changed = int(mask.sum())
    return {"width": 512, "height": 512, "threshold": threshold, "min_region_pixels": 80,
            "changed_pixels": changed, "changed_fraction": changed / mask.size,
            "pixel_size_m": pixel_size_m,
            "area_m2": changed * pixel_size_m ** 2 if pixel_size_m is not None else None,
            "regions": regions, "overlay": image_url(overlay), "mask": image_url(mask * 255)}
