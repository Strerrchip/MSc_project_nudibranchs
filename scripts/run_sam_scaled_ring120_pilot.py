from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from ultralytics import SAM
import matplotlib.pyplot as plt


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "mobile_sam.pt"

RING_WIDTH_PX = 120

OUTPUT_NAME = "sam_scaled_ring120"

MASK_OUTPUT_DIR = PROJECT_ROOT / "processed_data" / "automated_image_analysis" / "masks" / OUTPUT_NAME
RING_OUTPUT_DIR = PROJECT_ROOT / "processed_data" / "automated_image_analysis" / "background_rings" / OUTPUT_NAME
SCALED_IMAGE_OUTPUT_DIR = PROJECT_ROOT / "processed_data" / "automated_image_analysis" / "scaled_images" / OUTPUT_NAME
QC_OUTPUT_DIR = PROJECT_ROOT / "processed_data" / "automated_image_analysis" / "qc_figures" / OUTPUT_NAME
VALIDATION_OUTPUT_DIR = PROJECT_ROOT / "processed_data" / "automated_image_analysis" / "validation"

SUMMARY_CSV = VALIDATION_OUTPUT_DIR / "sam_scaled_ring120_pilot_summary.csv"


# These are the five pilot images used for testing the updated workflow.
TEST_IMAGES = [
    {
        "species": "Aphelodoris varia",
        "image_id": "Aphelodoris_varia_img01",
        "path": PROJECT_ROOT / "raw_data" / "pilot_images" / "imagej_test" / "Aphelodoris_varia" / "Aphelodoris_varia_img01.jpg",
    },
    {
        "species": "Aphelodoris varia",
        "image_id": "Aphelodoris_varia_img02",
        "path": PROJECT_ROOT / "raw_data" / "pilot_images" / "imagej_test" / "Aphelodoris_varia" / "Aphelodoris_varia_img02.jpg",
    },
    {
        "species": "Doriprismatica atromarginata",
        "image_id": "Doriprismatica_atromarginata_img01",
        "path": PROJECT_ROOT / "raw_data" / "pilot_images" / "imagej_test" / "Doriprismatica_atromarginata" / "Doriprismatica_atromarginata_img01.jpg",
    },
    {
        "species": "Doriprismatica atromarginata",
        "image_id": "Doriprismatica_atromarginata_img02",
        "path": PROJECT_ROOT / "raw_data" / "pilot_images" / "imagej_test" / "Doriprismatica_atromarginata" / "Doriprismatica_atromarginata_img02.jpg",
    },
    {
        "species": "Doriprismatica atromarginata",
        "image_id": "Doriprismatica_atromarginata_img03",
        "path": PROJECT_ROOT / "raw_data" / "pilot_images" / "imagej_test" / "Doriprismatica_atromarginata" / "Doriprismatica_atromarginata_img03.jpg",
    },
]


# =========================
# Helper functions
# =========================

def make_species_folder_name(species):
    """Convert species name to a folder-friendly name."""
    return species.replace(" ", "_")


def load_rgb_image(image_path):
    """Read an image as RGB."""
    image = Image.open(image_path).convert("RGB")
    return np.array(image)


def make_project_relative_path(path):
    """Convert an absolute path to a path relative to the project folder."""
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def get_sam_candidate_masks(model, image_path, image_shape):
    """Run SAM and return candidate masks as boolean arrays."""
    results = model(str(image_path))

    if len(results) == 0 or results[0].masks is None:
        return []

    masks_tensor = results[0].masks.data

    masks = []
    image_height, image_width = image_shape[:2]

    for i in range(masks_tensor.shape[0]):
        mask = masks_tensor[i].cpu().numpy()
        mask = (mask > 0.5).astype(np.uint8)

        if mask.shape != (image_height, image_width):
            mask = cv2.resize(
                mask,
                (image_width, image_height),
                interpolation=cv2.INTER_NEAREST,
            )

        masks.append(mask.astype(bool))

    return masks


