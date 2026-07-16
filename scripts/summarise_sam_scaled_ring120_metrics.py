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
    / "image_metrics"
    / "sam_scaled_ring120_image_metrics_pilot.csv"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
    / "sam_scaled_ring120_species_metrics_pilot.csv"
)


# =========================
# Metrics to summarise
# =========================

# Mean brightness and colour values for the animal and background.
# These help interpret the direction of signed contrast measurements.
LEVEL_METRIC_COLUMNS = [
    "animal_gray_mean",
    "background_gray_mean",
    "animal_saturation_mean",
    "background_saturation_mean",
    "animal_brightness_mean",
    "background_brightness_mean",
]


# Animal-background contrast measurements.
#
# Signed values show direction:
# positive = animal value is higher than background value
# negative = animal value is lower than background value
#
# Absolute values show the size of the difference and are more directly
# related to detectability.
CONTRAST_METRIC_COLUMNS = [
    "gray_contrast",
    "gray_contrast_abs",
    "brightness_contrast",
    "brightness_contrast_abs",
    "saturation_contrast",
    "saturation_contrast_abs",
    "lab_colour_distance",
]


# Variation measured inside the animal.
ANIMAL_VARIATION_COLUMNS = [
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_brightness_sd",
    "animal_edge_density",
    "animal_luminance_edge_mean",
    "animal_luminance_edge_sd",
    "animal_luminance_edge_cv",
]


# Variation measured inside the 120 px background ring.
BACKGROUND_VARIATION_COLUMNS = [
    "background_gray_sd",
    "background_saturation_sd",
    "background_brightness_sd",
    "background_edge_density",
    "background_luminance_edge_mean",
    "background_luminance_edge_sd",
    "background_luminance_edge_cv",
]


# Direct comparison between animal and background edge structure.
EDGE_COMPARISON_COLUMNS = [
    "luminance_edge_cv_difference",
]


# These variables are mainly used to check whether image scaling and
# mask construction behave consistently.
QC_COLUMNS = [
    "animal_area_fraction",
    "background_ring_area_fraction",
]


METRIC_COLUMNS = (
    LEVEL_METRIC_COLUMNS
    + CONTRAST_METRIC_COLUMNS
    + ANIMAL_VARIATION_COLUMNS
    + BACKGROUND_VARIATION_COLUMNS
    + EDGE_COMPARISON_COLUMNS
    + QC_COLUMNS
)


# =========================
# Helper functions
# =========================

def make_project_relative_path(path):
    """Convert a full path to a project-relative path."""
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_required_columns(image_df):
    """Check that all expected columns are present."""
    required_columns = ["species", "image_id"] + METRIC_COLUMNS

    missing_columns = [
        column
        for column in required_columns
        if column not in image_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "These expected columns are missing from the image-level CSV: "
            + ", ".join(missing_columns)
        )


def check_numeric_columns(image_df):
    """
    Confirm that metric columns contain numeric values.

    Existing missing values are allowed, but text values that cannot be
    converted to numbers cause an error.
    """
    for metric in METRIC_COLUMNS:
        original_values = image_df[metric]

        converted_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        invalid_values = (
            original_values.notna()
            & converted_values.isna()
        )

        if invalid_values.any():
            invalid_rows = image_df.loc[
                invalid_values,
                ["species", "image_id", metric],
            ]

            raise ValueError(
                f"Non-numeric values found in {metric}:\n"
                f"{invalid_rows.to_string(index=False)}"
            )

        image_df[metric] = converted_values


def report_missing_values(image_df):
    """Print any missing values found in the selected metrics."""
    missing_counts = image_df[METRIC_COLUMNS].isna().sum()
    missing_counts = missing_counts[missing_counts > 0]

    if missing_counts.empty:
        print("No missing metric values found.")
        return

    print("\nWarning: missing values were found:")
    print(missing_counts.to_string())


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find input CSV: {INPUT_CSV}"
        )

    image_df = pd.read_csv(INPUT_CSV)

    check_required_columns(image_df)
    check_numeric_columns(image_df)
    report_missing_values(image_df)

    summary_rows = []

    for species, species_df in image_df.groupby(
        "species",
        sort=True,
    ):
        row = {
            "species": species,
            "n_images": len(species_df),
        }

        for metric in METRIC_COLUMNS:
            row[f"mean_{metric}"] = species_df[metric].mean()

            # Pandas uses sample standard deviation here.
            # If a species has only one image, the SD will be NaN.
            row[f"sd_{metric}"] = species_df[metric].std()

        summary_rows.append(row)

    species_summary_df = pd.DataFrame(summary_rows)

    species_summary_df = species_summary_df.sort_values(
        "species"
    ).reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    species_summary_df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print("\nDone.")
    print(
        "Species-level metrics saved to: "
        f"{make_project_relative_path(OUTPUT_CSV)}"
    )

    preview_columns = [
        "species",
        "n_images",
        "mean_brightness_contrast_abs",
        "mean_saturation_contrast_abs",
        "mean_lab_colour_distance",
        "mean_animal_edge_density",
        "mean_background_edge_density",
        "mean_animal_luminance_edge_cv",
        "mean_background_luminance_edge_cv",
        "mean_luminance_edge_cv_difference",
    ]

    print("\nPreview:")
    print(
        species_summary_df[preview_columns]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()