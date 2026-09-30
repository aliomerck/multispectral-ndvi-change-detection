import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, homomorphic_filter, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply homomorphic filtering.")
    parser.add_argument("--input", default="outputs/01_dos", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/02_homomorphic", help="Output folder")
    parser.add_argument("--gamma-l", type=float, default=0.5, help="Low-frequency gain")
    parser.add_argument("--gamma-h", type=float, default=1.5, help="High-frequency gain")
    parser.add_argument("--c", type=float, default=1.0, help="Filter sharpness")
    parser.add_argument("--d0", type=float, default=30.0, help="Cutoff frequency")
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
                homomorphic_filter(
                    data[i],
                    gamma_l=args.gamma_l,
                    gamma_h=args.gamma_h,
                    c=args.c,
                    d0=args.d0,
                )
            )
        out = np.stack(out, axis=0)
        out_path = Path(args.output) / f"{path.stem}_homo.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
