from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUMMARY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "sam_scaled_ring120_pilot_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
)

OUTPUT_CSV = OUTPUT_DIR / "sam_scaled_ring120_image_metrics_pilot.csv"


# =========================
# Helper functions
# =========================

def resolve_project_path(path_value):
    """Convert a project-relative path to a full path."""
    path = Path(str(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def make_project_relative_path(path):
    """Convert a full path to a project-relative path."""
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_rgb_image(path):
    """Read image as RGB array."""
    image = Image.open(path).convert("RGB")
    return np.array(image)


def load_mask(path):
    """Read mask as a boolean array."""
    mask_image = Image.open(path).convert("L")
    mask = np.array(mask_image) > 127
    return mask


def region_mean(values, mask):
    """Calculate mean value inside a mask."""
    if np.sum(mask) == 0:
        return np.nan

    return float(np.mean(values[mask]))


def region_sd(values, mask):
    """Calculate standard deviation inside a mask."""
    if np.sum(mask) == 0:
        return np.nan

    return float(np.std(values[mask]))


def calculate_edge_density(gray_image, animal_mask):
    """
    Calculate edge density inside the animal mask.

    This is a simple animal-only pattern metric.
    Higher values mean more internal edges or texture inside the animal region.
    """
    if np.sum(animal_mask) == 0:
        return np.nan

    edges = cv2.Canny(gray_image, threshold1=100, threshold2=200)
    edges_inside_animal = (edges > 0) & animal_mask

    edge_density = np.sum(edges_inside_animal) / np.sum(animal_mask)

    return float(edge_density)


def check_same_shape(image, animal_mask, background_ring, image_id):
    """Check that image and masks have the same size."""
    image_height, image_width = image.shape[:2]

    if animal_mask.shape != (image_height, image_width):
        raise ValueError(
            f"Animal mask size does not match image size for {image_id}. "
            f"Image size: {(image_height, image_width)}, "
            f"mask size: {animal_mask.shape}"
        )

    if background_ring.shape != (image_height, image_width):
        raise ValueError(
            f"Background ring size does not match image size for {image_id}. "
            f"Image size: {(image_height, image_width)}, "
            f"ring size: {background_ring.shape}"
        )


# =========================
# Main workflow
# =========================

def main():
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(f"Cannot find summary CSV: {SUMMARY_CSV}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_df = pd.read_csv(SUMMARY_CSV)

    metric_rows = []

    for _, row in summary_df.iterrows():
        species = row["species"]
        image_id = row["image_id"]

        print(f"Processing metrics for: {image_id}")

        scaled_image_path = resolve_project_path(row["scaled_image_output_path"])
        animal_mask_path = resolve_project_path(row["mask_output_path"])
        background_ring_path = resolve_project_path(row["background_ring_output_path"])

        rgb_image = load_rgb_image(scaled_image_path)
        animal_mask = load_mask(animal_mask_path)
        background_ring = load_mask(background_ring_path)

        check_same_shape(rgb_image, animal_mask, background_ring, image_id)

        animal_pixels = int(np.sum(animal_mask))
        background_ring_pixels = int(np.sum(background_ring))
        image_pixels = int(rgb_image.shape[0] * rgb_image.shape[1])

        # RGB channels
        red = rgb_image[:, :, 0]
        green = rgb_image[:, :, 1]
        blue = rgb_image[:, :, 2]

        # Gray image
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)

        # HSV image
        hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1]
        brightness = hsv[:, :, 2]

        # Lab image
        lab = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2LAB)
        lab_l = lab[:, :, 0]
        lab_a = lab[:, :, 1]
        lab_b = lab[:, :, 2]

        # Animal means
        animal_red_mean = region_mean(red, animal_mask)
        animal_green_mean = region_mean(green, animal_mask)
        animal_blue_mean = region_mean(blue, animal_mask)

        animal_gray_mean = region_mean(gray, animal_mask)
        animal_saturation_mean = region_mean(saturation, animal_mask)
        animal_brightness_mean = region_mean(brightness, animal_mask)

        animal_lab_l_mean = region_mean(lab_l, animal_mask)
        animal_lab_a_mean = region_mean(lab_a, animal_mask)
        animal_lab_b_mean = region_mean(lab_b, animal_mask)

        # Background means
        background_red_mean = region_mean(red, background_ring)
        background_green_mean = region_mean(green, background_ring)
        background_blue_mean = region_mean(blue, background_ring)

        background_gray_mean = region_mean(gray, background_ring)
        background_saturation_mean = region_mean(saturation, background_ring)
        background_brightness_mean = region_mean(brightness, background_ring)

        background_lab_l_mean = region_mean(lab_l, background_ring)
        background_lab_a_mean = region_mean(lab_a, background_ring)
        background_lab_b_mean = region_mean(lab_b, background_ring)

        # Animal-only variation
        animal_red_sd = region_sd(red, animal_mask)
        animal_green_sd = region_sd(green, animal_mask)
        animal_blue_sd = region_sd(blue, animal_mask)

        animal_gray_sd = region_sd(gray, animal_mask)
        animal_saturation_sd = region_sd(saturation, animal_mask)
        animal_brightness_sd = region_sd(brightness, animal_mask)

        # Background variation
        background_gray_sd = region_sd(gray, background_ring)
        background_saturation_sd = region_sd(saturation, background_ring)
        background_brightness_sd = region_sd(brightness, background_ring)

        # Animal-background contrasts
        red_contrast = animal_red_mean - background_red_mean
        green_contrast = animal_green_mean - background_green_mean
        blue_contrast = animal_blue_mean - background_blue_mean

        gray_contrast = animal_gray_mean - background_gray_mean
        saturation_contrast = animal_saturation_mean - background_saturation_mean
        brightness_contrast = animal_brightness_mean - background_brightness_mean

        lab_l_contrast = animal_lab_l_mean - background_lab_l_mean
        lab_a_contrast = animal_lab_a_mean - background_lab_a_mean
        lab_b_contrast = animal_lab_b_mean - background_lab_b_mean

        lab_colour_distance = float(
            np.sqrt(
                lab_l_contrast ** 2
                + lab_a_contrast ** 2
                + lab_b_contrast ** 2
            )
        )

        animal_edge_density = calculate_edge_density(gray, animal_mask)

        metric_rows.append(
            {
                "species": species,
                "image_id": image_id,

                "scaled_image_path": make_project_relative_path(scaled_image_path),
                "animal_mask_path": make_project_relative_path(animal_mask_path),
                "background_ring_path": make_project_relative_path(background_ring_path),

                "scaled_width": rgb_image.shape[1],
                "scaled_height": rgb_image.shape[0],
                "animal_area_pixels": animal_pixels,
                "background_ring_area_pixels": background_ring_pixels,
                "scaled_image_area_pixels": image_pixels,
                "animal_area_fraction": animal_pixels / image_pixels,
                "background_ring_area_fraction": background_ring_pixels / image_pixels,

                "animal_red_mean": animal_red_mean,
                "background_red_mean": background_red_mean,
                "red_contrast": red_contrast,

                "animal_green_mean": animal_green_mean,
                "background_green_mean": background_green_mean,
                "green_contrast": green_contrast,

                "animal_blue_mean": animal_blue_mean,
                "background_blue_mean": background_blue_mean,
                "blue_contrast": blue_contrast,

                "animal_gray_mean": animal_gray_mean,
                "background_gray_mean": background_gray_mean,
                "gray_contrast": gray_contrast,

                "animal_saturation_mean": animal_saturation_mean,
                "background_saturation_mean": background_saturation_mean,
                "saturation_contrast": saturation_contrast,

                "animal_brightness_mean": animal_brightness_mean,
                "background_brightness_mean": background_brightness_mean,
                "brightness_contrast": brightness_contrast,

                "animal_lab_l_mean": animal_lab_l_mean,
                "background_lab_l_mean": background_lab_l_mean,
                "lab_l_contrast": lab_l_contrast,

                "animal_lab_a_mean": animal_lab_a_mean,
                "background_lab_a_mean": background_lab_a_mean,
                "lab_a_contrast": lab_a_contrast,

                "animal_lab_b_mean": animal_lab_b_mean,
                "background_lab_b_mean": background_lab_b_mean,
                "lab_b_contrast": lab_b_contrast,

                "lab_colour_distance": lab_colour_distance,

                "animal_red_sd": animal_red_sd,
                "animal_green_sd": animal_green_sd,
                "animal_blue_sd": animal_blue_sd,
                "animal_gray_sd": animal_gray_sd,
                "animal_saturation_sd": animal_saturation_sd,
                "animal_brightness_sd": animal_brightness_sd,

                "background_gray_sd": background_gray_sd,
                "background_saturation_sd": background_saturation_sd,
                "background_brightness_sd": background_brightness_sd,

                "animal_edge_density": animal_edge_density,
            }
        )

    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(OUTPUT_CSV, index=False)

    print("\nDone.")
    print(f"Image-level metrics saved to: {make_project_relative_path(OUTPUT_CSV)}")

    preview_columns = [
        "species",
        "image_id",
        "gray_contrast",
        "brightness_contrast",
        "saturation_contrast",
        "lab_colour_distance",
        "animal_brightness_sd",
        "animal_saturation_sd",
        "animal_edge_density",
    ]

    print("\nPreview:")
    print(metrics_df[preview_columns].round(3).to_string(index=False))


if __name__ == "__main__":
    main()