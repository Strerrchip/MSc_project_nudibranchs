from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]

metrics_path = (
    PROJECT_DIR
    / "processed_data/automated_image_analysis/image_metrics/grabcut_image_metrics_pilot.csv"
)

metrics = pd.read_csv(metrics_path)

columns_to_show = [
    "species",
    "image_id",
    "animal_area_pixels",
    "background_ring_area_pixels",
    "brightness_contrast",
    "saturation_contrast",
    "lab_colour_distance",
    "animal_brightness_sd",
    "animal_saturation_sd",
]

print(metrics[columns_to_show].to_string(index=False))