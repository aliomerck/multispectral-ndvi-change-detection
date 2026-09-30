import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio


def main():
    parser = argparse.ArgumentParser(description="Colorize Istanbul vegetation diff.")
    parser.add_argument(
        "--input",
        default="outputs/06_temporal/Istanbul_2016_2024_veg_diff.tif",
        help="Input diff TIFF (2016_2024 order)",
    )
    parser.add_argument(
        "--output",
        default="outputs/06_temporal/Istanbul_veg_change_red_yellow.png",
        help="Output PNG path",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Missing diff file: {in_path}")

    with rasterio.open(in_path) as ds:
        diff = ds.read(1)

    # For 2016_2024 order: -1 => loss, +1 => gain.
    h, w = diff.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    loss = diff == -1
    gain = diff == 1

    rgb[loss] = (255, 0, 0)     # red = loss
    rgb[gain] = (255, 255, 0)   # yellow = gain

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, mode="RGB").save(out_path)
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
