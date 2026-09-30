import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_tif


def initialize_centers(features, k, seed=0):
    rng = np.random.default_rng(seed)
    ndvi = features[:, 0]
    hue = features[:, 1]
    p10, p50, p90 = np.percentile(ndvi, [10, 50, 90])
    h50 = np.percentile(hue, 50)

    if features.shape[1] >= 3:
        ndmi = features[:, 2]
        m10, m50, m90 = np.percentile(ndmi, [10, 50, 90])
        centers = np.array(
            [[p10, h50, m10], [p50, h50, m50], [p90, h50, m90]],
            dtype=np.float32,
        )
    else:
        centers = np.array([[p10, h50], [p50, h50], [p90, h50]], dtype=np.float32)

    if k != 3:
        idx = rng.choice(features.shape[0], size=k, replace=False)
        centers = features[idx].astype(np.float32)
    return centers


def kmeans(features, k=3, iterations=10, seed=0):
    centers = initialize_centers(features, k, seed=seed)
    for _ in range(iterations):
        dists = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1)
        for i in range(k):
            mask = labels == i
            if np.any(mask):
                centers[i] = features[mask].mean(axis=0)
    return labels, centers


def main():
    parser = argparse.ArgumentParser(description="K-means segmentation on NDVI and Hue.")
    parser.add_argument("--input", default="outputs/04_features", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/05_segments", help="Output folder")
    parser.add_argument("--k", type=int, default=3, help="Number of clusters")
    parser.add_argument("--iterations", type=int, default=10, help="K-means iterations")
    parser.add_argument("--sample", type=int, default=200000, help="Sample size for fitting")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        ndvi = data[0].astype(np.float32)
        hue = data[1].astype(np.float32)
        if data.shape[0] >= 3:
            ndmi = data[2].astype(np.float32)
            flat = np.stack([ndvi.ravel(), hue.ravel(), ndmi.ravel()], axis=1)
        else:
            flat = np.stack([ndvi.ravel(), hue.ravel()], axis=1)
        mask = np.isfinite(flat).all(axis=1)
        flat = flat[mask]

        if flat.shape[0] > args.sample:
            rng = np.random.default_rng(args.seed)
            idx = rng.choice(flat.shape[0], size=args.sample, replace=False)
            sample = flat[idx]
        else:
            sample = flat

        mean = sample.mean(axis=0)
        std = sample.std(axis=0)
        std[std == 0] = 1
        sample_n = (sample - mean) / std

        labels_s, centers = kmeans(sample_n, k=args.k, iterations=args.iterations, seed=args.seed)
        centers = centers * std + mean

        flat_n = (flat - mean) / std
        dists = ((flat_n[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1).astype(np.uint8)

        full_labels = np.zeros(ndvi.size, dtype=np.uint8)
        full_labels[mask] = labels + 1
        label_img = full_labels.reshape(ndvi.shape)
        out = np.expand_dims(label_img, axis=0)

        out_path = Path(args.output) / f"{path.stem}_segments.tif"
        write_tif(out_path, out, profile, dtype="uint8", descriptions=["SEGMENTS"])
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
