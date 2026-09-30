import argparse
import re
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_tif


def parse_city_year(name):
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", name)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def match_histogram_quantiles(source, reference, quantiles=1024):
    src = source.astype(np.float32)
    ref = reference.astype(np.float32)
    mask_src = np.isfinite(src)
    mask_ref = np.isfinite(ref)
    if not mask_src.any() or not mask_ref.any():
        return src

    qs = np.linspace(0.0, 1.0, quantiles)
    src_q = np.quantile(src[mask_src], qs)
    ref_q = np.quantile(ref[mask_ref], qs)

    # Ensure monotonicity for interpolation
    src_q = np.maximum.accumulate(src_q)
    ref_q = np.maximum.accumulate(ref_q)

    flat = src.ravel()
    matched = np.interp(flat, src_q, ref_q).reshape(src.shape)
    return matched.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Radiometric normalization via histogram matching.")
    parser.add_argument("--input", default="outputs/01_dos", help="Input folder (DOS outputs)")
    parser.add_argument("--output", default="outputs/01_dos_norm", help="Output folder")
    parser.add_argument("--quantiles", type=int, default=1024, help="Quantiles for matching")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    by_city_year = {}
    for path in files:
        city, year = parse_city_year(path.stem)
        if city and year:
            by_city_year[(city, year)] = path

    for (city, year), src_path in by_city_year.items():
        if year != 2024:
            continue
        ref_key = (city, 2016)
        if ref_key not in by_city_year:
            continue

        ref_path = by_city_year[ref_key]
        src_data, profile, descriptions = read_tif(src_path)
        ref_data, _, _ = read_tif(ref_path)

        out = np.empty_like(src_data, dtype=np.float32)
        for i in range(src_data.shape[0]):
            out[i] = match_histogram_quantiles(
                src_data[i], ref_data[i], quantiles=args.quantiles
            )

        out_path = Path(args.output) / f"{src_path.stem}_norm.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
