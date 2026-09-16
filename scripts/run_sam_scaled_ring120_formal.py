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

INVENTORY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "image_inventory.csv"
)

RING_WIDTH_PX = 120

OUTPUT_NAME = "sam_scaled_ring120_formal_full"

MASK_OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "masks"
    / OUTPUT_NAME
)

RING_OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "background_rings"
    / OUTPUT_NAME
)

SCALED_IMAGE_OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "scaled_images"
    / OUTPUT_NAME
)

QC_OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "qc_figures"
    / OUTPUT_NAME
)

VALIDATION_OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
)

SUMMARY_CSV = (
    VALIDATION_OUTPUT_DIR
    / f"{OUTPUT_NAME}_summary.csv"
)


# =========================
# Helper functions
# =========================

def clean_text(value):
    """Convert a value to a clean string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def make_species_folder_name(species):
    """Convert species name to a folder-friendly name."""
    return species.replace(" ", "_")


def make_image_id(species, image_slot):
    """Create the standard image identifier."""
    species_folder = make_species_folder_name(species)
    return f"{species_folder}_{image_slot}"


def load_rgb_image(image_path):
    """Read an image as RGB."""
    image = Image.open(image_path).convert("RGB")
    return np.array(image)


def make_project_relative_path(path):
    """Convert an absolute path to a project-relative path."""
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

    largest_label = 1 + np.argmax(
        stats[1:, cv2.CC_STAT_AREA]
    )

    cleaned = labels == largest_label

    return cleaned


def score_candidate_mask(rgb_image, mask):
    """
    Score a SAM candidate mask.

    This keeps the same selection rule used in the validated pilot workflow.
    The formal run is used to test whether this fixed rule continues to
    identify the animal correctly across the expanded image set.
    """
    height, width = mask.shape

    area = np.sum(mask)
    image_area = height * width
    area_fraction = area / image_area

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
        (centroid_x - centre_x) ** 2
        + (centroid_y - centre_y) ** 2
    )

    max_distance = np.sqrt(
        centre_x ** 2
        + centre_y ** 2
    )

    centrality_score = (
        1
        - distance_from_centre / max_distance
    )

    border_width = 5

    border_mask = np.zeros_like(
        mask,
        dtype=bool,
    )

    border_mask[:border_width, :] = True
    border_mask[-border_width:, :] = True
    border_mask[:, :border_width] = True
    border_mask[:, -border_width:] = True

    border_touch_fraction = (
        np.sum(mask & border_mask)
        / area
    )

    hsv_image = cv2.cvtColor(
        rgb_image,
        cv2.COLOR_RGB2HSV,
    )

    saturation = hsv_image[:, :, 1]
    brightness = hsv_image[:, :, 2]

    mean_saturation = np.mean(
        saturation[mask]
    )

    mean_brightness = np.mean(
        brightness[mask]
    )

    pale_score = (
        mean_brightness
        - 0.6 * mean_saturation
    )

    preferred_area_fraction = 0.18

    size_score = (
        -abs(
            area_fraction
            - preferred_area_fraction
        )
        * 350
    )

    score = (
        pale_score
        + 50 * centrality_score
        - 200 * border_touch_fraction
        + size_score
    )

    return score


def select_best_mask(
    rgb_image,
    candidate_masks,
):
    """Select the best SAM candidate mask using the fixed scoring rule."""

    best_score = -1e9
    best_index = None
    best_mask = None

    for i, mask in enumerate(candidate_masks):

        cleaned_mask = keep_largest_component(
            mask
        )

        score = score_candidate_mask(
            rgb_image,
            cleaned_mask,
        )

        if score > best_score:

            best_score = score
            best_index = i
            best_mask = cleaned_mask

    return (
        best_mask,
        best_index,
        best_score,
    )


def calculate_mask_perimeter(mask):
    """Calculate animal mask perimeter in pixels."""

    mask_uint8 = (
        mask.astype(np.uint8)
        * 255
    )

    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if len(contours) == 0:
        return np.nan

    perimeter = sum(
        cv2.arcLength(
            contour,
            closed=True,
        )
        for contour in contours
    )

    return perimeter


def resize_image_and_mask(
    rgb_image,
    mask,
    scale_factor,
):
    """Resize image and mask using the same scale factor."""

    original_height, original_width = (
        rgb_image.shape[:2]
    )

    new_width = max(
        1,
        int(
            round(
                original_width
                * scale_factor
            )
        ),
    )

    new_height = max(
        1,
        int(
            round(
                original_height
                * scale_factor
            )
        ),
    )

    scaled_image = cv2.resize(
        rgb_image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )

    scaled_mask = cv2.resize(
        mask.astype(np.uint8),
        (new_width, new_height),
        interpolation=cv2.INTER_NEAREST,
    ).astype(bool)

    scaled_mask = keep_largest_component(
        scaled_mask
    )

    return scaled_image, scaled_mask


def make_background_ring(
    mask,
    ring_width_px,
):
    """Create the immediate background ring."""

    mask_uint8 = mask.astype(np.uint8)

    outside_animal = (
        1 - mask_uint8
    )

    distance_from_animal = (
        cv2.distanceTransform(
            outside_animal,
            distanceType=cv2.DIST_L2,
            maskSize=5,
        )
    )

    ring = (
        (distance_from_animal > 0)
        & (
            distance_from_animal
            <= ring_width_px
        )
    )

    return ring


def save_mask(
    mask,
    output_path,
):
    """Save a boolean mask as a black-and-white PNG."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mask_image = (
        mask.astype(np.uint8)
        * 255
    )

    Image.fromarray(
        mask_image
    ).save(
        output_path
    )


