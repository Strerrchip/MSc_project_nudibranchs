from pathlib import Path

import numpy as np
import pandas as pd


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
    / "sam_scaled_ring120_image_metrics_final.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "visibility_metrics"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "sam_scaled_ring120_visibility_metrics_final.csv"
)

EXPECTED_IMAGES = 295
EXPECTED_SPECIES = 30


# =========================
# Metric definitions
# =========================

BOLDNESS_METRICS = [
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_edge_density",
    "animal_luminance_edge_cv",
    "animal_chromatic_edge_mean",
    "animal_chromatic_edge_cv",
]

DIRECT_DETECTABILITY_METRICS = [
    "gray_contrast_abs",
    "saturation_contrast_abs",
    "lab_colour_distance",
    "luminance_edge_cv_difference",
    "chromatic_edge_cv_difference",
]

DERIVED_DETECTABILITY_METRICS = [
    "gray_sd_difference",
    "saturation_sd_difference",
    "edge_density_difference",
    "chromatic_edge_mean_difference",
]

DETECTABILITY_METRICS = (
    DIRECT_DETECTABILITY_METRICS
    + DERIVED_DETECTABILITY_METRICS
)

VISIBILITY_METRICS = (
    BOLDNESS_METRICS
    + DETECTABILITY_METRICS
)


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find input metrics file: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_CSV)

    if len(df) != EXPECTED_IMAGES:
        raise ValueError(
            f"Expected {EXPECTED_IMAGES} images, "
            f"but found {len(df)}."
        )

    species_count = df["species"].nunique()

    if species_count != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {species_count}."
        )

    if df["image_id"].duplicated().any():
        duplicated = (
            df.loc[
                df["image_id"].duplicated(keep=False),
                "image_id",
            ]
            .astype(str)
            .tolist()
        )

        raise ValueError(
            "Duplicate image_id values found: "
            + ", ".join(duplicated)
        )

    required_source_columns = [
        "species",
        "image_id",
        "animal_gray_sd",
        "background_gray_sd",
        "animal_saturation_sd",
        "background_saturation_sd",
        "animal_edge_density",
        "background_edge_density",
        "animal_luminance_edge_cv",
        "animal_chromatic_edge_mean",
        "background_chromatic_edge_mean",
        "animal_chromatic_edge_cv",
        "gray_contrast_abs",
        "saturation_contrast_abs",
        "lab_colour_distance",
        "luminance_edge_cv_difference",
        "chromatic_edge_cv_difference",
    ]

    missing_source_columns = [
        column
        for column in required_source_columns
        if column not in df.columns
    ]

    if missing_source_columns:
        raise KeyError(
            "Missing required source columns: "
            + ", ".join(missing_source_columns)
        )

    # Additional animal-background differences used to describe
    # detectability. Absolute differences are used because the
    # magnitude of visual separation is the quantity of interest.
    df["gray_sd_difference"] = (
        df["animal_gray_sd"]
        - df["background_gray_sd"]
    ).abs()

    df["saturation_sd_difference"] = (
        df["animal_saturation_sd"]
        - df["background_saturation_sd"]
    ).abs()

    df["edge_density_difference"] = (
        df["animal_edge_density"]
        - df["background_edge_density"]
    ).abs()

    df["chromatic_edge_mean_difference"] = (
        df["animal_chromatic_edge_mean"]
        - df["background_chromatic_edge_mean"]
    ).abs()

    output_columns = [
        "species",
        "image_id",
        *BOLDNESS_METRICS,
        *DETECTABILITY_METRICS,
    ]

    visibility_df = df[
        output_columns
    ].copy()

    missing_values = (
        visibility_df[VISIBILITY_METRICS]
        .isna()
        .sum()
    )

    if missing_values.sum() > 0:
        print(
            "WARNING: missing values were found "
            "in the visibility metrics:"
        )
        print(
            missing_values[
                missing_values > 0
            ].to_string()
        )
    else:
        print(
            "No missing values in the "
            "15 visibility metrics."
        )

    visibility_df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print()
    print("=" * 72)
    print("VISIBILITY METRICS COMPLETE")
    print("=" * 72)
    print(
        f"Images: {len(visibility_df)}"
    )
    print(
        f"Species: "
        f"{visibility_df['species'].nunique()}"
    )
    print(
        f"Boldness metrics: "
        f"{len(BOLDNESS_METRICS)}"
    )
    print(
        f"Detectability metrics: "
        f"{len(DETECTABILITY_METRICS)}"
    )
    print(
        f"Total visibility metrics: "
        f"{len(VISIBILITY_METRICS)}"
    )
    print()
    print("Saved to:")
    print(
        OUTPUT_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )


if __name__ == "__main__":
    main()
