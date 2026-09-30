import argparse
from pathlib import Path

import numpy as np

from common import adaptive_noise_reduction, ensure_dir, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply adaptive local noise reduction.")
    parser.add_argument("--input", default="outputs/02_homomorphic", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/03_denoised", help="Output folder")
    parser.add_argument("--window", type=int, default=7, help="Window size (odd)")
    parser.add_argument(
        "--noise-percentile",
        type=float,
        default=10.0,
        help="Percentile for estimating noise variance",
    )
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        out = []
        for i in range(data.shape[0]):
            out.append(
                adaptive_noise_reduction(
                    data[i], window=args.window, noise_percentile=args.noise_percentile
                )
            )
        out = np.stack(out, axis=0)
        out_path = Path(args.output) / f"{path.stem}_denoise.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
