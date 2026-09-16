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
    / "sam_scaled_ring120_final_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
)

OUTPUT_CSV = OUTPUT_DIR / "sam_scaled_ring120_image_metrics_final.csv"

# Edge settings
CANNY_THRESHOLD_1 = 100
CANNY_THRESHOLD_2 = 200

# Remove a narrow boundary before calculating internal edge measurements.
# This reduces contamination from the animal-background outline and
# from the inner and outer borders of the background ring.
EDGE_MASK_EROSION_PIXELS = 2

# Avoid division by a value extremely close to zero.
CV_EPSILON = 1e-8


# =========================
# Path and image functions
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
    """Read an image as an RGB NumPy array."""
    image = Image.open(path).convert("RGB")
    return np.array(image)


def load_mask(path):
    """Read a mask as a boolean NumPy array."""
    mask_image = Image.open(path).convert("L")
    return np.array(mask_image) > 127


# =========================
# Region summary functions
# =========================

def region_mean(values, mask):
    """Calculate the mean value inside a mask."""
    if np.sum(mask) == 0:
        return np.nan

    return float(np.mean(values[mask]))


def region_sd(values, mask):
    """Calculate the standard deviation inside a mask."""
    if np.sum(mask) == 0:
        return np.nan

    return float(np.std(values[mask]))


