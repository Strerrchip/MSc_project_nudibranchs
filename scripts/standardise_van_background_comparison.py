from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# File paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPARISON_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "van_background_comparison"
)

VAN_MEANS_FILE = (
    COMPARISON_DIR
    / "van_background_species_metric_means.csv"
)

ONLINE_MEANS_FILE = (
    COMPARISON_DIR
    / "online_background_species_metric_means.csv"
)

OUTPUT_FILE = (
    COMPARISON_DIR
    / "van_online_background_comparison_zscores.csv"
)


# ============================================================
# Metric pairs
# ============================================================

METRIC_PAIRS = [
    {
        "comparison": "luminance_edge_mean",
        "online_metric": "online_luminance_edge_mean",
        "van_metric": "van_luminance_edge_mean",
    },
    {
        "comparison": "luminance_edge_cv",
        "online_metric": "online_luminance_edge_cv",
        "van_metric": "van_luminance_edge_cv",
    },
    {
        "comparison": "chromatic_edge_mean",
        "online_metric": "online_chromatic_edge_mean",
        "van_metric": "van_chromatic_edge_mean",
    },
    {
        "comparison": "chromatic_edge_cv",
        "online_metric": "online_chromatic_edge_cv",
        "van_metric": "van_chromatic_edge_cv",
    },
]


# ============================================================
# Standardisation function
# ============================================================

def z_standardise(values):
    """
    Convert values to z-scores.

    A positive z-score means that a species has a value above
    the mean of the nine overlapping species.

    A negative z-score means that a species has a value below
    the mean of the nine overlapping species.
    """

    values = pd.to_numeric(
        values,
        errors="raise",
    ).astype(float)

    mean = values.mean()

    # Use sample standard deviation, consistent with the PCA script.
    sd = values.std(ddof=1)

    if not np.isfinite(sd) or sd <= 0:
        raise ValueError(
            "Cannot standardise a variable with zero or "
            "invalid standard deviation."
        )

    return (values - mean) / sd


# ============================================================
# Main workflow
# ============================================================

