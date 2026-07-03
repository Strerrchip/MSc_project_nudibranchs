from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]

input_path = (
    PROJECT_DIR
    / "processed_data/automated_image_analysis/image_metrics/grabcut_ring80_image_metrics_pilot.csv"
)

output_path = (
    PROJECT_DIR
    / "processed_data/automated_image_analysis/image_metrics/grabcut_ring80_species_metrics_pilot.csv"
)

metrics = pd.read_csv(input_path)

species_summary = metrics.groupby("species").agg(
    n_images=("image_id", "count"),

    mean_brightness_contrast=("brightness_contrast", "mean"),
    sd_brightness_contrast=("brightness_contrast", "std"),

    mean_saturation_contrast=("saturation_contrast", "mean"),
    sd_saturation_contrast=("saturation_contrast", "std"),

    mean_lab_colour_distance=("lab_colour_distance", "mean"),
    sd_lab_colour_distance=("lab_colour_distance", "std"),

    mean_animal_brightness_sd=("animal_brightness_sd", "mean"),
    sd_animal_brightness_sd=("animal_brightness_sd", "std"),

    mean_animal_saturation_sd=("animal_saturation_sd", "mean"),
    sd_animal_saturation_sd=("animal_saturation_sd", "std"),

    mean_animal_area_pixels=("animal_area_pixels", "mean"),
    mean_background_ring_area_pixels=("background_ring_area_pixels", "mean"),
).reset_index()

numeric_cols = species_summary.select_dtypes(include=["float64", "float32"]).columns
species_summary[numeric_cols] = species_summary[numeric_cols].round(3)

species_summary.to_csv(output_path, index=False)

print("Saved species-level GrabCut ring80 metrics to:")
print(output_path)

print("\nPreview:")
print(species_summary.to_string(index=False))