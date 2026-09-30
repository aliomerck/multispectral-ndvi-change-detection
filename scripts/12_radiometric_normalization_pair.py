import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, read_tif, write_tif


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

    src_q = np.maximum.accumulate(src_q)
    ref_q = np.maximum.accumulate(ref_q)

    flat = src.ravel()
    matched = np.interp(flat, src_q, ref_q).reshape(src.shape)
    return matched.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Normalize 2016 and 2024 to a common histogram.")
    parser.add_argument("--ref-2016", required=True, help="2016 DOS TIFF")
    parser.add_argument("--ref-2024", required=True, help="2024 DOS TIFF")
    parser.add_argument("--output", default="outputs/01_dos_norm_pair", help="Output folder")
    parser.add_argument("--quantiles", type=int, default=1024, help="Quantiles for matching")
    args = parser.parse_args()

    ensure_dir(args.output)
    p16 = Path(args.ref_2016)
    p24 = Path(args.ref_2024)

    d16, profile, desc = read_tif(p16)
    d24, _, _ = read_tif(p24)

    out16 = np.empty_like(d16, dtype=np.float32)
    out24 = np.empty_like(d24, dtype=np.float32)

    for i in range(d16.shape[0]):
        band16 = d16[i]
        band24 = d24[i]
        ref_q = (band16.astype(np.float32) + band24.astype(np.float32)) / 2.0
        out16[i] = match_histogram_quantiles(band16, ref_q, quantiles=args.quantiles)
        out24[i] = match_histogram_quantiles(band24, ref_q, quantiles=args.quantiles)

    out16_path = Path(args.output) / f"{p16.stem}_normpair.tif"
    out24_path = Path(args.output) / f"{p24.stem}_normpair.tif"
    write_tif(out16_path, out16, profile, dtype="float32", descriptions=desc)
    write_tif(out24_path, out24, profile, dtype="float32", descriptions=desc)
    print("Wrote", out16_path)
    print("Wrote", out24_path)


if __name__ == "__main__":
    main()
