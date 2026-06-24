from pathlib import Path
import pandas as pd

# Project root: C:/Users/Cicad/Desktop/MSc_project_nudibranchs
PROJECT_ROOT = Path(__file__).resolve().parents[1]

input_file = PROJECT_ROOT / "processed_data" / "image_analysis" / "pilot_imagej_summary.csv"
output_file = PROJECT_ROOT / "processed_data" / "image_analysis" / "pilot_imagej_species_summary.csv"

df = pd.read_csv(input_file)

# Columns we want to summarise at species level
contrast_cols = [
    "gray_contrast",
    "red_contrast",
    "green_contrast",
    "blue_contrast",
    "saturation_contrast",
    "brightness_contrast",
]

species_summary = (
    df.groupby("species")
    .agg(
        n_images=("image_id", "count"),
        mean_gray_contrast=("gray_contrast", "mean"),
        sd_gray_contrast=("gray_contrast", "std"),
        mean_red_contrast=("red_contrast", "mean"),
        sd_red_contrast=("red_contrast", "std"),
        mean_green_contrast=("green_contrast", "mean"),
        sd_green_contrast=("green_contrast", "std"),
        mean_blue_contrast=("blue_contrast", "mean"),
        sd_blue_contrast=("blue_contrast", "std"),
        mean_saturation_contrast=("saturation_contrast", "mean"),
        sd_saturation_contrast=("saturation_contrast", "std"),
        mean_brightness_contrast=("brightness_contrast", "mean"),
        sd_brightness_contrast=("brightness_contrast", "std"),
    )
    .reset_index()
)

# Round values for readability
numeric_cols = species_summary.select_dtypes(include="number").columns
species_summary[numeric_cols] = species_summary[numeric_cols].round(3)

species_summary.to_csv(output_file, index=False)

print("Species-level ImageJ summary saved to:")
print(output_file)
print()
print(species_summary)