import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio


def scale_to_uint8(arr, p_low=2, p_high=98):
    arr = arr.astype(np.float32)
    if not np.isfinite(arr).any():
        return np.zeros(arr.shape, dtype=np.uint8)
    vmin, vmax = np.percentile(arr[np.isfinite(arr)], [p_low, p_high])
    if vmax <= vmin:
        vmax = vmin + 1.0
    out = (arr - vmin) / (vmax - vmin)
    out = np.clip(out, 0, 1)
    return (out * 255).astype(np.uint8)


def save_rgb(path, r, g, b):
    rgb = np.stack([r, g, b], axis=2)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(path)


def save_gray(path, band):
    img = Image.fromarray(band, mode="L")
    img.save(path)


def export_tif(tif_path, out_dir):
    with rasterio.open(tif_path) as ds:
        data = ds.read()
        descriptions = ds.descriptions

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = tif_path.stem
    count = data.shape[0]

    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i - 1

    if count >= 3 and {"B2", "B3", "B4"}.issubset(mapping):
        b = scale_to_uint8(data[mapping["B2"]])
        g = scale_to_uint8(data[mapping["B3"]])
        r = scale_to_uint8(data[mapping["B4"]])
        save_rgb(out_dir / f"{stem}_rgb.png", r, g, b)
    elif count >= 3:
        r = scale_to_uint8(data[0])
        g = scale_to_uint8(data[1])
        b = scale_to_uint8(data[2])
        save_rgb(out_dir / f"{stem}_rgb.png", r, g, b)

    if count == 1:
        band = scale_to_uint8(data[0])
        save_gray(out_dir / f"{stem}.png", band)
    elif count == 2:
        name1 = descriptions[0] if descriptions[0] else "band1"
        name2 = descriptions[1] if descriptions[1] else "band2"
        save_gray(out_dir / f"{stem}_{name1.lower()}.png", scale_to_uint8(data[0]))
        save_gray(out_dir / f"{stem}_{name2.lower()}.png", scale_to_uint8(data[1]))
    elif count > 3:
        for i in range(count):
            name = descriptions[i] if descriptions[i] else f"band{i+1}"
            save_gray(out_dir / f"{stem}_{name.lower()}.png", scale_to_uint8(data[i]))


def main():
    parser = argparse.ArgumentParser(description="Export GeoTIFFs to PNG quicklooks.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--output", default="outputs/png", help="PNG output folder")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_root = root / args.output

    tif_paths = []
    for folder in ["photos", "outputs"]:
        path = root / folder
        if path.exists():
            tif_paths.extend(path.rglob("*.tif"))

    if not tif_paths:
        print("No .tif files found.")
        return

    for tif_path in tif_paths:
        rel = tif_path.parent.relative_to(root)
        out_dir = out_root / rel
        export_tif(tif_path, out_dir)
        print("Exported", tif_path.name, "->", out_dir)


if __name__ == "__main__":
    main()
