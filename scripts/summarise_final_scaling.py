from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# File paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
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
    / "validation"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "final_scaling_methods_summary.csv"
)

SUMMARY_TXT = (
    OUTPUT_DIR
    / "final_scaling_methods_summary.txt"
)


# ============================================================
# Expected final dataset values
# ============================================================

EXPECTED_FINAL_IMAGES = 295
EXPECTED_SPECIES = 30

# A total of 296 images entered automatic processing.
EXPECTED_INITIAL_IMAGES = 296


# ============================================================
# Main workflow
# ============================================================

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find final scaling summary: "
            f"{INPUT_FILE}"
        )

    data = pd.read_csv(
        INPUT_FILE
    )

    print("=" * 76)
    print("FINAL SCALING AND SEGMENTATION SUMMARY")
    print("=" * 76)

    # --------------------------------------------------------
    # Basic checks
    # --------------------------------------------------------

    required_columns = [
        "species",
        "image_id",
        "mask_source",
        "animal_perimeter_before_scaling",
        "target_animal_perimeter",
        "scale_factor",
        "animal_perimeter_after_scaling",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    if len(data) != EXPECTED_FINAL_IMAGES:
        raise ValueError(
            f"Expected {EXPECTED_FINAL_IMAGES} final images, "
            f"but found {len(data)}."
        )

    number_of_species = int(
        data["species"].nunique()
    )

    if number_of_species != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {number_of_species}."
        )

    if data["image_id"].duplicated().any():
        duplicate_ids = (
            data.loc[
                data["image_id"].duplicated(
                    keep=False
                ),
                "image_id",
            ]
            .tolist()
        )

        raise ValueError(
            "Duplicate image IDs found: "
            + ", ".join(duplicate_ids)
        )

    if data[
        required_columns
    ].isna().any().any():
        raise ValueError(
            "Missing values found in required columns."
        )

    # --------------------------------------------------------
    # Check the target perimeter
    # --------------------------------------------------------

    target_values = (
        data[
            "target_animal_perimeter"
        ]
        .astype(float)
        .unique()
    )

    if len(target_values) != 1:
        raise ValueError(
            "More than one target perimeter was found."
        )

    target_perimeter = float(
        target_values[0]
    )

    observed_median = float(
        data[
            "animal_perimeter_before_scaling"
        ]
        .median()
    )

    if not np.isclose(
        target_perimeter,
        observed_median,
        rtol=0,
        atol=1e-6,
    ):
        raise ValueError(
            "Target perimeter does not match the median "
            "pre-scaling perimeter."
        )

    # --------------------------------------------------------
    # Classify images relative to the median
    # --------------------------------------------------------

    original_perimeters = (
        data[
            "animal_perimeter_before_scaling"
        ]
        .astype(float)
    )

    equal_to_target = np.isclose(
        original_perimeters,
        target_perimeter,
        rtol=0,
        atol=1e-6,
    )

    below_target = (
        original_perimeters
        < target_perimeter
    ) & (
        ~equal_to_target
    )

    above_target = (
        original_perimeters
        > target_perimeter
    ) & (
        ~equal_to_target
    )

    number_below_target = int(
        below_target.sum()
    )

    number_equal_target = int(
        equal_to_target.sum()
    )

    number_above_target = int(
        above_target.sum()
    )

    number_at_or_below_target = (
        number_below_target
        + number_equal_target
    )

    if (
        number_below_target
        + number_equal_target
        + number_above_target
        != EXPECTED_FINAL_IMAGES
    ):
        raise ValueError(
            "Perimeter categories do not sum to 295."
        )

    # --------------------------------------------------------
    # Check scale factors
    # --------------------------------------------------------

    scale_factors = (
        data[
            "scale_factor"
        ]
        .astype(float)
    )

    scale_factor_equal_one = np.isclose(
        scale_factors,
        1.0,
        rtol=0,
        atol=1e-12,
    )

    scale_factor_below_one = (
        scale_factors < 1.0
    ) & (
        ~scale_factor_equal_one
    )

    scale_factor_above_one = (
        scale_factors > 1.0
    ) & (
        ~scale_factor_equal_one
    )

    number_not_rescaled = int(
        scale_factor_equal_one.sum()
    )

    number_downscaled = int(
        scale_factor_below_one.sum()
    )

    number_upscaled = int(
        scale_factor_above_one.sum()
    )

    if number_upscaled != 0:
        raise ValueError(
            f"Found {number_upscaled} upscaled images. "
            "The final method should not enlarge small animals."
        )

    if (
        number_not_rescaled
        != number_at_or_below_target
    ):
        raise ValueError(
            "The number of scale factor = 1 images does not "
            "match the number at or below the target perimeter."
        )

    if (
        number_downscaled
        != number_above_target
    ):
        raise ValueError(
            "The number of downscaled images does not match "
            "the number above the target perimeter."
        )

    # --------------------------------------------------------
    # Segmentation-source counts
    # --------------------------------------------------------

    mask_source_counts = (
        data[
            "mask_source"
        ]
        .value_counts()
    )

    number_automatic = int(
        mask_source_counts.get(
            "automatic_qc_pass",
            0,
        )
    )

    number_manual_rescue = int(
        mask_source_counts.get(
            "manual_rescue",
            0,
        )
    )

    if (
        number_automatic
        + number_manual_rescue
        != EXPECTED_FINAL_IMAGES
    ):
        raise ValueError(
            "Automatic and rescue masks do not sum to "
            "the final 295 images."
        )

    number_requiring_rescue = (
        EXPECTED_INITIAL_IMAGES
        - number_automatic
    )

    number_excluded_after_rescue = (
        number_requiring_rescue
        - number_manual_rescue
    )

    # --------------------------------------------------------
    # Build summary table
    # --------------------------------------------------------

    summary = pd.DataFrame(
        [
            {
                "initial_images_processed": (
                    EXPECTED_INITIAL_IMAGES
                ),
                "final_images": (
                    EXPECTED_FINAL_IMAGES
                ),
                "species": (
                    number_of_species
                ),
                "target_median_perimeter_px": (
                    target_perimeter
                ),
                "images_below_target": (
                    number_below_target
                ),
                "images_equal_to_target": (
                    number_equal_target
                ),
                "images_at_or_below_target_not_enlarged": (
                    number_at_or_below_target
                ),
                "images_above_target_downscaled": (
                    number_above_target
                ),
                "images_with_scale_factor_1": (
                    number_not_rescaled
                ),
                "images_with_scale_factor_below_1": (
                    number_downscaled
                ),
                "images_with_scale_factor_above_1": (
                    number_upscaled
                ),
                "automatic_qc_pass": (
                    number_automatic
                ),
                "images_requiring_rescue": (
                    number_requiring_rescue
                ),
                "successful_manual_rescue": (
                    number_manual_rescue
                ),
                "excluded_after_rescue": (
                    number_excluded_after_rescue
                ),
            }
        ]
    )

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    summary.to_csv(
        SUMMARY_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    summary_lines = [
        "Final scaling and segmentation summary",
        "======================================",
        "",
        (
            "Initial images entering automatic processing: "
            f"{EXPECTED_INITIAL_IMAGES}"
        ),
        (
            "Final images retained: "
            f"{EXPECTED_FINAL_IMAGES}"
        ),
        (
            "Species: "
            f"{number_of_species}"
        ),
        "",
        (
            "Median target animal perimeter: "
            f"{target_perimeter:.2f} px"
        ),
        (
            "Images below the target perimeter: "
            f"{number_below_target}"
        ),
        (
            "Images exactly equal to the target perimeter: "
            f"{number_equal_target}"
        ),
        (
            "Images at or below the target and not enlarged: "
            f"{number_at_or_below_target}"
        ),
        (
            "Images above the target and downscaled: "
            f"{number_above_target}"
        ),
        (
            "Images upscaled: "
            f"{number_upscaled}"
        ),
        "",
        (
            "Automatic QC passes: "
            f"{number_automatic}"
        ),
        (
            "Images requiring rescue: "
            f"{number_requiring_rescue}"
        ),
        (
            "Successful manual rescues: "
            f"{number_manual_rescue}"
        ),
        (
            "Images excluded after rescue: "
            f"{number_excluded_after_rescue}"
        ),
    ]

    SUMMARY_TXT.write_text(
        "\n".join(
            summary_lines
        )
        + "\n",
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Print summary
    # --------------------------------------------------------

    print(
        f"\nFinal images: "
        f"{EXPECTED_FINAL_IMAGES}"
    )

    print(
        f"Species: "
        f"{number_of_species}"
    )

    print(
        f"Median target perimeter: "
        f"{target_perimeter:.2f} px"
    )

    print(
        f"Images below target: "
        f"{number_below_target}"
    )

    print(
        f"Images equal to target: "
        f"{number_equal_target}"
    )

    print(
        "Images at or below target and not enlarged: "
        f"{number_at_or_below_target}"
    )

    print(
        f"Images above target and downscaled: "
        f"{number_above_target}"
    )

    print(
        f"Images upscaled: "
        f"{number_upscaled}"
    )

    print(
        f"\nAutomatic QC passes: "
        f"{number_automatic}"
    )

    print(
        f"Images requiring rescue: "
        f"{number_requiring_rescue}"
    )

    print(
        f"Successful manual rescues: "
        f"{number_manual_rescue}"
    )

    print(
        f"Excluded after rescue: "
        f"{number_excluded_after_rescue}"
    )

    print("\nFiles saved:")

    print(SUMMARY_CSV)
    print(SUMMARY_TXT)


if __name__ == "__main__":
    main()