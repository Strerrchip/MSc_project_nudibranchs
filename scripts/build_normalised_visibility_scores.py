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
    / "species_metrics"
    / "sam_scaled_ring120_visibility_species_summary_final.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "composite_scores"
)

SCORES_FILE = (
    OUTPUT_DIR
    / "visibility_mean_normalised_scores.csv"
)

STANDARDISATION_FILE = (
    OUTPUT_DIR
    / "visibility_metric_standardisation.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "visibility_mean_normalised_scores_summary.txt"
)


# ============================================================
# Metric definitions
# ============================================================

# All six metrics are already oriented so that a larger value
# represents greater within-animal colour-pattern boldness.

BOLDNESS_METRICS = [
    "animal_gray_sd_mean",
    "animal_saturation_sd_mean",
    "animal_edge_density_mean",
    "animal_luminance_edge_cv_mean",
    "animal_chromatic_edge_mean_mean",
    "animal_chromatic_edge_cv_mean",
]


# All nine metrics are already oriented so that a larger value
# represents a greater difference between the animal and its
# immediate background.

DETECTABILITY_METRICS = [
    "gray_contrast_abs_mean",
    "saturation_contrast_abs_mean",
    "lab_colour_distance_mean",
    "luminance_edge_cv_difference_mean",
    "chromatic_edge_cv_difference_mean",
    "gray_sd_difference_mean",
    "saturation_sd_difference_mean",
    "edge_density_difference_mean",
    "chromatic_edge_mean_difference_mean",
]


# ============================================================
# Standardisation
# ============================================================

def z_standardise(values):
    """
    Standardise a metric across the 30 species.

    The sample standard deviation is used so that this is
    consistent with the existing PCA analysis.

    Returns:
        z-scores
        original mean
        original standard deviation
    """

    values = pd.to_numeric(
        values,
        errors="raise",
    ).astype(float)

    mean = float(
        values.mean()
    )

    sd = float(
        values.std(ddof=1)
    )

    if not np.isfinite(sd) or sd <= 0:
        raise ValueError(
            "Cannot standardise a metric with zero or "
            "invalid standard deviation."
        )

    z_scores = (
        values - mean
    ) / sd

    return z_scores, mean, sd


def make_z_column_name(metric):
    """
    Convert an input metric name into a shorter z-score name.
    """

    if metric.endswith("_mean"):
        base_name = metric[:-5]
    else:
        base_name = metric

    return f"{base_name}_z"


# ============================================================
# Main workflow
# ============================================================

