import argparse
from pathlib import Path

import rasterio

from common import list_tifs, write_csv


def main():
    parser = argparse.ArgumentParser(description="Scan GeoTIFFs and report metadata.")
    parser.add_argument("--input", default="photos", help="Input folder with .tif files")
    parser.add_argument("--out", default="outputs/00_data_check.csv", help="CSV output path")
    args = parser.parse_args()

    rows = []
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        with rasterio.open(path) as ds:
            names = [n if n else "" for n in ds.descriptions]
            row = [
                path.name,
                ds.width,
                ds.height,
                ds.count,
                str(ds.crs) if ds.crs else "",
                ",".join(ds.dtypes),
                ",".join(names),
            ]
            rows.append(row)
            print(
                f"{path.name}: {ds.width}x{ds.height}, bands={ds.count}, "
                f"dtypes={ds.dtypes}, names={names}"
            )

    write_csv(args.out, rows, ["file", "width", "height", "bands", "crs", "dtypes", "band_names"])
    print("Wrote", Path(args.out))


if __name__ == "__main__":
    main()