def save_qc_figure(
    rgb_image,
    animal_mask,
    background_ring,
    output_path,
    title,
):
    """Save QC figure for the formal segmentation run."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_for_overlay = (
        rgb_image.copy()
    )

    animal_overlay = (
        image_for_overlay.copy()
    )

    animal_overlay[
        animal_mask
    ] = [255, 0, 0]

    ring_overlay = (
        image_for_overlay.copy()
    )

    ring_overlay[
        background_ring
    ] = [0, 255, 0]

    combined_overlay = (
        image_for_overlay.copy()
    )

    combined_overlay[
        background_ring
    ] = [0, 255, 0]

    combined_overlay[
        animal_mask
    ] = [255, 0, 0]

    fig, axes = plt.subplots(
        1,
        4,
        figsize=(16, 4),
    )

    axes[0].imshow(rgb_image)
    axes[0].set_title(
        "Scaled image"
    )

    axes[1].imshow(
        animal_overlay
    )
    axes[1].set_title(
        "Animal mask"
    )

    axes[2].imshow(
        ring_overlay
    )
    axes[2].set_title(
        "120 px background ring"
    )

    axes[3].imshow(
        combined_overlay
    )
    axes[3].set_title(
        "Mask + ring"
    )

    for ax in axes:
        ax.axis("off")

    fig.suptitle(title)

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=200,
    )

    plt.close(fig)


def load_formal_images():
    """
    Load all downloaded and usable images listed in image_inventory.csv.

    Only images with image_downloaded == "yes", usable == "yes", and a
    non-empty original_image_path are included in the formal analysis.
    """

    if not INVENTORY_CSV.exists():

        raise FileNotFoundError(
            f"Cannot find inventory: "
            f"{INVENTORY_CSV}"
        )

    inventory = pd.read_csv(
        INVENTORY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    required_columns = [
        "species",
        "image_slot",
        "image_id",
        "original_image_path",
        "image_downloaded",
        "usable",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in inventory.columns
    ]

    if missing_columns:

        raise KeyError(
            "image_inventory.csv is missing: "
            + ", ".join(
                missing_columns
            )
        )

    inventory = inventory[
        inventory[
            "image_downloaded"
        ]
        .str.strip()
        .str.lower()
        .eq("yes")
    ].copy()

    inventory = inventory[
        inventory[
            "usable"
        ]
        .str.strip()
        .str.lower()
        .eq("yes")
    ].copy()

    inventory = inventory[
        inventory[
            "original_image_path"
        ]
        .str.strip()
        .ne("")
    ].copy()

    images = []

    for _, row in inventory.iterrows():

        species = clean_text(
            row["species"]
        )

        image_slot = clean_text(
            row["image_slot"]
        )

        relative_path = clean_text(
            row["original_image_path"]
        )

        image_path = (
            PROJECT_ROOT
            / Path(relative_path)
        )

        image_id = clean_text(
            row["image_id"]
        )

        images.append(
            {
                "species": species,
                "image_slot": image_slot,
                "image_id": image_id,
                "path": image_path,
            }
        )

    return images


# =========================
# Main workflow
# =========================

def main():

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Cannot find SAM model file: "
            f"{MODEL_PATH}"
        )

    VALIDATION_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    formal_images = (
        load_formal_images()
    )

    print(
        f"Images selected from inventory: "
        f"{len(formal_images)}"
    )

    species_counts = {}

    for item in formal_images:

        species = item["species"]

        species_counts[species] = (
            species_counts.get(
                species,
                0,
            )
            + 1
        )

    print()

    print("Images per species:")

    for species, count in sorted(
        species_counts.items()
    ):
        print(
            f"  {species}: {count}"
        )

    print()

    missing_images = [
        item
        for item in formal_images
        if not item["path"].exists()
    ]

    if missing_images:

        print(
            "Missing image files:"
        )

        for item in missing_images:

            print(
                f"  {item['image_id']}: "
                f"{item['path']}"
            )

        raise FileNotFoundError(
            "Some downloaded images listed "
            "in the inventory are missing."
        )

    print(
        "Loading SAM model..."
    )

    model = SAM(
        str(MODEL_PATH)
    )

    print(
        "Running SAM on formal images..."
    )

    segmented_images = []

    failed_rows = []

    for item in formal_images:

        species = item["species"]
        image_slot = item["image_slot"]
        image_id = item["image_id"]
        image_path = item["path"]

        print()
        print(
            f"Processing: {image_id}"
        )

        try:

            rgb_image = (
                load_rgb_image(
                    image_path
                )
            )

            candidate_masks = (
                get_sam_candidate_masks(
                    model,
                    image_path,
                    rgb_image.shape,
                )
            )

            print(
                "  Number of SAM "
                f"candidate masks: "
                f"{len(candidate_masks)}"
            )

            if len(candidate_masks) == 0:

                print(
                    "  No masks found."
                )

                failed_rows.append(
                    {
                        "species": species,
                        "image_slot": image_slot,
                        "image_id": image_id,
                        "reason": (
                            "no_candidate_masks"
                        ),
                    }
                )

                continue

            (
                best_mask,
                best_index,
                best_score,
            ) = select_best_mask(
                rgb_image,
                candidate_masks,
            )

            if best_mask is None:

                print(
                    "  No suitable mask selected."
                )

                failed_rows.append(
                    {
                        "species": species,
                        "image_slot": image_slot,
                        "image_id": image_id,
                        "reason": (
                            "no_suitable_mask"
                        ),
                    }
                )

                continue

            animal_perimeter = (
                calculate_mask_perimeter(
                    best_mask
                )
            )

            if (
                np.isnan(
                    animal_perimeter
                )
                or animal_perimeter <= 0
            ):

                print(
                    "  Invalid animal perimeter."
                )

                failed_rows.append(
                    {
                        "species": species,
                        "image_slot": image_slot,
                        "image_id": image_id,
                        "reason": (
                            "invalid_perimeter"
                        ),
                    }
                )

                continue

            print(
                f"  Selected candidate: "
                f"{best_index}"
            )

            print(
                f"  Candidate score: "
                f"{best_score:.3f}"
            )

            print(
                "  Animal perimeter before "
                f"scaling: "
                f"{animal_perimeter:.3f} px"
            )

            segmented_images.append(
                {
                    "species": species,
                    "image_slot": image_slot,
                    "species_folder": (
                        make_species_folder_name(
                            species
                        )
                    ),
                    "image_id": image_id,
                    "image_path": image_path,
                    "rgb_image": rgb_image,
                    "animal_mask": best_mask,
                    "animal_perimeter_before_scaling": (
                        animal_perimeter
                    ),
                    "selected_candidate_index": (
                        best_index
                    ),
                    "selected_candidate_score": (
                        best_score
                    ),
                    "n_candidate_masks": len(
                        candidate_masks
                    ),
                }
            )

        except Exception as exc:

            print(
                f"  FAILED: {exc}"
            )

            failed_rows.append(
                {
                    "species": species,
                    "image_slot": image_slot,
                    "image_id": image_id,
                    "reason": str(exc),
                }
            )

    if len(segmented_images) == 0:

        raise RuntimeError(
            "No images were successfully "
            "segmented."
        )

    successful_perimeters = [
        item[
            "animal_perimeter_before_scaling"
        ]
        for item in segmented_images
    ]

    target_perimeter = float(
        np.median(
            successful_perimeters
        )
    )

    print()
    print("=" * 72)

    print(
        "Target animal perimeter for "
        f"formal dataset: "
        f"{target_perimeter:.3f} px"
    )

    print("=" * 72)
    print()

    summary_rows = []

    for item in segmented_images:

        species = item["species"]

        species_folder = (
            item["species_folder"]
        )

        image_slot = item["image_slot"]

        image_id = item["image_id"]

        rgb_image = item[
            "rgb_image"
        ]

        animal_mask = item[
            "animal_mask"
        ]

        original_perimeter = item[
            "animal_perimeter_before_scaling"
        ]

        scale_factor = (
            target_perimeter
            / original_perimeter
        )

        # Keep the validated pilot rule:
        # images are only scaled down.
        scale_factor = min(
            scale_factor,
            1.0,
        )

        (
            scaled_image,
            scaled_mask,
        ) = resize_image_and_mask(
            rgb_image,
            animal_mask,
            scale_factor,
        )

        scaled_perimeter = (
            calculate_mask_perimeter(
                scaled_mask
            )
        )

        background_ring = (
            make_background_ring(
                scaled_mask,
                RING_WIDTH_PX,
            )
        )

        scaled_image_output_path = (
            SCALED_IMAGE_OUTPUT_DIR
            / species_folder
            / (
                f"{image_id}_"
                f"{OUTPUT_NAME}_"
                "scaled_image.png"
            )
        )

        mask_output_path = (
            MASK_OUTPUT_DIR
            / species_folder
            / (
                f"{image_id}_"
                f"{OUTPUT_NAME}_"
                "animal_mask.png"
            )
        )

        ring_output_path = (
            RING_OUTPUT_DIR
            / species_folder
            / (
                f"{image_id}_"
                f"{OUTPUT_NAME}_"
                "background_ring120.png"
            )
        )

        qc_output_path = (
            QC_OUTPUT_DIR
            / species_folder
            / (
                f"{image_id}_"
                f"{OUTPUT_NAME}_qc.png"
            )
        )

        scaled_image_output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        Image.fromarray(
            scaled_image
        ).save(
            scaled_image_output_path
        )

        save_mask(
            scaled_mask,
            mask_output_path,
        )

        save_mask(
            background_ring,
            ring_output_path,
        )

        qc_title = (
            f"{image_id}\n"
            f"scale factor = "
            f"{scale_factor:.3f}, "
            f"perimeter after scaling = "
            f"{scaled_perimeter:.1f} px"
        )

        save_qc_figure(
            scaled_image,
            scaled_mask,
            background_ring,
            qc_output_path,
            qc_title,
        )

        animal_area_pixels = int(
            np.sum(
                scaled_mask
            )
        )

        background_ring_area_pixels = int(
            np.sum(
                background_ring
            )
        )

        scaled_image_area_pixels = int(
            scaled_image.shape[0]
            * scaled_image.shape[1]
        )

        animal_area_fraction = (
            animal_area_pixels
            / scaled_image_area_pixels
        )

        background_ring_area_fraction = (
            background_ring_area_pixels
            / scaled_image_area_pixels
        )

        summary_rows.append(
            {
                "species": species,
                "image_slot": image_slot,
                "image_id": image_id,
                "original_image_path": (
                    make_project_relative_path(
                        item["image_path"]
                    )
                ),
                "original_width": (
                    rgb_image.shape[1]
                ),
                "original_height": (
                    rgb_image.shape[0]
                ),
                "animal_perimeter_before_scaling": (
                    original_perimeter
                ),
                "target_animal_perimeter": (
                    target_perimeter
                ),
                "scale_factor": (
                    scale_factor
                ),
                "scaled_width": (
                    scaled_image.shape[1]
                ),
                "scaled_height": (
                    scaled_image.shape[0]
                ),
                "animal_perimeter_after_scaling": (
                    scaled_perimeter
                ),
                "ring_width_px": (
                    RING_WIDTH_PX
                ),
                "animal_area_pixels": (
                    animal_area_pixels
                ),
                "background_ring_area_pixels": (
                    background_ring_area_pixels
                ),
                "scaled_image_area_pixels": (
                    scaled_image_area_pixels
                ),
                "animal_area_fraction": (
                    animal_area_fraction
                ),
                "background_ring_area_fraction": (
                    background_ring_area_fraction
                ),
                "n_candidate_masks": (
                    item[
                        "n_candidate_masks"
                    ]
                ),
                "selected_candidate_index": (
                    item[
                        "selected_candidate_index"
                    ]
                ),
                "selected_candidate_score": (
                    item[
                        "selected_candidate_score"
                    ]
                ),
                "scaled_image_output_path": (
                    make_project_relative_path(
                        scaled_image_output_path
                    )
                ),
                "mask_output_path": (
                    make_project_relative_path(
                        mask_output_path
                    )
                ),
                "background_ring_output_path": (
                    make_project_relative_path(
                        ring_output_path
                    )
                ),
                "qc_output_path": (
                    make_project_relative_path(
                        qc_output_path
                    )
                ),
            }
        )

        print(
            f"Saved outputs for "
            f"{image_id}"
        )

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_df.to_csv(
        SUMMARY_CSV,
        index=False,
    )

    if failed_rows:

        failed_csv = (
            VALIDATION_OUTPUT_DIR
            / f"{OUTPUT_NAME}_failed.csv"
        )

        pd.DataFrame(
            failed_rows
        ).to_csv(
            failed_csv,
            index=False,
        )

    print()
    print("=" * 72)
    print("FORMAL SAM RUN COMPLETE")
    print("=" * 72)

    print(
        f"Images requested: "
        f"{len(formal_images)}"
    )

    print(
        f"Successfully segmented: "
        f"{len(summary_rows)}"
    )

    print(
        f"Failed: "
        f"{len(failed_rows)}"
    )

    print()

    print(
        "Summary saved to:"
    )

    print(
        make_project_relative_path(
            SUMMARY_CSV
        )
    )

    print()

    print(
        "QC figures saved to:"
    )

    print(
        make_project_relative_path(
            QC_OUTPUT_DIR
        )
    )


if __name__ == "__main__":
    main()