def main():

    # --------------------------------------------------------
    # Read and check input
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find species metric table: "
            f"{INPUT_FILE}"
        )

    data = pd.read_csv(
        INPUT_FILE
    )

    print("=" * 76)
    print("MEAN NORMALISED VISIBILITY SCORES")
    print("=" * 76)

    print(
        f"\nSpecies rows: {len(data)}"
    )

    if len(data) != 30:
        raise ValueError(
            f"Expected 30 species, but found {len(data)}."
        )

    if "species" not in data.columns:
        raise KeyError(
            "Input table is missing the species column."
        )

    if "n_images" not in data.columns:
        raise KeyError(
            "Input table is missing the n_images column."
        )

    if data["species"].duplicated().any():
        duplicate_species = (
            data.loc[
                data["species"].duplicated(
                    keep=False
                ),
                "species",
            ]
            .tolist()
        )

        raise ValueError(
            "Duplicate species rows found: "
            + ", ".join(duplicate_species)
        )

    total_images = int(
        data["n_images"].sum()
    )

    print(
        f"Images represented: {total_images}"
    )

    if total_images != 295:
        raise ValueError(
            f"Expected 295 images, but found {total_images}."
        )

    required_metrics = (
        BOLDNESS_METRICS
        + DETECTABILITY_METRICS
    )

    missing_metrics = [
        metric
        for metric in required_metrics
        if metric not in data.columns
    ]

    if missing_metrics:
        raise KeyError(
            "Missing input metrics: "
            + ", ".join(missing_metrics)
        )

    if data[
        required_metrics
    ].isna().any().any():
        missing_columns = (
            data[
                required_metrics
            ]
            .columns[
                data[
                    required_metrics
                ]
                .isna()
                .any()
            ]
            .tolist()
        )

        raise ValueError(
            "Missing values found in: "
            + ", ".join(missing_columns)
        )

    # Keep species in alphabetical order.
    data = (
        data
        .sort_values("species")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Prepare output table
    # --------------------------------------------------------

    output = data[
        [
            "species",
            "n_images",
            *required_metrics,
        ]
    ].copy()

    standardisation_rows = []

    boldness_z_columns = []
    detectability_z_columns = []

    # --------------------------------------------------------
    # Standardise boldness metrics
    # --------------------------------------------------------

    for metric in BOLDNESS_METRICS:

        z_scores, mean, sd = (
            z_standardise(
                data[metric]
            )
        )

        z_column = (
            make_z_column_name(
                metric
            )
        )

        output[
            z_column
        ] = z_scores

        boldness_z_columns.append(
            z_column
        )

        standardisation_rows.append(
            {
                "metric_group": "boldness",
                "metric": metric,
                "z_score_column": z_column,
                "direction_multiplier": 1,
                "higher_value_interpretation": (
                    "greater boldness"
                ),
                "species_mean": mean,
                "species_sd": sd,
                "standardisation_ddof": 1,
            }
        )

    # --------------------------------------------------------
    # Standardise detectability metrics
    # --------------------------------------------------------

    for metric in DETECTABILITY_METRICS:

        z_scores, mean, sd = (
            z_standardise(
                data[metric]
            )
        )

        z_column = (
            make_z_column_name(
                metric
            )
        )

        output[
            z_column
        ] = z_scores

        detectability_z_columns.append(
            z_column
        )

        standardisation_rows.append(
            {
                "metric_group": "detectability",
                "metric": metric,
                "z_score_column": z_column,
                "direction_multiplier": 1,
                "higher_value_interpretation": (
                    "greater detectability"
                ),
                "species_mean": mean,
                "species_sd": sd,
                "standardisation_ddof": 1,
            }
        )

    # --------------------------------------------------------
    # Calculate mean normalised scores
    # --------------------------------------------------------

    output[
        "mean_normalised_boldness"
    ] = (
        output[
            boldness_z_columns
        ]
        .mean(axis=1)
    )

    output[
        "mean_normalised_detectability"
    ] = (
        output[
            detectability_z_columns
        ]
        .mean(axis=1)
    )

    if output.isna().any().any():
        raise ValueError(
            "Missing values found in the final score table."
        )

    # --------------------------------------------------------
    # Verify z-scores
    # --------------------------------------------------------

    print("\n" + "=" * 76)
    print("STANDARDISATION CHECK")
    print("=" * 76)

    all_z_columns = (
        boldness_z_columns
        + detectability_z_columns
    )

    for z_column in all_z_columns:

        mean = float(
            output[
                z_column
            ]
            .mean()
        )

        sd = float(
            output[
                z_column
            ]
            .std(ddof=1)
        )

        print(
            f"{z_column}: "
            f"mean = {mean:.6f}, "
            f"SD = {sd:.6f}"
        )

        if not np.isclose(
            mean,
            0,
            atol=1e-10,
        ):
            raise ValueError(
                f"{z_column} does not have mean zero."
            )

        if not np.isclose(
            sd,
            1,
            atol=1e-10,
        ):
            raise ValueError(
                f"{z_column} does not have SD one."
            )

    # The mean of several z-score columns should also be
    # approximately zero.
    boldness_score_mean = float(
        output[
            "mean_normalised_boldness"
        ]
        .mean()
    )

    detectability_score_mean = float(
        output[
            "mean_normalised_detectability"
        ]
        .mean()
    )

    if not np.isclose(
        boldness_score_mean,
        0,
        atol=1e-10,
    ):
        raise ValueError(
            "Mean normalised boldness does not have "
            "an overall mean of zero."
        )

    if not np.isclose(
        detectability_score_mean,
        0,
        atol=1e-10,
    ):
        raise ValueError(
            "Mean normalised detectability does not have "
            "an overall mean of zero."
        )

    # --------------------------------------------------------
    # Save files
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        SCORES_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    standardisation_table = pd.DataFrame(
        standardisation_rows
    )

    standardisation_table.to_csv(
        STANDARDISATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary_lines = [
        "Mean normalised visibility scores",
        "=================================",
        "",
        f"Species: {len(output)}",
        (
            "Images represented: "
            f"{int(output['n_images'].sum())}"
        ),
        (
            "Boldness metrics averaged: "
            f"{len(BOLDNESS_METRICS)}"
        ),
        (
            "Detectability metrics averaged: "
            f"{len(DETECTABILITY_METRICS)}"
        ),
        "",
        "Method:",
        (
            "Each species-level metric was z-standardised "
            "across the 30 species using the sample standard "
            "deviation."
        ),
        (
            "All metrics were already oriented so that larger "
            "values represented greater boldness or "
            "detectability."
        ),
        (
            "The standardised metrics were averaged separately "
            "for boldness and detectability."
        ),
        (
            "The existing PCA outputs were not changed and "
            "remain available as secondary analyses."
        ),
        "",
        (
            "Mean normalised boldness range: "
            f"{output['mean_normalised_boldness'].min():.4f} "
            "to "
            f"{output['mean_normalised_boldness'].max():.4f}"
        ),
        (
            "Mean normalised detectability range: "
            f"{output['mean_normalised_detectability'].min():.4f} "
            "to "
            f"{output['mean_normalised_detectability'].max():.4f}"
        ),
    ]

    SUMMARY_FILE.write_text(
        "\n".join(
            summary_lines
        )
        + "\n",
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Print final scores
    # --------------------------------------------------------

    print("\n" + "=" * 76)
    print("FINAL COMPOSITE SCORES")
    print("=" * 76)

    print(
        output[
            [
                "species",
                "n_images",
                "mean_normalised_boldness",
                "mean_normalised_detectability",
            ]
        ]
        .to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.4f}"
            ),
        )
    )

    print("\n" + "=" * 76)
    print("FILES SAVED")
    print("=" * 76)

    print("\nComposite scores:")
    print(SCORES_FILE)

    print("\nStandardisation audit:")
    print(STANDARDISATION_FILE)

    print("\nSummary:")
    print(SUMMARY_FILE)


if __name__ == "__main__":
    main()