def keep_largest_component(mask):
    """Keep only the largest connected component in a mask."""
    mask_uint8 = mask.astype(np.uint8)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask_uint8,
        connectivity=8,
    )

    if num_labels <= 1:
        return mask

    largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    cleaned = labels == largest_label

    return cleaned


def score_candidate_mask(rgb_image, mask):
    """
    Score a SAM candidate mask.

    This scoring rule is mainly for the current pale / white pilot species.
    It favours masks that are:
    - large enough to represent the whole animal
    - close to the image centre
    - not strongly touching the image border
    - bright and not highly saturated

    Very small masks are rejected, because they often represent only part of
    the animal rather than the whole animal.
    """
    height, width = mask.shape
    area = np.sum(mask)
    image_area = height * width
    area_fraction = area / image_area

    # Reject masks that are clearly too small or too large.
    if area_fraction < 0.03 or area_fraction > 0.65:
        return -1e9

    ys, xs = np.where(mask)

    if len(xs) == 0:
        return -1e9

    centroid_x = np.mean(xs)
    centroid_y = np.mean(ys)

    centre_x = width / 2
    centre_y = height / 2

    distance_from_centre = np.sqrt(
        (centroid_x - centre_x) ** 2 + (centroid_y - centre_y) ** 2
    )
    max_distance = np.sqrt(centre_x ** 2 + centre_y ** 2)
    centrality_score = 1 - (distance_from_centre / max_distance)

    border_width = 5
    border_mask = np.zeros_like(mask, dtype=bool)
    border_mask[:border_width, :] = True
    border_mask[-border_width:, :] = True
    border_mask[:, :border_width] = True
    border_mask[:, -border_width:] = True

    border_touch_fraction = np.sum(mask & border_mask) / area

    hsv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)
    saturation = hsv_image[:, :, 1]
    brightness = hsv_image[:, :, 2]

    mean_saturation = np.mean(saturation[mask])
    mean_brightness = np.mean(brightness[mask])

    pale_score = mean_brightness - 0.6 * mean_saturation

    # Prefer a whole-animal mask, not a small internal patch.
    preferred_area_fraction = 0.18
    size_score = -abs(area_fraction - preferred_area_fraction) * 350

    score = (
        pale_score
        + 50 * centrality_score
        - 200 * border_touch_fraction
        + size_score
    )

    return score


def select_best_mask(rgb_image, candidate_masks):
    """Select the best SAM candidate mask using the scoring rule."""
    best_score = -1e9
    best_index = None
    best_mask = None

    for i, mask in enumerate(candidate_masks):
        cleaned_mask = keep_largest_component(mask)
        score = score_candidate_mask(rgb_image, cleaned_mask)

        if score > best_score:
            best_score = score
            best_index = i
            best_mask = cleaned_mask

    return best_mask, best_index, best_score


def calculate_mask_perimeter(mask):
    """Calculate animal mask perimeter in pixels."""
    mask_uint8 = mask.astype(np.uint8) * 255
    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if len(contours) == 0:
        return np.nan

    perimeter = sum(cv2.arcLength(contour, closed=True) for contour in contours)
    return perimeter


def resize_image_and_mask(rgb_image, mask, scale_factor):
    """Resize image and mask using the same scale factor."""
    original_height, original_width = rgb_image.shape[:2]

    new_width = max(1, int(round(original_width * scale_factor)))
    new_height = max(1, int(round(original_height * scale_factor)))

    resized_image = cv2.resize(
        rgb_image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )

    resized_mask = cv2.resize(
        mask.astype(np.uint8),
        (new_width, new_height),
        interpolation=cv2.INTER_NEAREST,
    ).astype(bool)

    resized_mask = keep_largest_component(resized_mask)

    return resized_image, resized_mask


def make_background_ring(mask, ring_width_px):
    """
    Create a surrounding background ring.

    The ring is made from pixels outside the animal mask that are within
    ring_width_px pixels of the animal boundary.
    """
    mask_uint8 = mask.astype(np.uint8)
    outside_animal = 1 - mask_uint8

    distance_from_animal = cv2.distanceTransform(
        outside_animal,
        distanceType=cv2.DIST_L2,
        maskSize=5,
    )

    ring = (distance_from_animal > 0) & (distance_from_animal <= ring_width_px)

    return ring


