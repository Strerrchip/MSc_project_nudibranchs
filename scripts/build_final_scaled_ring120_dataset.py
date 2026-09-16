from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from ultralytics import SAM


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

FORMAL_SUMMARY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "sam_scaled_ring120_formal_full_summary.csv"
)

RESCUE_SELECTION_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "manual_rescue"
    / "manual_rescue_selections.csv"
)

RING_WIDTH_PX = 120

OUTPUT_NAME = "sam_scaled_ring120_final"

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

FAILED_CSV = (
    VALIDATION_OUTPUT_DIR
    / f"{OUTPUT_NAME}_failed.csv"
)


# =========================
# Helper functions
# =========================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def make_species_folder_name(species):
    return species.replace(" ", "_")


def make_project_relative_path(path):
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_project_path(path_value):
    path = Path(clean_text(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_rgb_image(image_path):
    return np.array(
        Image.open(image_path).convert("RGB")
    )


def keep_largest_component(mask):
    mask_uint8 = mask.astype(np.uint8)

    num_labels, labels, stats, _ = (
        cv2.connectedComponentsWithStats(
            mask_uint8,
            connectivity=8,
        )
    )

    if num_labels <= 1:
        return mask

    largest_label = 1 + np.argmax(
        stats[1:, cv2.CC_STAT_AREA]
    )

    return labels == largest_label


def get_sam_candidate_masks(
    model,
    image_path,
    image_shape,
):
    results = model(
        str(image_path),
        verbose=False,
    )

    if (
        len(results) == 0
        or results[0].masks is None
    ):
        return []

    masks_tensor = results[0].masks.data

    image_height, image_width = (
        image_shape[:2]
    )

    masks = []

    for i in range(
        masks_tensor.shape[0]
    ):
        mask = (
            masks_tensor[i]
            .cpu()
            .numpy()
        )

        mask = (
            mask > 0.5
        ).astype(np.uint8)

        if mask.shape != (
            image_height,
            image_width,
        ):
            mask = cv2.resize(
                mask,
                (
                    image_width,
                    image_height,
                ),
                interpolation=cv2.INTER_NEAREST,
            )

        masks.append(
            mask.astype(bool)
        )

    return masks


def score_candidate_mask(
    rgb_image,
    mask,
):
    height, width = mask.shape

    area = np.sum(mask)
    image_area = height * width
    area_fraction = area / image_area

    if (
        area_fraction < 0.03
        or area_fraction > 0.65
    ):
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
        - distance_from_centre
        / max_distance
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

    return (
        pale_score
        + 50 * centrality_score
        - 200 * border_touch_fraction
        + size_score
    )


def select_best_mask(
    rgb_image,
    candidate_masks,
):
    best_score = -1e9
    best_index = None
    best_mask = None

    for i, mask in enumerate(
        candidate_masks
    ):
        cleaned_mask = (
            keep_largest_component(
                mask
            )
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

    return float(
        sum(
            cv2.arcLength(
                contour,
                closed=True,
            )
            for contour in contours
        )
    )


def resize_image_and_mask(
    rgb_image,
    mask,
    scale_factor,
):
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
        (
            new_width,
            new_height,
        ),
        interpolation=cv2.INTER_AREA,
    )

    scaled_mask = cv2.resize(
        mask.astype(np.uint8),
        (
            new_width,
            new_height,
        ),
        interpolation=cv2.INTER_NEAREST,
    ).astype(bool)

    scaled_mask = (
        keep_largest_component(
            scaled_mask
        )
    )

    return (
        scaled_image,
        scaled_mask,
    )


def make_background_ring(
    mask,
    ring_width_px,
):
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

    return (
        (distance_from_animal > 0)
        & (
            distance_from_animal
            <= ring_width_px
        )
    )


def save_mask(
    mask,
    output_path,
):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Image.fromarray(
        mask.astype(np.uint8) * 255
    ).save(output_path)


def atomic_save_csv(
    dataframe,
    output_path,
):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        output_path.with_suffix(
            output_path.suffix + ".tmp"
        )
    )

    dataframe.to_csv(
        temporary_path,
        index=False,
    )

    temporary_path.replace(
        output_path
    )


# =========================
# Load and validate dataset
# =========================

def build_final_dataset():
    inventory = pd.read_csv(
        INVENTORY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    formal_summary = pd.read_csv(
        FORMAL_SUMMARY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    rescue = pd.read_csv(
        RESCUE_SELECTION_CSV,
        dtype=str,
        keep_default_na=False,
    )

    required_inventory = [
        "species",
        "image_slot",
        "image_id",
        "original_image_path",
        "image_downloaded",
        "usable",
    ]

    missing_inventory = [
        column
        for column in required_inventory
        if column not in inventory.columns
    ]

    if missing_inventory:
        raise KeyError(
            "image_inventory.csv is missing: "
            + ", ".join(
                missing_inventory
            )
        )

    final_inventory = inventory[
        inventory[
            "image_downloaded"
        ]
        .str.strip()
        .str.lower()
        .eq("yes")
        &
        inventory[
            "usable"
        ]
        .str.strip()
        .str.lower()
        .eq("yes")
        &
        inventory[
            "original_image_path"
        ]
        .str.strip()
        .ne("")
    ].copy()

    if len(final_inventory) != 296:
        raise ValueError(
            "Expected 296 downloaded + usable "
            f"images before final QC, found "
            f"{len(final_inventory)}."
        )

    rescue_status = (
        rescue
        .drop_duplicates(
            subset=["image_id"],
            keep="last",
        )
        .set_index("image_id")
    )

    rejected_ids = set(
        rescue_status[
            rescue_status["status"]
            .str.strip()
            .str.lower()
            .eq("rejected")
        ].index
    )

    accepted_rescue_ids = set(
        rescue_status[
            rescue_status["status"]
            .str.strip()
            .str.lower()
            .eq("accepted")
        ].index
    )

    if len(rejected_ids) != 1:
        raise ValueError(
            "Expected exactly 1 final rejected "
            f"rescue image, found "
            f"{len(rejected_ids)}."
        )

    if len(accepted_rescue_ids) != 68:
        raise ValueError(
            "Expected 68 accepted rescue images, "
            f"found "
            f"{len(accepted_rescue_ids)}."
        )

    final_inventory = final_inventory[
        ~final_inventory["image_id"]
        .isin(rejected_ids)
    ].copy()

    if len(final_inventory) != 295:
        raise ValueError(
            "Expected 295 final images after "
            f"rescue QC, found "
            f"{len(final_inventory)}."
        )

    formal_by_id = (
        formal_summary
        .drop_duplicates(
            subset=["image_id"],
            keep="last",
        )
        .set_index("image_id")
    )

    records = []

    for _, row in final_inventory.iterrows():
        image_id = clean_text(
            row["image_id"]
        )

        species = clean_text(
            row["species"]
        )

        image_slot = clean_text(
            row["image_slot"]
        )

        image_path = resolve_project_path(
            row["original_image_path"]
        )

        if image_id in accepted_rescue_ids:
            rescue_row = (
                rescue_status.loc[
                    image_id
                ]
            )

            mask_path = resolve_project_path(
                rescue_row["mask_path"]
            )

            expected_perimeter = float(
                rescue_row[
                    "animal_perimeter_original_px"
                ]
            )

            mask_source = (
                "manual_rescue"
            )

            expected_candidate_index = None
            expected_n_candidate_masks = None

        else:
            if image_id not in formal_by_id.index:
                raise KeyError(
                    "Final non-rescue image is "
                    "missing from formal summary: "
                    f"{image_id}"
                )

            formal_row = (
                formal_by_id.loc[
                    image_id
                ]
            )

            mask_path = None

            expected_perimeter = float(
                formal_row[
                    "animal_perimeter_before_scaling"
                ]
            )

            mask_source = (
                "automatic_qc_pass"
            )

            expected_candidate_index = int(
                float(
                    formal_row[
                        "selected_candidate_index"
                    ]
                )
            )

            expected_n_candidate_masks = int(
                float(
                    formal_row[
                        "n_candidate_masks"
                    ]
                )
            )

        records.append(
            {
                "species": species,
                "image_slot": image_slot,
                "image_id": image_id,
                "image_path": image_path,
                "mask_source": mask_source,
                "rescue_mask_path": mask_path,
                "expected_perimeter": (
                    expected_perimeter
                ),
                "expected_candidate_index": (
                    expected_candidate_index
                ),
                "expected_n_candidate_masks": (
                    expected_n_candidate_masks
                ),
            }
        )

    target_perimeter = float(
        np.median(
            [
                item["expected_perimeter"]
                for item in records
            ]
        )
    )

    return (
        records,
        target_perimeter,
        rejected_ids,
    )


# =========================
# Main workflow
# =========================

def main():
    for required_path in [
        MODEL_PATH,
        INVENTORY_CSV,
        FORMAL_SUMMARY_CSV,
        RESCUE_SELECTION_CSV,
    ]:
        if not required_path.exists():
            raise FileNotFoundError(
                f"Cannot find: {required_path}"
            )

    (
        final_records,
        target_perimeter,
        rejected_ids,
    ) = build_final_dataset()

    print("=" * 72)
    print("FINAL MASK + SCALING + RING BUILD")
    print("=" * 72)
    print(
        f"Final images: "
        f"{len(final_records)}"
    )
    print(
        f"Final rejected images: "
        f"{len(rejected_ids)}"
    )
    print(
        "Rejected image: "
        + ", ".join(
            sorted(rejected_ids)
        )
    )
    print(
        "Final median target perimeter: "
        f"{target_perimeter:.3f} px"
    )

    source_counts = pd.Series(
        [
            item["mask_source"]
            for item in final_records
        ]
    ).value_counts()

    print()
    print("Mask sources:")
    print(
        source_counts.to_string()
    )
    print()

    existing_summary = None

    if SUMMARY_CSV.exists():
        existing_summary = pd.read_csv(
            SUMMARY_CSV,
            dtype=str,
            keep_default_na=False,
        )

    if (
        existing_summary is None
        or len(existing_summary) == 0
    ):
        summary_rows = []
        completed_ids = set()
    else:
        summary_rows = (
            existing_summary
            .to_dict(
                orient="records"
            )
        )

        completed_ids = set(
            existing_summary[
                "image_id"
            ].astype(str)
        )

    pending_records = [
        item
        for item in final_records
        if item["image_id"]
        not in completed_ids
    ]

    print(
        f"Already completed: "
        f"{len(completed_ids)}"
    )
    print(
        f"Still pending: "
        f"{len(pending_records)}"
    )
    print()

    if not pending_records:
        print(
            "Final dataset is already complete."
        )
        return

    automatic_pending = any(
        item["mask_source"]
        == "automatic_qc_pass"
        for item in pending_records
    )

    model = None

    if automatic_pending:
        print(
            "Loading MobileSAM model..."
        )
        model = SAM(
            str(MODEL_PATH)
        )

    failed_rows = []

    for position, item in enumerate(
        pending_records,
        start=1,
    ):
        species = item["species"]
        image_slot = item[
            "image_slot"
        ]
        image_id = item[
            "image_id"
        ]
        image_path = item[
            "image_path"
        ]
        mask_source = item[
            "mask_source"
        ]

        print()
        print(
            f"[{position}/"
            f"{len(pending_records)}] "
            f"{image_id}"
        )
        print(
            f"  mask source: "
            f"{mask_source}"
        )

        try:
            if not image_path.exists():
                raise FileNotFoundError(
                    f"Missing original image: "
                    f"{image_path}"
                )

            rgb_image = (
                load_rgb_image(
                    image_path
                )
            )

            if (
                mask_source
                == "manual_rescue"
            ):
                mask_path = item[
                    "rescue_mask_path"
                ]

                if (
                    mask_path is None
                    or not mask_path.exists()
                ):
                    raise FileNotFoundError(
                        "Missing accepted rescue "
                        f"mask: {mask_path}"
                    )

                original_mask = np.array(
                    Image.open(mask_path)
                    .convert("L")
                ) > 127

                if (
                    original_mask.shape
                    != rgb_image.shape[:2]
                ):
                    raise ValueError(
                        "Rescue mask shape does "
                        "not match original image."
                    )

                candidate_index = ""
                n_candidate_masks = ""
                candidate_score = ""

            else:
                candidate_masks = (
                    get_sam_candidate_masks(
                        model,
                        image_path,
                        rgb_image.shape,
                    )
                )

                n_candidate_masks = len(
                    candidate_masks
                )

                if (
                    n_candidate_masks
                    != item[
                        "expected_n_candidate_masks"
                    ]
                ):
                    raise RuntimeError(
                        "SAM candidate count changed "
                        f"for {image_id}: "
                        f"expected "
                        f"{item['expected_n_candidate_masks']}, "
                        f"got "
                        f"{n_candidate_masks}."
                    )

                (
                    original_mask,
                    candidate_index,
                    candidate_score,
                ) = select_best_mask(
                    rgb_image,
                    candidate_masks,
                )

                if original_mask is None:
                    raise RuntimeError(
                        "Automatic mask could not "
                        "be reconstructed."
                    )

                if (
                    candidate_index
                    != item[
                        "expected_candidate_index"
                    ]
                ):
                    raise RuntimeError(
                        "Selected candidate changed "
                        f"for {image_id}: "
                        f"expected "
                        f"{item['expected_candidate_index']}, "
                        f"got "
                        f"{candidate_index}."
                    )

            original_perimeter = (
                calculate_mask_perimeter(
                    original_mask
                )
            )

            if (
                np.isnan(
                    original_perimeter
                )
                or original_perimeter <= 0
            ):
                raise RuntimeError(
                    "Invalid original mask "
                    "perimeter."
                )

            expected_perimeter = item[
                "expected_perimeter"
            ]

            perimeter_difference = abs(
                original_perimeter
                - expected_perimeter
            )

            perimeter_tolerance = max(
                5.0,
                0.01 * expected_perimeter,
            )

            if (
                perimeter_difference
                > perimeter_tolerance
            ):
                raise RuntimeError(
                    "Reconstructed perimeter "
                    "does not match the QC-approved "
                    f"mask for {image_id}. "
                    f"Expected "
                    f"{expected_perimeter:.3f}, "
                    f"got "
                    f"{original_perimeter:.3f}."
                )

            scale_factor = (
                target_perimeter
                / original_perimeter
            )

            scale_factor = min(
                scale_factor,
                1.0,
            )

            (
                scaled_image,
                scaled_mask,
            ) = resize_image_and_mask(
                rgb_image,
                original_mask,
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

            species_folder = (
                make_species_folder_name(
                    species
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

            summary_row = {
                "species": species,
                "image_slot": image_slot,
                "image_id": image_id,
                "mask_source": mask_source,
                "original_image_path": (
                    make_project_relative_path(
                        image_path
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
                    animal_area_pixels
                    / scaled_image_area_pixels
                ),
                "background_ring_area_fraction": (
                    background_ring_area_pixels
                    / scaled_image_area_pixels
                ),
                "n_candidate_masks": (
                    n_candidate_masks
                ),
                "selected_candidate_index": (
                    candidate_index
                ),
                "selected_candidate_score": (
                    candidate_score
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
            }

            summary_rows = [
                row
                for row in summary_rows
                if str(
                    row.get(
                        "image_id",
                        "",
                    )
                ) != image_id
            ]

            summary_rows.append(
                summary_row
            )

            summary_df = pd.DataFrame(
                summary_rows
            )

            summary_df = (
                summary_df
                .sort_values(
                    [
                        "species",
                        "image_slot",
                        "image_id",
                    ]
                )
                .reset_index(
                    drop=True
                )
            )

            atomic_save_csv(
                summary_df,
                SUMMARY_CSV,
            )

            print(
                "  saved final outputs"
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
                    "mask_source": mask_source,
                    "reason": str(exc),
                }
            )

            pd.DataFrame(
                failed_rows
            ).to_csv(
                FAILED_CSV,
                index=False,
            )

    final_summary = pd.read_csv(
        SUMMARY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    print()
    print("=" * 72)
    print("FINAL DATASET BUILD COMPLETE")
    print("=" * 72)
    print(
        f"Expected final images: "
        f"{len(final_records)}"
    )
    print(
        f"Saved final images: "
        f"{len(final_summary)}"
    )
    print(
        f"Failures this run: "
        f"{len(failed_rows)}"
    )
    print(
        "Final target perimeter: "
        f"{target_perimeter:.3f} px"
    )
    print()
    print("Summary saved to:")
    print(
        make_project_relative_path(
            SUMMARY_CSV
        )
    )


if __name__ == "__main__":
    main()
