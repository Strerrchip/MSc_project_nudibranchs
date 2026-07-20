from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
    / "sam_scaled_ring120_image_metrics_pilot.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "qc_figures"
    / "chromatic_edges"
)

EDGE_MASK_EROSION_PIXELS = 2


# =========================
# File functions
# =========================

def resolve_project_path(path_value):
    """Convert a project-relative path to a full path."""
    path = Path(str(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_rgb_image(path):
    """Read an image as an RGB NumPy array."""
    image = Image.open(path).convert("RGB")
    return np.array(image)


def load_mask(path):
    """Read a mask as a boolean NumPy array."""
    mask_image = Image.open(path).convert("L")
    return np.array(mask_image) > 127


# =========================
# Measurement functions
# =========================

def erode_region_mask(mask, erosion_pixels=EDGE_MASK_EROSION_PIXELS):
    """
    Slightly shrink a mask before measuring internal edges.

    This reduces the influence of the animal outline and the borders
    of the background ring.
    """
    if np.sum(mask) == 0:
        return mask.copy()

    if erosion_pixels <= 0:
        return mask.copy()

    kernel = np.ones((3, 3), dtype=np.uint8)

    eroded_mask = cv2.erode(
        mask.astype(np.uint8),
        kernel,
        iterations=erosion_pixels,
    ) > 0

    if np.sum(eroded_mask) < 10:
        return mask.copy()

    return eroded_mask


def calculate_chromatic_gradient(rgb_image):
    """
    Calculate chromatic-edge strength from CIELAB a* and b*.

    L* is excluded so that this heatmap mainly represents local colour
    changes rather than light-dark changes.
    """
    rgb_float = rgb_image.astype(np.float32) / 255.0

    lab = cv2.cvtColor(
        rgb_float,
        cv2.COLOR_RGB2LAB,
    )

    lab_a = lab[:, :, 1]
    lab_b = lab[:, :, 2]

    a_gradient_x = cv2.Sobel(
        lab_a,
        cv2.CV_32F,
        1,
        0,
        ksize=3,
    )
    a_gradient_y = cv2.Sobel(
        lab_a,
        cv2.CV_32F,
        0,
        1,
        ksize=3,
    )

    b_gradient_x = cv2.Sobel(
        lab_b,
        cv2.CV_32F,
        1,
        0,
        ksize=3,
    )
    b_gradient_y = cv2.Sobel(
        lab_b,
        cv2.CV_32F,
        0,
        1,
        ksize=3,
    )

    return np.sqrt(
        a_gradient_x ** 2
        + a_gradient_y ** 2
        + b_gradient_x ** 2
        + b_gradient_y ** 2
    )


def make_masked_heatmap(values, mask):
    """Return values inside the mask and NaN outside it."""
    heatmap = np.full(values.shape, np.nan, dtype=np.float32)
    heatmap[mask] = values[mask]
    return heatmap


# =========================
# QC figure
# =========================

def create_qc_figure(
    rgb_image,
    animal_mask,
    background_ring,
    image_id,
    output_path,
):
    """Create one chromatic-edge QC figure for an image."""
    animal_internal_mask = erode_region_mask(animal_mask)
    background_internal_mask = erode_region_mask(background_ring)

    chromatic_gradient = calculate_chromatic_gradient(rgb_image)

    animal_heatmap = make_masked_heatmap(
        chromatic_gradient,
        animal_internal_mask,
    )

    background_heatmap = make_masked_heatmap(
        chromatic_gradient,
        background_internal_mask,
    )

    combined_mask = animal_internal_mask | background_internal_mask

    if np.any(combined_mask):
        display_max = float(
            np.percentile(
                chromatic_gradient[combined_mask],
                99,
            )
        )
    else:
        display_max = float(np.max(chromatic_gradient))

    if display_max <= 0:
        display_max = 1.0

    figure, axes = plt.subplots(
        2,
        2,
        figsize=(12, 10),
    )

    axes[0, 0].imshow(rgb_image)
    axes[0, 0].set_title("Scaled RGB image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(rgb_image)
    axes[0, 1].contour(
        animal_mask.astype(np.uint8),
        levels=[0.5],
        linewidths=1,
    )
    axes[0, 1].contour(
        background_ring.astype(np.uint8),
        levels=[0.5],
        linewidths=1,
    )
    axes[0, 1].set_title("Animal mask and 120 px background ring")
    axes[0, 1].axis("off")

    animal_plot = axes[1, 0].imshow(
        animal_heatmap,
        vmin=0,
        vmax=display_max,
    )
    axes[1, 0].set_title("Animal chromatic-edge strength")
    axes[1, 0].axis("off")
    figure.colorbar(
        animal_plot,
        ax=axes[1, 0],
        fraction=0.046,
        pad=0.04,
    )

    background_plot = axes[1, 1].imshow(
        background_heatmap,
        vmin=0,
        vmax=display_max,
    )
    axes[1, 1].set_title("Background chromatic-edge strength")
    axes[1, 1].axis("off")
    figure.colorbar(
        background_plot,
        ax=axes[1, 1],
        fraction=0.046,
        pad=0.04,
    )

    figure.suptitle(
        f"Chromatic-edge QC: {image_id}",
        fontsize=14,
    )

    figure.tight_layout()
    figure.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(figure)


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find image-level metrics CSV: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_df = pd.read_csv(INPUT_CSV)

    required_columns = [
        "image_id",
        "scaled_image_path",
        "animal_mask_path",
        "background_ring_path",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in image_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    for _, row in image_df.iterrows():
        image_id = row["image_id"]

        print(f"Creating chromatic-edge QC for: {image_id}")

        scaled_image_path = resolve_project_path(
            row["scaled_image_path"]
        )
        animal_mask_path = resolve_project_path(
            row["animal_mask_path"]
        )
        background_ring_path = resolve_project_path(
            row["background_ring_path"]
        )

        rgb_image = load_rgb_image(scaled_image_path)
        animal_mask = load_mask(animal_mask_path)
        background_ring = load_mask(background_ring_path)

        expected_shape = rgb_image.shape[:2]

        if animal_mask.shape != expected_shape:
            raise ValueError(
                f"Animal mask shape mismatch for {image_id}."
            )

        if background_ring.shape != expected_shape:
            raise ValueError(
                f"Background ring shape mismatch for {image_id}."
            )

        output_path = OUTPUT_DIR / f"{image_id}_chromatic_edge_qc.png"

        create_qc_figure(
            rgb_image,
            animal_mask,
            background_ring,
            image_id,
            output_path,
        )

    print("\nDone.")
    print(f"QC figures saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()