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


# These are the main image traits to summarise at species level.
# They include animal-background contrast traits and animal-only pattern traits.
METRIC_COLUMNS = [
    "gray_contrast",
    "brightness_contrast",
    "saturation_contrast",
    "lab_colour_distance",
    "animal_brightness_sd",
    "animal_saturation_sd",
    "animal_gray_sd",
    "animal_edge_density",
    "animal_area_fraction",
    "background_ring_area_fraction",
]


def make_project_relative_path(path):
    """Convert a full path to a project-relative path."""
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {INPUT_CSV}")

    image_df = pd.read_csv(INPUT_CSV)

    missing_columns = [col for col in METRIC_COLUMNS if col not in image_df.columns]

    if missing_columns:
        raise ValueError(
            "These expected metric columns are missing from the image-level CSV: "
            + ", ".join(missing_columns)
        )

    summary_rows = []

    for species, species_df in image_df.groupby("species"):
        row = {
            "species": species,
            "n_images": len(species_df),
        }

        for metric in METRIC_COLUMNS:
            row[f"mean_{metric}"] = species_df[metric].mean()
            row[f"sd_{metric}"] = species_df[metric].std()

        summary_rows.append(row)

    species_summary_df = pd.DataFrame(summary_rows)

    species_summary_df = species_summary_df.sort_values("species")

    species_summary_df.to_csv(OUTPUT_CSV, index=False)

    print("Done.")
    print(f"Species-level metrics saved to: {make_project_relative_path(OUTPUT_CSV)}")

    preview_columns = [
        "species",
        "n_images",
        "mean_gray_contrast",
        "mean_brightness_contrast",
        "mean_saturation_contrast",
        "mean_lab_colour_distance",
        "mean_animal_brightness_sd",
        "mean_animal_saturation_sd",
        "mean_animal_edge_density",
    ]

    print("\nPreview:")
    print(species_summary_df[preview_columns].round(3).to_string(index=False))


if __name__ == "__main__":
    main()