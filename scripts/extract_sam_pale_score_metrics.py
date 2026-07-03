from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[1]

RING_WIDTH = 80

test_images = [
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img03.jpg",
]

base_output_dir = PROJECT_DIR / "processed_data/automated_image_analysis"

mask_dir = base_output_dir / "masks" / "sam_pale_score"
ring_dir = base_output_dir / "background_rings" / "sam_pale_score"
metrics_dir = base_output_dir / "image_metrics"

metrics_dir.mkdir(parents=True, exist_ok=True)


def read_binary_mask(mask_path):
    mask_image = Image.open(mask_path).convert("L")
    mask_array = np.array(mask_image)
    return mask_array > 0


def region_mean(values, mask):
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(values[mask]))


def region_sd(values, mask):
    if mask.sum() == 0:
        return np.nan
    return float(np.std(values[mask], ddof=1))


def edge_density_in_mask(gray_image, mask):
    if mask.sum() == 0:
        return np.nan

    edges = cv2.Canny(gray_image, threshold1=50, threshold2=150)
    edge_pixels_inside_mask = edges[mask] > 0

    return float(edge_pixels_inside_mask.sum() / mask.sum())


def extract_metrics_for_image(image_path):
    species_folder = image_path.parent.name
    species_name = species_folder.replace("_", " ")
    image_id = image_path.stem

    mask_path = (
        mask_dir
        / species_folder
        / f"{image_id}_sam_pale_score_animal_mask.png"
    )

    ring_path = (
        ring_dir
        / species_folder
        / f"{image_id}_sam_pale_score_background_ring{RING_WIDTH}.png"
    )

    if not mask_path.exists():
        raise FileNotFoundError(f"Missing animal mask: {mask_path}")

    if not ring_path.exists():
        raise FileNotFoundError(f"Missing background ring: {ring_path}")

    image_rgb = np.array(Image.open(image_path).convert("RGB"))

    animal_mask = read_binary_mask(mask_path)
    background_ring = read_binary_mask(ring_path)

    red = image_rgb[:, :, 0]
    green = image_rgb[:, :, 1]
    blue = image_rgb[:, :, 2]

    image_gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    image_hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    saturation = image_hsv[:, :, 1]
    brightness = image_hsv[:, :, 2]

    image_lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    lab_l = image_lab[:, :, 0]
    lab_a = image_lab[:, :, 1]
    lab_b = image_lab[:, :, 2]

    animal_red_mean = region_mean(red, animal_mask)
    background_red_mean = region_mean(red, background_ring)

    animal_green_mean = region_mean(green, animal_mask)
    background_green_mean = region_mean(green, background_ring)

    animal_blue_mean = region_mean(blue, animal_mask)
    background_blue_mean = region_mean(blue, background_ring)

    animal_gray_mean = region_mean(image_gray, animal_mask)
    background_gray_mean = region_mean(image_gray, background_ring)

    animal_saturation_mean = region_mean(saturation, animal_mask)
    background_saturation_mean = region_mean(saturation, background_ring)

    animal_brightness_mean = region_mean(brightness, animal_mask)
    background_brightness_mean = region_mean(brightness, background_ring)

    animal_l_mean = region_mean(lab_l, animal_mask)
    background_l_mean = region_mean(lab_l, background_ring)

    animal_a_mean = region_mean(lab_a, animal_mask)
    background_a_mean = region_mean(lab_a, background_ring)

    animal_b_mean = region_mean(lab_b, animal_mask)
    background_b_mean = region_mean(lab_b, background_ring)

    lab_colour_distance = np.sqrt(
        (animal_l_mean - background_l_mean) ** 2
        + (animal_a_mean - background_a_mean) ** 2
        + (animal_b_mean - background_b_mean) ** 2
    )

    row = {
        "species": species_name,
        "image_id": image_id,
        "segmentation_method": "sam_pale_score",
        "background_ring_width_pixels": RING_WIDTH,

        "animal_area_pixels": int(animal_mask.sum()),
        "background_ring_area_pixels": int(background_ring.sum()),

        "animal_gray_mean": animal_gray_mean,
        "background_gray_mean": background_gray_mean,
        "gray_contrast": animal_gray_mean - background_gray_mean,

        "animal_red_mean": animal_red_mean,
        "background_red_mean": background_red_mean,
        "red_contrast": animal_red_mean - background_red_mean,

        "animal_green_mean": animal_green_mean,
        "background_green_mean": background_green_mean,
        "green_contrast": animal_green_mean - background_green_mean,

        "animal_blue_mean": animal_blue_mean,
        "background_blue_mean": background_blue_mean,
        "blue_contrast": animal_blue_mean - background_blue_mean,

        "animal_saturation_mean": animal_saturation_mean,
        "background_saturation_mean": background_saturation_mean,
        "saturation_contrast": animal_saturation_mean - background_saturation_mean,

        "animal_brightness_mean": animal_brightness_mean,
        "background_brightness_mean": background_brightness_mean,
        "brightness_contrast": animal_brightness_mean - background_brightness_mean,

        "animal_l_mean": animal_l_mean,
        "background_l_mean": background_l_mean,
        "l_contrast": animal_l_mean - background_l_mean,

        "animal_a_mean": animal_a_mean,
        "background_a_mean": background_a_mean,
        "a_contrast": animal_a_mean - background_a_mean,

        "animal_b_mean": animal_b_mean,
        "background_b_mean": background_b_mean,
        "b_contrast": animal_b_mean - background_b_mean,

        "lab_colour_distance": lab_colour_distance,

        "animal_brightness_sd": region_sd(brightness, animal_mask),
        "animal_saturation_sd": region_sd(saturation, animal_mask),
        "animal_gray_sd": region_sd(image_gray, animal_mask),

        "background_brightness_sd": region_sd(brightness, background_ring),
        "background_saturation_sd": region_sd(saturation, background_ring),
        "background_gray_sd": region_sd(image_gray, background_ring),

        "animal_edge_density": edge_density_in_mask(image_gray, animal_mask),

        "notes": "SAM pale-score segmentation; background ring generated by mask dilation",
    }

    return row


def main():
    rows = []

    print("Extracting image metrics from SAM pale-score masks...\n")

    for image_path in test_images:
        if image_path.exists():
            print(f"Processing: {image_path.name}")
            row = extract_metrics_for_image(image_path)
            rows.append(row)
        else:
            print(f"Missing image: {image_path}")

    metrics = pd.DataFrame(rows)

    numeric_cols = metrics.select_dtypes(include=["float64", "float32"]).columns
    metrics[numeric_cols] = metrics[numeric_cols].round(3)

    output_path = metrics_dir / "sam_pale_score_image_metrics_pilot.csv"
    metrics.to_csv(output_path, index=False)

    print("\nSaved SAM image metrics CSV to:")
    print(output_path)

    print("\nPreview:")
    preview_cols = [
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

    print(metrics[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()