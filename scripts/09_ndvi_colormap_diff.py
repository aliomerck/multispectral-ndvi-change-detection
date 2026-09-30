import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image

from common import ensure_dir, list_tifs, read_tif, write_csv, write_tif


def parse_city_year(name):
    base = name
    for suffix in ["_features"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", base)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def ndvi_colormap(ndvi):
    x = np.clip((ndvi + 1.0) / 2.0, 0, 1)
    # Red (-1) -> Yellow (0) -> Green (+1)
    r = np.where(x < 0.5, 1.0, 1.0 - (x - 0.5) * 2.0)
    g = np.where(x < 0.5, x * 2.0, 1.0)
    b = np.zeros_like(x)
    rgb = np.stack([r, g, b], axis=2)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def diff_colormap(diff, vmin=-0.5, vmax=0.5):
    x = (diff - vmin) / (vmax - vmin)
    x = np.clip(x, 0, 1)
    r = np.where(x > 0.5, (x - 0.5) * 2.0, 0.0)
    b = np.where(x < 0.5, (0.5 - x) * 2.0, 0.0)
    g = 1.0 - (np.abs(x - 0.5) * 2.0)
    rgb = np.stack([r, g, b], axis=2)
    return (rgb * 255).astype(np.uint8)


def save_png(path, rgb):
    Image.fromarray(rgb, mode="RGB").save(path)


def main():
    parser = argparse.ArgumentParser(description="NDVI colormap and year-to-year diff.")
    parser.add_argument("--features", default="outputs/04_features", help="Features folder")
    parser.add_argument("--out-ndvi", default="outputs/07_ndvi_png", help="NDVI PNG folder")
    parser.add_argument("--out-diff", default="outputs/08_ndvi_diff", help="NDVI diff outputs")
    args = parser.parse_args()

    features = list_tifs(args.features)
    if not features:
        print("No feature .tif files found.")
        return

    out_ndvi = Path(args.out_ndvi)
    out_diff = Path(args.out_diff)
    ensure_dir(out_ndvi)
    ensure_dir(out_diff)

    by_city_year = {}
    for path in features:
        city, year = parse_city_year(path.stem)
        if city and year:
            by_city_year[(city, year)] = path

    stats = []
    for (city, year), feat_path in by_city_year.items():
        data, profile, _ = read_tif(feat_path)
        ndvi = data[0].astype(np.float32)
        rgb = ndvi_colormap(ndvi)
        out_path = out_ndvi / f"{city}_{year}_ndvi.png"
        save_png(out_path, rgb)
        stats.append([city, year, f"{float(np.nanmean(ndvi)):.4f}"])

    for city in set(c for c, _ in by_city_year.keys()):
        if (city, 2016) in by_city_year and (city, 2024) in by_city_year:
            ndvi16, profile, _ = read_tif(by_city_year[(city, 2016)])
            ndvi24, _, _ = read_tif(by_city_year[(city, 2024)])
            diff = (ndvi24[0].astype(np.float32) - ndvi16[0].astype(np.float32))
            diff_tif = out_diff / f"{city}_ndvi_diff_2024_2016.tif"
            write_tif(diff_tif, diff[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI_DIFF"])
            diff_png = out_diff / f"{city}_ndvi_diff_2024_2016.png"
            save_png(diff_png, diff_colormap(diff))
            stats.append([city, "2024-2016", f"{float(np.nanmean(diff)):.4f}"])

    write_csv(out_diff / "ndvi_stats.csv", stats, ["city", "year_or_diff", "mean_ndvi"])
    print("Wrote NDVI PNGs to", out_ndvi)
    print("Wrote NDVI diffs to", out_diff)


if __name__ == "__main__":
    main()
