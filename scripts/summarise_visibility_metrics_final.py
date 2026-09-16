from pathlib import Path

import pandas as pd


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "visibility_metrics"
    / "sam_scaled_ring120_visibility_metrics_final.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "species_metrics"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "sam_scaled_ring120_visibility_species_summary_final.csv"
)

EXPECTED_IMAGES = 295
EXPECTED_SPECIES = 30

BOLDNESS_METRICS = [
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_edge_density",
    "animal_luminance_edge_cv",
    "animal_chromatic_edge_mean",
    "animal_chromatic_edge_cv",
]

DETECTABILITY_METRICS = [
    "gray_contrast_abs",
    "saturation_contrast_abs",
    "lab_colour_distance",
    "luminance_edge_cv_difference",
    "chromatic_edge_cv_difference",
    "gray_sd_difference",
    "saturation_sd_difference",
    "edge_density_difference",
    "chromatic_edge_mean_difference",
]

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
            f"Cannot find visibility metrics: {INPUT_CSV}"
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

    if df["species"].nunique() != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {df['species'].nunique()}."
        )

    missing_columns = [
        metric
        for metric in VISIBILITY_METRICS
        if metric not in df.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing visibility metrics: "
            + ", ".join(missing_columns)
        )

    grouped = df.groupby(
        "species",
        sort=True,
    )

    species_summary = grouped.size().rename(
        "n_images"
    ).to_frame()

    for metric in VISIBILITY_METRICS:
        species_summary[
            f"{metric}_mean"
        ] = grouped[metric].mean()

        species_summary[
            f"{metric}_sd"
        ] = grouped[metric].std(
            ddof=1
        )

    species_summary = (
        species_summary
        .reset_index()
    )

    if len(species_summary) != EXPECTED_SPECIES:
        raise ValueError(
            "Species summary does not contain "
            f"{EXPECTED_SPECIES} rows."
        )

    metric_summary_columns = [
        column
        for column in species_summary.columns
        if column not in [
            "species",
            "n_images",
        ]
    ]

    missing_values = (
        species_summary[
            metric_summary_columns
        ]
        .isna()
        .sum()
    )

    if missing_values.sum() > 0:
        print(
            "WARNING: missing values were found "
            "in the species summary:"
        )
        print(
            missing_values[
                missing_values > 0
            ].to_string()
        )
    else:
        print(
            "No missing values in the "
            "species-level summary."
        )

    species_summary.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print()
    print("=" * 72)
    print("SPECIES VISIBILITY SUMMARY COMPLETE")
    print("=" * 72)
    print(
        f"Images represented: "
        f"{species_summary['n_images'].sum()}"
    )
    print(
        f"Species: "
        f"{len(species_summary)}"
    )
    print(
        f"Images per species: "
        f"{species_summary['n_images'].min()}-"
        f"{species_summary['n_images'].max()}"
    )
    print()
    print(
        species_summary[
            ["species", "n_images"]
        ].to_string(
            index=False
        )
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
