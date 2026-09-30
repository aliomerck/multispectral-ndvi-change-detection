import argparse
import re
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_csv, write_tif


def parse_city_year(name):
    base = name
    for suffix in ["_dos", "_homo", "_denoise", "_features", "_segments"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", base)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def compute_ndwi(green, nir):
    green = green.astype(np.float32)
    nir = nir.astype(np.float32)
    denom = green + nir
    return (green - nir) / (denom + 1e-6)


def band_indices_from_descriptions(descriptions):
    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i
    return mapping


def load_bands(denoised_path):
    data, _, descriptions = read_tif(denoised_path)
    mapping = band_indices_from_descriptions(descriptions)
    try:
        b_i = mapping["B2"] - 1
        g_i = mapping["B3"] - 1
        r_i = mapping["B4"] - 1
        n_i = mapping["B8"] - 1
    except KeyError:
        b_i, g_i, r_i, n_i = 0, 1, 2, 3
    blue = data[b_i].astype(np.float32)
    green = data[g_i].astype(np.float32)
    red = data[r_i].astype(np.float32)
    nir = data[n_i].astype(np.float32)
    return blue, green, red, nir


def main():
    parser = argparse.ArgumentParser(description="Temporal vegetation change analysis.")
    parser.add_argument("--features", default="outputs/04_features", help="Features folder")
    parser.add_argument("--features-2016", default=None, help="Override 2016 features folder")
    parser.add_argument("--features-2024", default=None, help="Override 2024 features folder")
    parser.add_argument(
        "--bands",
        default="outputs/03_denoised",
        help="Folder containing band data for NDWI/ratios",
    )
    parser.add_argument("--output", default="outputs/06_temporal", help="Output folder")
    parser.add_argument(
        "--ndvi-threshold",
        type=float,
        default=0.3,
        help="NDVI threshold for vegetation mask",
    )
    parser.add_argument(
        "--ndvi-max",
        type=float,
        default=None,
        help="Optional max NDVI for vegetation mask",
    )
    parser.add_argument(
        "--green-red-ratio",
        type=float,
        default=1.05,
        help="Green/Red ratio threshold for vegetation mask",
    )
    parser.add_argument(
        "--nir-red-ratio",
        type=float,
        default=1.2,
        help="NIR/Red ratio threshold for vegetation mask",
    )
    parser.add_argument(
        "--ndwi-threshold",
        type=float,
        default=0.0,
        help="NDWI threshold for water mask (water if NDWI > threshold)",
    )
    parser.add_argument(
        "--land-intersection",
        action="store_true",
        help="Use land mask intersection for both years",
    )
    args = parser.parse_args()

    ensure_dir(args.output)
    feat_files = list_tifs(args.features)
    if not feat_files and not (args.features_2016 or args.features_2024):
        print("Missing feature files.")
        return

    feat_map = {}
    for path in feat_files:
        city, year = parse_city_year(path.stem)
        if city and year:
            feat_map[(city, year)] = path

    if args.features_2016:
        for path in list_tifs(args.features_2016):
            city, year = parse_city_year(path.stem)
            if city and year == 2016:
                feat_map[(city, year)] = path

    if args.features_2024:
        for path in list_tifs(args.features_2024):
            city, year = parse_city_year(path.stem)
            if city and year == 2024:
                feat_map[(city, year)] = path

    rows = []
    for (city, year), feat_path in feat_map.items():
        other_year = 2024 if year == 2016 else 2016
        key_other = (city, other_year)
        if key_other not in feat_map:
            continue

        feat1, profile, _ = read_tif(feat_path)
        feat2, _, _ = read_tif(feat_map[key_other])

        ndvi1 = feat1[0]
        ndvi2 = feat2[0]

        base1 = feat_path.stem.replace("_features", "")
        base2 = feat_map[key_other].stem.replace("_features", "")
        bands1 = Path(args.bands) / f"{base1}.tif"
        bands2 = Path(args.bands) / f"{base2}.tif"
        if bands1.exists() and bands2.exists():
            b1, g1, r1, n1 = load_bands(bands1)
            b2, g2, r2, n2 = load_bands(bands2)
            ndwi1 = compute_ndwi(g1, n1)
            ndwi2 = compute_ndwi(g2, n2)
            water1 = ndwi1 > args.ndwi_threshold
            water2 = ndwi2 > args.ndwi_threshold
        else:
            water1 = np.zeros(ndvi1.shape, dtype=bool)
            water2 = np.zeros(ndvi2.shape, dtype=bool)
            b1 = g1 = r1 = n1 = None
            b2 = g2 = r2 = n2 = None

        land1 = ~water1
        land2 = ~water2
        if args.land_intersection:
            land1 = land1 & land2
            land2 = land1

        veg1 = (ndvi1 > args.ndvi_threshold) & land1
        veg2 = (ndvi2 > args.ndvi_threshold) & land2
        if args.ndvi_max is not None:
            veg1 &= ndvi1 <= args.ndvi_max
            veg2 &= ndvi2 <= args.ndvi_max
        if r1 is not None:
            gr1 = g1 / (r1 + 1e-6)
            nr1 = n1 / (r1 + 1e-6)
            veg1 &= (gr1 > args.green_red_ratio) & (nr1 > args.nir_red_ratio)
        if r2 is not None:
            gr2 = g2 / (r2 + 1e-6)
            nr2 = n2 / (r2 + 1e-6)
            veg2 &= (gr2 > args.green_red_ratio) & (nr2 > args.nir_red_ratio)

        total1 = land1.sum()
        total2 = land2.sum()
        pct1 = float(veg1.sum()) / max(total1, 1) * 100.0
        pct2 = float(veg2.sum()) / max(total2, 1) * 100.0
        delta = pct2 - pct1

        rows.append([city, year, other_year, f"{pct1:.2f}", f"{pct2:.2f}", f"{delta:.2f}"])

        diff = np.zeros(veg1.shape, dtype=np.int8)
        diff[(veg1) & (~veg2)] = -1
        diff[(~veg1) & (veg2)] = 1
        diff[water1 & water2] = 0
        diff_path = Path(args.output) / f"{city}_{year}_{other_year}_veg_diff.tif"
        write_tif(diff_path, diff[np.newaxis, :, :], profile, dtype="int8", descriptions=["VEG_DIFF"])
        print("Wrote", diff_path)

    out_csv = Path(args.output) / "summary.csv"
    write_csv(
        out_csv,
        rows,
        ["city", "year_a", "year_b", "veg_pct_a", "veg_pct_b", "delta_pct"],
    )
    print("Wrote", out_csv)


if __name__ == "__main__":
    main()
