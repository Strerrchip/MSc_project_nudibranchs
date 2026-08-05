from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------

INPUT_PATH = Path(
    "processed_data/automated_image_analysis/image_metrics/"
    "sam_scaled_ring120_image_metrics_pilot.csv"
)

OUTPUT_PATH = Path(
    "processed_data/automated_image_analysis/image_metrics/"
    "sam_scaled_ring120_visibility_metrics_pilot.csv"
)


# ---------------------------------------------------------------------
# Metrics required from the existing image-level table
# ---------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "species",
    "image_id",

    # Existing direct animal-background comparisons
    "gray_contrast_abs",
    "saturation_contrast_abs",
    "lab_colour_distance",
    "luminance_edge_cv_difference",
    "chromatic_edge_cv_difference",

    # Animal-only metrics for boldness
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_edge_density",
    "animal_luminance_edge_cv",
    "animal_chromatic_edge_mean",
    "animal_chromatic_edge_cv",

    # Background metrics needed for additional comparisons
    "background_gray_sd",
    "background_saturation_sd",
    "background_edge_density",
    "background_chromatic_edge_mean",
]


def main() -> None:
    """Create pilot boldness and detectability metrics."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_PATH.resolve()}"
        )

    df = pd.read_csv(INPUT_PATH)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "The input file is missing these required columns:\n"
            + "\n".join(missing_columns)
        )

    result = pd.DataFrame()

    # Identifiers
    result["species"] = df["species"]
    result["image_id"] = df["image_id"]

    # -----------------------------------------------------------------
    # Boldness metrics
    #
    # These describe visual variation within the animal itself.
    # They are kept separate from detectability because James noted
    # that boldness and detectability are distinct concepts.
    # -----------------------------------------------------------------

    result["boldness_gray_sd"] = df["animal_gray_sd"]

    result["boldness_saturation_sd"] = (
        df["animal_saturation_sd"]
    )

    result["boldness_edge_density"] = (
        df["animal_edge_density"]
    )

    result["boldness_luminance_edge_cv"] = (
        df["animal_luminance_edge_cv"]
    )

    result["boldness_chromatic_edge_mean"] = (
        df["animal_chromatic_edge_mean"]
    )

    result["boldness_chromatic_edge_cv"] = (
        df["animal_chromatic_edge_cv"]
    )

    # -----------------------------------------------------------------
    # Detectability metrics
    #
    # These describe how different the animal is from its immediate
    # background. Absolute differences are used because the current
    # question is how strongly the animal differs from the background,
    # rather than which region has the larger value.
    # -----------------------------------------------------------------

    # Already calculated in the original workflow
    result["detectability_gray_mean_difference"] = (
        df["gray_contrast_abs"]
    )

    result["detectability_saturation_mean_difference"] = (
        df["saturation_contrast_abs"]
    )

    result["detectability_lab_colour_distance"] = (
        df["lab_colour_distance"]
    )

    result["detectability_luminance_edge_cv_difference"] = (
        df["luminance_edge_cv_difference"]
    )

    result["detectability_chromatic_edge_cv_difference"] = (
        df["chromatic_edge_cv_difference"]
    )

    # Newly derived animal-background comparisons
    result["detectability_gray_sd_difference"] = (
        df["animal_gray_sd"] - df["background_gray_sd"]
    ).abs()

    result["detectability_saturation_sd_difference"] = (
        df["animal_saturation_sd"]
        - df["background_saturation_sd"]
    ).abs()

    result["detectability_edge_density_difference"] = (
        df["animal_edge_density"]
        - df["background_edge_density"]
    ).abs()

    result["detectability_chromatic_edge_mean_difference"] = (
        df["animal_chromatic_edge_mean"]
        - df["background_chromatic_edge_mean"]
    ).abs()

    # Check that all calculated metric values are present
    metric_columns = [
        column for column in result.columns
        if column not in ["species", "image_id"]
    ]

    missing_value_counts = result[metric_columns].isna().sum()
    missing_value_counts = missing_value_counts[
        missing_value_counts > 0
    ]

    if not missing_value_counts.empty:
        raise ValueError(
            "Missing values were found in the output metrics:\n"
            + missing_value_counts.to_string()
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    boldness_columns = [
        column for column in result.columns
        if column.startswith("boldness_")
    ]

    detectability_columns = [
        column for column in result.columns
        if column.startswith("detectability_")
    ]

    print("Visibility metric preparation completed.")
    print(f"Input rows: {len(df)}")
    print(f"Output rows: {len(result)}")
    print(f"Boldness metrics: {len(boldness_columns)}")
    print(f"Detectability metrics: {len(detectability_columns)}")
    print(f"Missing metric values: 0")
    print(f"Output saved to:\n{OUTPUT_PATH}")


if __name__ == "__main__":
    main()