import argparse
from pathlib import Path

from common import dark_object_subtraction, ensure_dir, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply Dark Object Subtraction.")
    parser.add_argument("--input", default="photos", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/01_dos", help="Output folder")
    parser.add_argument("--percentile", type=float, default=1.0, help="Dark pixel percentile")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        out = dark_object_subtraction(data, percentile=args.percentile)
        out_path = Path(args.output) / f"{path.stem}_dos.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