def erode_region_mask(mask, erosion_pixels=EDGE_MASK_EROSION_PIXELS):
    """
    Slightly shrink a mask before calculating internal edge measurements.

    For the animal, this reduces the influence of the outer silhouette.
    For the background ring, this removes the inner and outer ring borders.
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

    # Fall back to the original mask if erosion removes almost everything.
    if np.sum(eroded_mask) < 10:
        return mask.copy()

    return eroded_mask


# =========================
# Edge measurement functions
# =========================

def calculate_edge_density(gray_image, region_mask):
    """
    Calculate Canny edge density inside a region.

    Edge density is the proportion of region pixels classified as edges.
    The region mask is eroded first so that region boundaries are not
    treated as internal pattern edges.
    """
    internal_mask = erode_region_mask(region_mask)

    if np.sum(internal_mask) == 0:
        return np.nan

    edges = cv2.Canny(
        gray_image,
        threshold1=CANNY_THRESHOLD_1,
        threshold2=CANNY_THRESHOLD_2,
    )

    edge_pixels = (edges > 0) & internal_mask
    edge_density = np.sum(edge_pixels) / np.sum(internal_mask)

    return float(edge_density)


def calculate_luminance_edge_metrics(lightness_image, region_mask):
    """
    Calculate simplified luminance-edge measurements inside a region.

    CIELAB L* is used as a simple achromatic/lightness proxy.

    The Sobel gradient magnitude describes the strength of local
    light-dark changes. This is inspired by the edge-based measurements
    in D05 and D06, but it does not reproduce QCPA, LEIA or predator
    visual modelling.

    Returns:
        mean edge strength
        standard deviation of edge strength
        coefficient of variation of edge strength
    """
    internal_mask = erode_region_mask(region_mask)

    if np.sum(internal_mask) == 0:
        return np.nan, np.nan, np.nan

    lightness_float = lightness_image.astype(np.float32)

    gradient_x = cv2.Sobel(
        lightness_float,
        cv2.CV_32F,
        1,
        0,
        ksize=3,
    )

    gradient_y = cv2.Sobel(
        lightness_float,
        cv2.CV_32F,
        0,
        1,
        ksize=3,
    )

    gradient_magnitude = cv2.magnitude(gradient_x, gradient_y)
    region_values = gradient_magnitude[internal_mask]

    if region_values.size == 0:
        return np.nan, np.nan, np.nan

    edge_mean = float(np.mean(region_values))
    edge_sd = float(np.std(region_values))

    if edge_mean <= CV_EPSILON:
        edge_cv = np.nan
    else:
        edge_cv = float(edge_sd / edge_mean)

    return edge_mean, edge_sd, edge_cv


def calculate_chromatic_edge_metrics(
    lab_a_image,
    lab_b_image,
    region_mask,
):
    """
    Calculate simplified chromatic-edge measurements inside a region.

    CIELAB a* and b* are used as two opponent-colour channels.
    Sobel gradients are calculated for both channels and combined as:

        sqrt(
            da_dx^2 + da_dy^2
            + db_dx^2 + db_dy^2
        )

    This describes the strength of local colour changes while reducing
    the influence of light-dark changes already measured with L*.

    It is inspired by the chromatic edge measurements in D04-D06,
    but it does not reproduce QCPA, LEIA or predator visual modelling.

    Returns:
        mean chromatic-edge strength
        standard deviation of chromatic-edge strength
        coefficient of variation of chromatic-edge strength
    """
    internal_mask = erode_region_mask(region_mask)

    if np.sum(internal_mask) == 0:
        return np.nan, np.nan, np.nan

    lab_a_float = lab_a_image.astype(np.float32)
    lab_b_float = lab_b_image.astype(np.float32)

    a_gradient_x = cv2.Sobel(
        lab_a_float,
        cv2.CV_32F,
        1,
        0,
        ksize=3,
    )
    a_gradient_y = cv2.Sobel(
        lab_a_float,
        cv2.CV_32F,
        0,
        1,
        ksize=3,
    )

    b_gradient_x = cv2.Sobel(
        lab_b_float,
        cv2.CV_32F,
        1,
        0,
        ksize=3,
    )
    b_gradient_y = cv2.Sobel(
        lab_b_float,
        cv2.CV_32F,
        0,
        1,
        ksize=3,
    )

    chromatic_gradient_magnitude = np.sqrt(
        a_gradient_x ** 2
        + a_gradient_y ** 2
        + b_gradient_x ** 2
        + b_gradient_y ** 2
    )

    region_values = chromatic_gradient_magnitude[internal_mask]

    if region_values.size == 0:
        return np.nan, np.nan, np.nan

    edge_mean = float(np.mean(region_values))
    edge_sd = float(np.std(region_values))

    if edge_mean <= CV_EPSILON:
        edge_cv = np.nan
    else:
        edge_cv = float(edge_sd / edge_mean)

    return edge_mean, edge_sd, edge_cv


# =========================
# Validation functions
# =========================

def check_same_shape(image, animal_mask, background_ring, image_id):
    """Check that the image and masks have matching dimensions."""
    image_height, image_width = image.shape[:2]

    expected_shape = (image_height, image_width)

    if animal_mask.shape != expected_shape:
        raise ValueError(
            f"Animal mask size does not match image size for {image_id}. "
            f"Image size: {expected_shape}, "
            f"mask size: {animal_mask.shape}"
        )

    if background_ring.shape != expected_shape:
        raise ValueError(
            f"Background ring size does not match image size for {image_id}. "
            f"Image size: {expected_shape}, "
            f"ring size: {background_ring.shape}"
        )

    if np.any(animal_mask & background_ring):
        raise ValueError(
            f"Animal mask and background ring overlap for {image_id}."
        )

    if np.sum(animal_mask) == 0:
        raise ValueError(f"Animal mask is empty for {image_id}.")

    if np.sum(background_ring) == 0:
        raise ValueError(f"Background ring is empty for {image_id}.")


# =========================
# Main workflow
# =========================

def main():
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find summary CSV: {SUMMARY_CSV}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_df = pd.read_csv(SUMMARY_CSV)

    # Final-dataset checks.
    expected_image_count = 295
    expected_species_count = 30

    if len(summary_df) != expected_image_count:
        raise ValueError(
            f"Expected {expected_image_count} final images, "
            f"but summary contains {len(summary_df)} rows."
        )

    if summary_df["image_id"].duplicated().any():
        duplicated_ids = (
            summary_df.loc[
                summary_df["image_id"].duplicated(keep=False),
                "image_id",
            ]
            .astype(str)
            .tolist()
        )
        raise ValueError(
            "Duplicate image_id values found in final summary: "
            + ", ".join(duplicated_ids)
        )

    species_count = summary_df["species"].nunique()

    if species_count != expected_species_count:
        raise ValueError(
            f"Expected {expected_species_count} species, "
            f"but summary contains {species_count}."
        )

    print(
        f"Validated final dataset: "
        f"{len(summary_df)} images across "
        f"{species_count} species."
    )

    metric_rows = []

    for _, row in summary_df.iterrows():
        species = row["species"]
        image_id = row["image_id"]

        print(f"Processing metrics for: {image_id}")

        scaled_image_path = resolve_project_path(
            row["scaled_image_output_path"]
        )

        animal_mask_path = resolve_project_path(
            row["mask_output_path"]
        )

        background_ring_path = resolve_project_path(
            row["background_ring_output_path"]
        )

        rgb_image = load_rgb_image(scaled_image_path)
        animal_mask = load_mask(animal_mask_path)
        background_ring = load_mask(background_ring_path)

        check_same_shape(
            rgb_image,
            animal_mask,
            background_ring,
            image_id,
        )

        animal_pixels = int(np.sum(animal_mask))
        background_ring_pixels = int(np.sum(background_ring))
        image_pixels = int(
            rgb_image.shape[0] * rgb_image.shape[1]
        )

        # -------------------------
        # Colour-space conversion
        # -------------------------

        # RGB channels remain on a 0-255 scale.
        red = rgb_image[:, :, 0]
        green = rgb_image[:, :, 1]
        blue = rgb_image[:, :, 2]

        # Grayscale image on a 0-255 scale.
        gray = cv2.cvtColor(
            rgb_image,
            cv2.COLOR_RGB2GRAY,
        )

        # OpenCV HSV image:
        # saturation and brightness are stored on a 0-255 scale.
        hsv = cv2.cvtColor(
            rgb_image,
            cv2.COLOR_RGB2HSV,
        )

        saturation = hsv[:, :, 1]
        brightness = hsv[:, :, 2]

        # Use a floating-point RGB image for standard CIELAB values.
        # RGB input is scaled to 0-1.
        rgb_float = rgb_image.astype(np.float32) / 255.0

        lab = cv2.cvtColor(
            rgb_float,
            cv2.COLOR_RGB2LAB,
        )

        lab_l = lab[:, :, 0]
        lab_a = lab[:, :, 1]
        lab_b = lab[:, :, 2]

        # -------------------------
        # Animal means
        # -------------------------

        animal_red_mean = region_mean(red, animal_mask)
        animal_green_mean = region_mean(green, animal_mask)
        animal_blue_mean = region_mean(blue, animal_mask)

        animal_gray_mean = region_mean(gray, animal_mask)
        animal_saturation_mean = region_mean(
            saturation,
            animal_mask,
        )
        animal_brightness_mean = region_mean(
            brightness,
            animal_mask,
        )

        animal_lab_l_mean = region_mean(lab_l, animal_mask)
        animal_lab_a_mean = region_mean(lab_a, animal_mask)
        animal_lab_b_mean = region_mean(lab_b, animal_mask)

        # -------------------------
        # Background means
        # -------------------------

        background_red_mean = region_mean(
            red,
            background_ring,
        )
        background_green_mean = region_mean(
            green,
            background_ring,
        )
        background_blue_mean = region_mean(
            blue,
            background_ring,
        )

        background_gray_mean = region_mean(
            gray,
            background_ring,
        )
        background_saturation_mean = region_mean(
            saturation,
            background_ring,
        )
        background_brightness_mean = region_mean(
            brightness,
            background_ring,
        )

        background_lab_l_mean = region_mean(
            lab_l,
            background_ring,
        )
        background_lab_a_mean = region_mean(
            lab_a,
            background_ring,
        )
        background_lab_b_mean = region_mean(
            lab_b,
            background_ring,
        )

        # -------------------------
        # Animal-only variation
        # -------------------------

        animal_red_sd = region_sd(red, animal_mask)
        animal_green_sd = region_sd(green, animal_mask)
        animal_blue_sd = region_sd(blue, animal_mask)

        animal_gray_sd = region_sd(gray, animal_mask)
        animal_saturation_sd = region_sd(
            saturation,
            animal_mask,
        )
        animal_brightness_sd = region_sd(
            brightness,
            animal_mask,
        )

        # -------------------------
        # Background-only variation
        # -------------------------

        background_gray_sd = region_sd(
            gray,
            background_ring,
        )
        background_saturation_sd = region_sd(
            saturation,
            background_ring,
        )
        background_brightness_sd = region_sd(
            brightness,
            background_ring,
        )

        # -------------------------
        # Signed animal-background contrasts
        # -------------------------

        red_contrast = (
            animal_red_mean
            - background_red_mean
        )
        green_contrast = (
            animal_green_mean
            - background_green_mean
        )
        blue_contrast = (
            animal_blue_mean
            - background_blue_mean
        )

        gray_contrast = (
            animal_gray_mean
            - background_gray_mean
        )
        saturation_contrast = (
            animal_saturation_mean
            - background_saturation_mean
        )
        brightness_contrast = (
            animal_brightness_mean
            - background_brightness_mean
        )

        lab_l_contrast = (
            animal_lab_l_mean
            - background_lab_l_mean
        )
        lab_a_contrast = (
            animal_lab_a_mean
            - background_lab_a_mean
        )
        lab_b_contrast = (
            animal_lab_b_mean
            - background_lab_b_mean
        )

        # Signed values describe direction.
        # Absolute values describe the magnitude of detectability.
        gray_contrast_abs = float(abs(gray_contrast))
        saturation_contrast_abs = float(
            abs(saturation_contrast)
        )
        brightness_contrast_abs = float(
            abs(brightness_contrast)
        )

        # Approximate CIE76 distance between the mean animal
        # and mean background colours in floating-point CIELAB.
        lab_colour_distance = float(
            np.sqrt(
                lab_l_contrast ** 2
                + lab_a_contrast ** 2
                + lab_b_contrast ** 2
            )
        )

        # -------------------------
        # Edge-density measurements
        # -------------------------

        animal_edge_density = calculate_edge_density(
            gray,
            animal_mask,
        )

        background_edge_density = calculate_edge_density(
            gray,
            background_ring,
        )

        # -------------------------
        # Simplified luminance-edge measurements
        # -------------------------

        (
            animal_luminance_edge_mean,
            animal_luminance_edge_sd,
            animal_luminance_edge_cv,
        ) = calculate_luminance_edge_metrics(
            lab_l,
            animal_mask,
        )

        (
            background_luminance_edge_mean,
            background_luminance_edge_sd,
            background_luminance_edge_cv,
        ) = calculate_luminance_edge_metrics(
            lab_l,
            background_ring,
        )

        if (
            np.isnan(animal_luminance_edge_cv)
            or np.isnan(background_luminance_edge_cv)
        ):
            luminance_edge_cv_difference = np.nan
        else:
            luminance_edge_cv_difference = float(
                abs(
                    animal_luminance_edge_cv
                    - background_luminance_edge_cv
                )
            )

        # -------------------------
        # Simplified chromatic-edge measurements
        # -------------------------

        (
            animal_chromatic_edge_mean,
            animal_chromatic_edge_sd,
            animal_chromatic_edge_cv,
        ) = calculate_chromatic_edge_metrics(
            lab_a,
            lab_b,
            animal_mask,
        )

        (
            background_chromatic_edge_mean,
            background_chromatic_edge_sd,
            background_chromatic_edge_cv,
        ) = calculate_chromatic_edge_metrics(
            lab_a,
            lab_b,
            background_ring,
        )

        if (
            np.isnan(animal_chromatic_edge_cv)
            or np.isnan(background_chromatic_edge_cv)
        ):
            chromatic_edge_cv_difference = np.nan
        else:
            chromatic_edge_cv_difference = float(
                abs(
                    animal_chromatic_edge_cv
                    - background_chromatic_edge_cv
                )
            )

        # -------------------------
        # Save one row per image
        # -------------------------

        metric_rows.append(
            {
                "species": species,
                "image_id": image_id,

                "scaled_image_path": make_project_relative_path(
                    scaled_image_path
                ),
                "animal_mask_path": make_project_relative_path(
                    animal_mask_path
                ),
                "background_ring_path": make_project_relative_path(
                    background_ring_path
                ),

                "scaled_width": rgb_image.shape[1],
                "scaled_height": rgb_image.shape[0],
                "animal_area_pixels": animal_pixels,
                "background_ring_area_pixels": background_ring_pixels,
                "scaled_image_area_pixels": image_pixels,
                "animal_area_fraction": (
                    animal_pixels / image_pixels
                ),
                "background_ring_area_fraction": (
                    background_ring_pixels / image_pixels
                ),

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
                "gray_contrast_abs": gray_contrast_abs,

                "animal_saturation_mean": animal_saturation_mean,
                "background_saturation_mean": background_saturation_mean,
                "saturation_contrast": saturation_contrast,
                "saturation_contrast_abs": saturation_contrast_abs,

                "animal_brightness_mean": animal_brightness_mean,
                "background_brightness_mean": background_brightness_mean,
                "brightness_contrast": brightness_contrast,
                "brightness_contrast_abs": brightness_contrast_abs,

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
                "background_edge_density": background_edge_density,

                "animal_luminance_edge_mean": (
                    animal_luminance_edge_mean
                ),
                "animal_luminance_edge_sd": (
                    animal_luminance_edge_sd
                ),
                "animal_luminance_edge_cv": (
                    animal_luminance_edge_cv
                ),

                "background_luminance_edge_mean": (
                    background_luminance_edge_mean
                ),
                "background_luminance_edge_sd": (
                    background_luminance_edge_sd
                ),
                "background_luminance_edge_cv": (
                    background_luminance_edge_cv
                ),

                "luminance_edge_cv_difference": (
                    luminance_edge_cv_difference
                ),

                "animal_chromatic_edge_mean": (
                    animal_chromatic_edge_mean
                ),
                "animal_chromatic_edge_sd": (
                    animal_chromatic_edge_sd
                ),
                "animal_chromatic_edge_cv": (
                    animal_chromatic_edge_cv
                ),

                "background_chromatic_edge_mean": (
                    background_chromatic_edge_mean
                ),
                "background_chromatic_edge_sd": (
                    background_chromatic_edge_sd
                ),
                "background_chromatic_edge_cv": (
                    background_chromatic_edge_cv
                ),

                "chromatic_edge_cv_difference": (
                    chromatic_edge_cv_difference
                ),
            }
        )

    metrics_df = pd.DataFrame(metric_rows)

    frozen_metrics = [
        "gray_contrast_abs",
        "saturation_contrast_abs",
        "lab_colour_distance",
        "luminance_edge_cv_difference",
        "chromatic_edge_cv_difference",
        "animal_gray_sd",
        "animal_saturation_sd",
        "animal_edge_density",
        "animal_luminance_edge_cv",
        "animal_chromatic_edge_mean",
        "animal_chromatic_edge_cv",
        "background_gray_sd",
        "background_saturation_sd",
        "background_edge_density",
        "background_luminance_edge_cv",
        "background_chromatic_edge_mean",
        "background_chromatic_edge_cv",
    ]

    missing_metric_columns = [
        metric
        for metric in frozen_metrics
        if metric not in metrics_df.columns
    ]

    if missing_metric_columns:
        raise KeyError(
            "Missing frozen metric columns: "
            + ", ".join(missing_metric_columns)
        )

    missing_values = (
        metrics_df[frozen_metrics]
        .isna()
        .sum()
    )

    metrics_df.to_csv(OUTPUT_CSV, index=False)

    print("\nFrozen 17-metric missing-value check:")
    print(missing_values.to_string())

    print("\nDone.")
    print(
        "Image-level metrics saved to: "
        f"{make_project_relative_path(OUTPUT_CSV)}"
    )

    preview_columns = [
        "species",
        "image_id",
        "gray_contrast_abs",
        "saturation_contrast_abs",
        "lab_colour_distance",
        "animal_edge_density",
        "background_edge_density",
        "animal_luminance_edge_cv",
        "background_luminance_edge_cv",
        "luminance_edge_cv_difference",
        "animal_chromatic_edge_mean",
        "background_chromatic_edge_mean",
        "animal_chromatic_edge_cv",
        "background_chromatic_edge_cv",
        "chromatic_edge_cv_difference",
    ]

    print("\nPreview:")
    print(
        metrics_df[preview_columns]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()