def main():

    # --------------------------------------------------------
    # Check input files
    # --------------------------------------------------------

    if not VAN_MEANS_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find Van species means: "
            f"{VAN_MEANS_FILE}"
        )

    if not ONLINE_MEANS_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find online-image species means: "
            f"{ONLINE_MEANS_FILE}"
        )

    # --------------------------------------------------------
    # Read input files
    # --------------------------------------------------------

    van_data = pd.read_csv(
        VAN_MEANS_FILE
    )

    online_data = pd.read_csv(
        ONLINE_MEANS_FILE
    )

    print("=" * 72)
    print("INPUT CHECK")
    print("=" * 72)

    print(
        f"\nVan rows: {len(van_data)}"
    )

    print(
        f"Online-image rows: {len(online_data)}"
    )

    # --------------------------------------------------------
    # Check expected rows
    # --------------------------------------------------------

    if len(van_data) != 18:
        raise ValueError(
            "Expected 18 Van rows: "
            "9 species x 2 distances. "
            f"Found {len(van_data)}."
        )

    if len(online_data) != 9:
        raise ValueError(
            "Expected 9 online-image rows. "
            f"Found {len(online_data)}."
        )

    if van_data["species"].duplicated().all():
        raise ValueError(
            "Unexpected duplicate structure in Van data."
        )

    if online_data["species"].duplicated().any():
        raise ValueError(
            "Duplicate species found in online-image data."
        )

    # --------------------------------------------------------
    # Check distance values
    # --------------------------------------------------------

    van_data["distance"] = (
        van_data["distance"]
        .astype(str)
        .str.strip()
    )

    expected_distances = {
        "2cm",
        "30cm",
    }

    observed_distances = set(
        van_data["distance"].unique()
    )

    if observed_distances != expected_distances:
        raise ValueError(
            "Expected Van distances 2cm and 30cm, "
            f"but found {sorted(observed_distances)}."
        )

    distance_counts = (
        van_data["distance"]
        .value_counts()
        .to_dict()
    )

    if distance_counts.get("2cm") != 9:
        raise ValueError(
            "Expected 9 species at 2cm."
        )

    if distance_counts.get("30cm") != 9:
        raise ValueError(
            "Expected 9 species at 30cm."
        )

    # --------------------------------------------------------
    # Check metric columns
    # --------------------------------------------------------

    required_van_columns = [
        "species",
        "distance",
        "van_n_records",
        "van_n_individuals",
    ]

    required_online_columns = [
        "species",
        "our_n_images",
    ]

    for pair in METRIC_PAIRS:
        required_van_columns.append(
            pair["van_metric"]
        )

        required_online_columns.append(
            pair["online_metric"]
        )

    missing_van = [
        column
        for column in required_van_columns
        if column not in van_data.columns
    ]

    missing_online = [
        column
        for column in required_online_columns
        if column not in online_data.columns
    ]

    if missing_van:
        raise KeyError(
            "Missing Van columns: "
            + ", ".join(missing_van)
        )

    if missing_online:
        raise KeyError(
            "Missing online-image columns: "
            + ", ".join(missing_online)
        )

    # --------------------------------------------------------
    # Check that the same nine species are present
    # --------------------------------------------------------

    van_species = set(
        van_data["species"]
    )

    online_species = set(
        online_data["species"]
    )

    if van_species != online_species:
        only_in_van = sorted(
            van_species - online_species
        )

        only_in_online = sorted(
            online_species - van_species
        )

        raise ValueError(
            "Species do not match between the two files.\n"
            f"Only in Van: {only_in_van}\n"
            f"Only in online data: {only_in_online}"
        )

    # Make working copies.
    van_standardised = (
        van_data.copy()
    )

    online_standardised = (
        online_data.copy()
    )

    # --------------------------------------------------------
    # Standardise online-image metrics
    # --------------------------------------------------------

    # Each online metric is standardised once across the
    # nine overlapping species.
    for pair in METRIC_PAIRS:

        online_metric = (
            pair["online_metric"]
        )

        online_z_column = (
            f"{online_metric}_z"
        )

        online_standardised[
            online_z_column
        ] = z_standardise(
            online_standardised[
                online_metric
            ]
        )

    # --------------------------------------------------------
    # Standardise Van metrics
    # --------------------------------------------------------

    # Van values are standardised separately within the
    # 2cm and 30cm datasets.
    #
    # This is necessary because viewing distance changes
    # the scale and distribution of the QCPA measurements.
    for pair in METRIC_PAIRS:

        van_metric = (
            pair["van_metric"]
        )

        van_z_column = (
            f"{van_metric}_z"
        )

        van_standardised[
            van_z_column
        ] = (
            van_standardised
            .groupby(
                "distance"
            )[
                van_metric
            ]
            .transform(
                z_standardise
            )
        )

    # --------------------------------------------------------
    # Merge the standardised datasets
    # --------------------------------------------------------

    comparison = (
        van_standardised
        .merge(
            online_standardised,
            on="species",
            how="inner",
            validate="many_to_one",
        )
        .sort_values(
            [
                "species",
                "distance",
            ]
        )
        .reset_index(drop=True)
    )

    if len(comparison) != 18:
        raise ValueError(
            "Expected 18 rows after merging, "
            f"but found {len(comparison)}."
        )

    if comparison.isna().any().any():
        missing_columns = (
            comparison.columns[
                comparison.isna().any()
            ]
            .tolist()
        )

        raise ValueError(
            "Missing values found after merging in: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Arrange output columns
    # --------------------------------------------------------

    output_columns = [
        "species",
        "distance",
        "our_n_images",
        "van_n_records",
        "van_n_individuals",
    ]

    for pair in METRIC_PAIRS:

        online_metric = (
            pair["online_metric"]
        )

        van_metric = (
            pair["van_metric"]
        )

        output_columns.extend(
            [
                online_metric,
                f"{online_metric}_z",
                van_metric,
                f"{van_metric}_z",
            ]
        )

    comparison = comparison[
        output_columns
    ]

    # --------------------------------------------------------
    # Verify standardisation
    # --------------------------------------------------------

    print("\n" + "=" * 72)
    print("STANDARDISATION CHECK")
    print("=" * 72)

    for pair in METRIC_PAIRS:

        comparison_name = (
            pair["comparison"]
        )

        online_z_column = (
            f"{pair['online_metric']}_z"
        )

        van_z_column = (
            f"{pair['van_metric']}_z"
        )

        # Online values occur twice after merging because
        # Van has two distance rows. Check the original
        # nine-row online table instead.
        online_mean = (
            online_standardised[
                online_z_column
            ]
            .mean()
        )

        online_sd = (
            online_standardised[
                online_z_column
            ]
            .std(ddof=1)
        )

        print(
            f"\n{comparison_name}"
        )

        print(
            "  Online z-score mean: "
            f"{online_mean:.6f}"
        )

        print(
            "  Online z-score SD: "
            f"{online_sd:.6f}"
        )

        if not np.isclose(
            online_mean,
            0,
            atol=1e-10,
        ):
            raise ValueError(
                f"Online z-score mean is not zero for "
                f"{comparison_name}."
            )

        if not np.isclose(
            online_sd,
            1,
            atol=1e-10,
        ):
            raise ValueError(
                f"Online z-score SD is not one for "
                f"{comparison_name}."
            )

        for distance in [
            "2cm",
            "30cm",
        ]:

            distance_values = (
                comparison.loc[
                    comparison[
                        "distance"
                    ].eq(distance),
                    van_z_column,
                ]
            )

            distance_mean = (
                distance_values.mean()
            )

            distance_sd = (
                distance_values.std(
                    ddof=1
                )
            )

            print(
                f"  Van {distance} z-score mean: "
                f"{distance_mean:.6f}"
            )

            print(
                f"  Van {distance} z-score SD: "
                f"{distance_sd:.6f}"
            )

            if not np.isclose(
                distance_mean,
                0,
                atol=1e-10,
            ):
                raise ValueError(
                    f"Van {distance} z-score mean is "
                    f"not zero for {comparison_name}."
                )

            if not np.isclose(
                distance_sd,
                1,
                atol=1e-10,
            ):
                raise ValueError(
                    f"Van {distance} z-score SD is "
                    f"not one for {comparison_name}."
                )

    # --------------------------------------------------------
    # Save output
    # --------------------------------------------------------

    comparison.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 72)
    print("STANDARDISATION COMPLETE")
    print("=" * 72)

    print(
        f"\nRows in final comparison table: "
        f"{len(comparison)}"
    )

    print(
        f"Species: "
        f"{comparison['species'].nunique()}"
    )

    print(
        "Distances: "
        + ", ".join(
            sorted(
                comparison[
                    "distance"
                ].unique()
            )
        )
    )

    print("\nSaved comparison file:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()