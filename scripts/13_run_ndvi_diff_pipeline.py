import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from common import (
    adaptive_noise_reduction,
    band_indices_from_descriptions,
    compute_ndvi,
    dark_object_subtraction,
    ensure_dir,
    homomorphic_filter,
    read_tif,
    write_tif,
)


def ndvi_colormap(ndvi):
    # Simple red-yellow-green ramp for quick NDVI previews.
    x = np.clip((ndvi + 1.0) / 2.0, 0, 1)
    r = np.where(x < 0.5, 1.0, 1.0 - (x - 0.5) * 2.0)
    g = np.where(x < 0.5, x * 2.0, 1.0)
    b = np.zeros_like(x)
    rgb = np.stack([r, g, b], axis=2)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def diff_colormap(diff, vmin=-0.5, vmax=0.0):
    # Show only loss (negative change). Gains are set to black.
    neg = np.minimum(diff, 0.0)
    x = (neg - vmin) / (vmax - vmin)
    x = np.clip(x, 0, 1)
    r = x
    g = np.zeros_like(x)
    b = np.zeros_like(x)
    rgb = np.stack([r, g, b], axis=2)
    return (rgb * 255).astype(np.uint8)


def save_png(path, rgb):
    Image.fromarray(rgb, mode="RGB").save(path)


def resolve_band_indices(descriptions, blue, green, red, nir):
    # Prefer named bands if present, otherwise fall back to the first 4 bands.
    mapping = band_indices_from_descriptions(descriptions)

    def idx(name, fallback):
        if name in mapping:
            return mapping[name] - 1
        return fallback

    return (
        idx(blue, 0),
        idx(green, 1),
        idx(red, 2),
        idx(nir, 3),
    )


def process_image(path, args, out_dir, prefix):
    data, profile, descriptions = read_tif(path)

    # 1) DOS for haze correction.
    dos = dark_object_subtraction(data, percentile=args.dos_percentile)
    dos_path = out_dir / f"{prefix}_dos.tif"
    write_tif(dos_path, dos, profile, dtype="float32", descriptions=descriptions)

    # 2) Homomorphic filter to reduce illumination effects.
    homo_bands = []
    for i in range(dos.shape[0]):
        homo_bands.append(
            homomorphic_filter(
                dos[i],
                gamma_l=args.gamma_l,
                gamma_h=args.gamma_h,
                c=args.c,
                d0=args.d0,
            )
        )
    homo = np.stack(homo_bands, axis=0)
    homo_path = out_dir / f"{prefix}_homo.tif"
    write_tif(homo_path, homo, profile, dtype="float32", descriptions=descriptions)

    # 3) Adaptive local noise reduction.
    denoise_bands = []
    for i in range(homo.shape[0]):
        denoise_bands.append(
            adaptive_noise_reduction(
                homo[i],
                window=args.window,
                noise_percentile=args.noise_percentile,
            )
        )
    denoise = np.stack(denoise_bands, axis=0)
    denoise_path = out_dir / f"{prefix}_denoise.tif"
    write_tif(denoise_path, denoise, profile, dtype="float32", descriptions=descriptions)

    # 4) NDVI feature from the corrected bands.
    b_i, g_i, r_i, n_i = resolve_band_indices(
        descriptions, args.blue, args.green, args.red, args.nir
    )
    ndvi = compute_ndvi(denoise[r_i], denoise[n_i])
    ndvi_path = out_dir / f"{prefix}_ndvi.tif"
    write_tif(ndvi_path, ndvi[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI"])

    ndvi_png = out_dir / f"{prefix}_ndvi.png"
    save_png(ndvi_png, ndvi_colormap(ndvi))

    return ndvi, profile


def main():
    parser = argparse.ArgumentParser(
        description="Run DOS -> homomorphic -> denoise -> NDVI and output NDVI diff."
    )
    parser.add_argument("--image-a", required=True, help="First GeoTIFF (A)")
    parser.add_argument("--image-b", required=True, help="Second GeoTIFF (B)")
    parser.add_argument("--output", default="outputs/ndvi_diff_runs", help="Output root")
    parser.add_argument("--tag", default=None, help="Output folder name")
    parser.add_argument("--blue", default="B2", help="Blue band name")
    parser.add_argument("--green", default="B3", help="Green band name")
    parser.add_argument("--red", default="B4", help="Red band name")
    parser.add_argument("--nir", default="B8", help="NIR band name")
    parser.add_argument("--dos-percentile", type=float, default=1.0, help="DOS percentile")
    parser.add_argument("--gamma-l", type=float, default=0.5, help="Homomorphic low gain")
    parser.add_argument("--gamma-h", type=float, default=1.5, help="Homomorphic high gain")
    parser.add_argument("--c", type=float, default=1.0, help="Homomorphic sharpness")
    parser.add_argument("--d0", type=float, default=30.0, help="Homomorphic cutoff")
    parser.add_argument("--window", type=int, default=7, help="Denoise window (odd)")
    parser.add_argument(
        "--noise-percentile",
        type=float,
        default=10.0,
        help="Denoise noise percentile",
    )
    parser.add_argument("--diff-vmin", type=float, default=-0.5, help="Diff colormap min")
    parser.add_argument("--diff-vmax", type=float, default=0.5, help="Diff colormap max")
    args = parser.parse_args()

    path_a = Path(args.image_a)
    path_b = Path(args.image_b)
    if not path_a.exists() or not path_b.exists():
        raise FileNotFoundError("One or both input images do not exist.")

    tag = args.tag
    if not tag:
        tag = f"{path_a.stem}_vs_{path_b.stem}"
    out_dir = Path(args.output) / tag
    ensure_dir(out_dir)

    # Run the same pipeline for both inputs.
    ndvi_a, profile = process_image(path_a, args, out_dir, "a")
    ndvi_b, _ = process_image(path_b, args, out_dir, "b")

    # Diff is B - A (positive means increase in NDVI).
    diff = ndvi_b.astype(np.float32) - ndvi_a.astype(np.float32)
    diff_name = f"ndvi_diff_{tag.lower()}.tif"
    diff_path = out_dir / diff_name
    write_tif(diff_path, diff[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI_DIFF"])

    diff_png = out_dir / diff_name.replace(".tif", ".png")
    save_png(diff_png, diff_colormap(diff, vmin=args.diff_vmin, vmax=args.diff_vmax))

    print("Wrote", diff_path)
    print("Wrote", diff_png)


if __name__ == "__main__":
    main()
