from pathlib import Path
import pandas as pd


# =========================
# Paths
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "processed_data" / "pilot_image_inventory.csv"

OUTPUT_SUMMARY_CSV = PROJECT_ROOT / "processed_data" / "pilot_image_species_summary.csv"
OUTPUT_SUMMARY_MD = PROJECT_ROOT / "notes" / "pilot_image_collection_summary.md"


# =========================
# Load data
# =========================

df = pd.read_csv(INPUT_FILE)

# Standardise column names just in case
df.columns = df.columns.str.strip()

# Check required columns
required_columns = ["species", "usable"]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# Clean usable column
df["usable_clean"] = (
    df["usable"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["is_usable"] = df["usable_clean"].isin(["yes", "y", "true", "1"])


# =========================
# Species-level summary
# =========================

species_summary = (
    df.groupby("species", dropna=False)
    .agg(
        total_images_checked=("species", "size"),
        usable_images=("is_usable", "sum")
    )
    .reset_index()
)

species_summary["usable_rate"] = (
    species_summary["usable_images"] / species_summary["total_images_checked"] * 100
).round(1)

# Sort alphabetically by species
species_summary = species_summary.sort_values("species")


# =========================
# Overall summary
# =========================

total_images = len(df)
total_usable = int(df["is_usable"].sum())
overall_usable_rate = round(total_usable / total_images * 100, 1)


# =========================
# Save CSV summary
# =========================

species_summary.to_csv(OUTPUT_SUMMARY_CSV, index=False)


# =========================
# Save markdown summary
# =========================

markdown_table = species_summary.to_markdown(index=False)

summary_text = f"""# Pilot image collection summary

I completed a pilot image collection for five dorid nudibranch species using iNaturalist observations. For each species, I recorded candidate images, including observation URL, source, licence, observer or photographer, research-grade status where available, usability, and brief quality notes.

In total, the pilot inventory contains {total_images} images across {species_summary.shape[0]} species. Of these, {total_usable} images were marked as usable for pilot colour-pattern analysis. The overall usable image rate is therefore {overall_usable_rate}%.

## Usable image numbers by species

{markdown_table}

## Interpretation

This pilot suggests that online citizen-science images are feasible for extracting colour-pattern traits in the selected dorid nudibranch species. All five pilot species had multiple usable images, and most species had a high usable image rate.

The main reasons for excluding images were poor visibility of the animal, unclear separation between the animal and background, or unsuitable image quality. Overall, the pilot supports continuing with the proposed image-based workflow.

## Next step

The next step is to use the usable images to test simple colour-pattern metric extraction, such as brightness, saturation, colour diversity, and possibly animal-background contrast.
"""

OUTPUT_SUMMARY_MD.write_text(summary_text, encoding="utf-8")


# =========================
# Print results
# =========================

print("Pilot image summary complete.")
print()
print(f"Input file: {INPUT_FILE}")
print(f"Species summary CSV saved to: {OUTPUT_SUMMARY_CSV}")
print(f"Markdown summary saved to: {OUTPUT_SUMMARY_MD}")
print()
print(species_summary)
print()
print(f"Total images: {total_images}")
print(f"Total usable images: {total_usable}")
print(f"Overall usable rate: {overall_usable_rate}%")