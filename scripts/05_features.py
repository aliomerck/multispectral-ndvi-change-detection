import argparse
from pathlib import Path

import numpy as np

from common import (
    band_indices_from_descriptions,
    compute_hue,
    compute_ndvi,
    ensure_dir,
    list_tifs,
    read_tif,
    write_tif,
)


def main():
    parser = argparse.ArgumentParser(description="Compute NDVI and Hue features.")
    parser.add_argument("--input", default="outputs/03_denoised", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/04_features", help="Output folder")
    parser.add_argument("--blue", default="B2", help="Blue band name")
    parser.add_argument("--green", default="B3", help="Green band name")
    parser.add_argument("--red", default="B4", help="Red band name")
    parser.add_argument("--nir", default="B8", help="NIR band name")
    parser.add_argument("--swir", default="B11", help="SWIR band name for NDMI")
    parser.add_argument("--hue-rad", action="store_true", help="Store hue in radians")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        mapping = band_indices_from_descriptions(descriptions)
        try:
            b_i = mapping[args.blue] - 1
            g_i = mapping[args.green] - 1
            r_i = mapping[args.red] - 1
            n_i = mapping[args.nir] - 1
            sw_i = mapping.get(args.swir, None)
            if sw_i is not None:
                sw_i = sw_i - 1
        except KeyError:
            b_i, g_i, r_i, n_i = 0, 1, 2, 3
            sw_i = None

        blue = data[b_i]
        green = data[g_i]
        red = data[r_i]
        nir = data[n_i]

        ndvi = compute_ndvi(red, nir)
        hue = compute_hue(red, green, blue, degrees=not args.hue_rad)
        bands = [ndvi, hue]
        descriptions_out = ["NDVI", "HUE"]
        if sw_i is not None and sw_i < data.shape[0]:
            swir = data[sw_i]
            ndmi = compute_ndvi(swir, nir)
            bands.append(ndmi)
            descriptions_out.append("NDMI")
        out = np.stack(bands, axis=0)
        out_path = Path(args.output) / f"{path.stem}_features.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions_out)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