def save_mask(mask, output_path):
    """Save a boolean mask as a black-and-white PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask_image = mask.astype(np.uint8) * 255
    Image.fromarray(mask_image).save(output_path)


def save_qc_figure(
    rgb_image,
    animal_mask,
    background_ring,
    output_path,
    title,
):
    """Save a QC figure showing image, animal mask and background ring."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_for_overlay = rgb_image.copy()

    animal_overlay = image_for_overlay.copy()
    animal_overlay[animal_mask] = [255, 0, 0]

    ring_overlay = image_for_overlay.copy()
    ring_overlay[background_ring] = [0, 255, 0]

    combined_overlay = image_for_overlay.copy()
    combined_overlay[background_ring] = [0, 255, 0]
    combined_overlay[animal_mask] = [255, 0, 0]

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))

    axes[0].imshow(rgb_image)
    axes[0].set_title("Scaled image")

    axes[1].imshow(animal_overlay)
    axes[1].set_title("Animal mask")

    axes[2].imshow(ring_overlay)
    axes[2].set_title("120 px background ring")

    axes[3].imshow(combined_overlay)
    axes[3].set_title("Mask + ring")

    for ax in axes:
        ax.axis("off")

    fig.suptitle(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close(fig)


# =========================
# Main workflow
# =========================

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Cannot find SAM model file: {MODEL_PATH}")

    VALIDATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading SAM model...")
    model = SAM(str(MODEL_PATH))

    print("Running SAM on pilot images...")

    segmented_images = []

    for item in TEST_IMAGES:
        species = item["species"]
        image_id = item["image_id"]
        image_path = item["path"]

        print(f"\nProcessing: {image_id}")

        if not image_path.exists():
            print(f"  MISSING IMAGE: {image_path}")
            continue

        rgb_image = load_rgb_image(image_path)
        candidate_masks = get_sam_candidate_masks(model, image_path, rgb_image.shape)

        print(f"  Number of SAM candidate masks: {len(candidate_masks)}")

        if len(candidate_masks) == 0:
            print("  No masks found.")
            continue

        best_mask, best_index, best_score = select_best_mask(rgb_image, candidate_masks)

        if best_mask is None:
            print("  No suitable mask selected.")
            continue

        animal_perimeter = calculate_mask_perimeter(best_mask)

        print(f"  Selected candidate: {best_index}")
        print(f"  Candidate score: {best_score:.3f}")
        print(f"  Animal perimeter before scaling: {animal_perimeter:.3f} px")

        segmented_images.append(
            {
                "species": species,
                "species_folder": make_species_folder_name(species),
                "image_id": image_id,
                "image_path": image_path,
                "rgb_image": rgb_image,
                "animal_mask": best_mask,
                "animal_perimeter_before_scaling": animal_perimeter,
                "selected_candidate_index": best_index,
                "selected_candidate_score": best_score,
                "n_candidate_masks": len(candidate_masks),
            }
        )

    if len(segmented_images) == 0:
        raise RuntimeError("No images were successfully segmented.")

    # The target perimeter is set to the median successful animal perimeter.
    # This avoids making the target size too small.
    successful_perimeters = [
        item["animal_perimeter_before_scaling"]
        for item in segmented_images
        if not np.isnan(item["animal_perimeter_before_scaling"])
    ]

    target_perimeter = float(np.median(successful_perimeters))

    print("\n=========================")
    print(f"Target animal perimeter for this pilot: {target_perimeter:.3f} px")
    print("=========================\n")

    summary_rows = []

    for item in segmented_images:
        species = item["species"]
        species_folder = item["species_folder"]
        image_id = item["image_id"]
        rgb_image = item["rgb_image"]
        animal_mask = item["animal_mask"]
        original_perimeter = item["animal_perimeter_before_scaling"]

        scale_factor = target_perimeter / original_perimeter

        # This pilot only scales images down. Images smaller than the target are kept at original size.
        scale_factor = min(scale_factor, 1.0)

        scaled_image, scaled_mask = resize_image_and_mask(
            rgb_image,
            animal_mask,
            scale_factor,
        )

        scaled_perimeter = calculate_mask_perimeter(scaled_mask)

        background_ring = make_background_ring(scaled_mask, RING_WIDTH_PX)

        scaled_image_output_path = SCALED_IMAGE_OUTPUT_DIR / species_folder / f"{image_id}_{OUTPUT_NAME}_scaled_image.png"
        mask_output_path = MASK_OUTPUT_DIR / species_folder / f"{image_id}_{OUTPUT_NAME}_animal_mask.png"
        ring_output_path = RING_OUTPUT_DIR / species_folder / f"{image_id}_{OUTPUT_NAME}_background_ring120.png"
        qc_output_path = QC_OUTPUT_DIR / species_folder / f"{image_id}_{OUTPUT_NAME}_qc.png"

        scaled_image_output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(scaled_image).save(scaled_image_output_path)

        save_mask(scaled_mask, mask_output_path)
        save_mask(background_ring, ring_output_path)

        qc_title = (
            f"{image_id}\n"
            f"scale factor = {scale_factor:.3f}, "
            f"perimeter after scaling = {scaled_perimeter:.1f} px"
        )

        save_qc_figure(
            scaled_image,
            scaled_mask,
            background_ring,
            qc_output_path,
            qc_title,
        )

        animal_area_pixels = int(np.sum(scaled_mask))
        background_ring_area_pixels = int(np.sum(background_ring))
        scaled_image_area_pixels = int(scaled_image.shape[0] * scaled_image.shape[1])

        animal_area_fraction = animal_area_pixels / scaled_image_area_pixels
        background_ring_area_fraction = background_ring_area_pixels / scaled_image_area_pixels

        summary_rows.append(
            {
                "species": species,
                "image_id": image_id,
                "original_image_path": make_project_relative_path(item["image_path"]),
                "original_width": rgb_image.shape[1],
                "original_height": rgb_image.shape[0],
                "animal_perimeter_before_scaling": original_perimeter,
                "target_animal_perimeter": target_perimeter,
                "scale_factor": scale_factor,
                "scaled_width": scaled_image.shape[1],
                "scaled_height": scaled_image.shape[0],
                "animal_perimeter_after_scaling": scaled_perimeter,
                "ring_width_px": RING_WIDTH_PX,
                "animal_area_pixels": animal_area_pixels,
                "background_ring_area_pixels": background_ring_area_pixels,
                "scaled_image_area_pixels": scaled_image_area_pixels,
                "animal_area_fraction": animal_area_fraction,
                "background_ring_area_fraction": background_ring_area_fraction,
                "n_candidate_masks": item["n_candidate_masks"],
                "selected_candidate_index": item["selected_candidate_index"],
                "selected_candidate_score": item["selected_candidate_score"],
                "scaled_image_output_path": make_project_relative_path(scaled_image_output_path),
                "mask_output_path": make_project_relative_path(mask_output_path),
                "background_ring_output_path": make_project_relative_path(ring_output_path),
                "qc_output_path": make_project_relative_path(qc_output_path),
            }
        )

        print(f"Saved outputs for {image_id}")
        print(f"  scale factor: {scale_factor:.3f}")
        print(f"  perimeter after scaling: {scaled_perimeter:.3f} px")
        print(f"  animal area: {animal_area_pixels} pixels")
        print(f"  background ring area: {background_ring_area_pixels} pixels")
        print(f"  animal area fraction: {animal_area_fraction:.3f}")
        print(f"  background ring area fraction: {background_ring_area_fraction:.3f}")

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    print("\nDone.")
    print(f"Summary saved to: {make_project_relative_path(SUMMARY_CSV)}")
    print(f"Scaled images saved to: {make_project_relative_path(SCALED_IMAGE_OUTPUT_DIR)}")
    print(f"QC figures saved to: {make_project_relative_path(QC_OUTPUT_DIR)}")


if __name__ == "__main__":
    main()