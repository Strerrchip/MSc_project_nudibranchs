from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# Create pilot image inventory for D03 image collection
# ------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_DIR / "processed_data"

# Input file created from D03
species_list_file = PROCESSED_DIR / "species_for_image_collection.csv"

print("Reading D03 species list:")
print(species_list_file)

species_list = pd.read_csv(species_list_file)

# Keep pilot species only
pilot_species = species_list[
    species_list["image_collection_priority"] == "pilot"
].copy()

print("\nPilot species:")
print(pilot_species["species"].tolist())

print("\nNumber of pilot species:")
print(len(pilot_species))

# Number of planned image slots per species
n_image_slots_per_species = 10

rows = []

for _, row in pilot_species.iterrows():
    species = row["species"]

    for image_number in range(1, n_image_slots_per_species + 1):
        rows.append({
            "species": species,
            "image_slot": image_number,
            "image_id": f"{species.replace(' ', '_')}_{image_number:02d}",
            "source": "",
            "image_url": "",
            "license": "",
            "photographer_or_observer": "",
            "date_accessed": "",
            "image_downloaded": "no",
            "usable": "",
            "exclusion_reason": "",
            "animal_clear": "",
            "background_clear": "",
            "notes": ""
        })

pilot_image_inventory = pd.DataFrame(rows)

# Save output
output_file = PROCESSED_DIR / "pilot_image_inventory.csv"

pilot_image_inventory.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved pilot image inventory to:")
print(output_file)

print("\nPilot image inventory shape:")
print(pilot_image_inventory.shape)

print("\nFirst 10 rows:")
print(pilot_image_inventory.head(10))