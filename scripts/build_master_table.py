# ============================================================
# Build master table for dorid nudibranch project
# Step 1: create file-level inventory
# Author: Avery
# ============================================================

from pathlib import Path
import pandas as pd


# ------------------------------------------------------------
# 1. Set project folders
# ------------------------------------------------------------

# This Python file is inside:
# MSc_project_nudibranchs/scripts/build_master_table.py
#
# parents[1] means:
# go up from scripts/ to MSc_project_nudibranchs/

PROJECT_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_DIR / "raw_data"
NOTES_DIR = PROJECT_DIR / "notes"
PROCESSED_DIR = PROJECT_DIR / "processed_data"

NOTES_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)


print("Project folder:")
print(PROJECT_DIR)

print("\nRaw data folder:")
print(RAW_DIR)


# ------------------------------------------------------------
# 2. Scan all files in raw_data
# ------------------------------------------------------------

file_records = []

for file_path in RAW_DIR.rglob("*"):
    if file_path.is_file():

        relative_path = file_path.relative_to(PROJECT_DIR)

        file_records.append({
            "file_name": file_path.name,
            "relative_path": str(relative_path),
            "parent_folder": file_path.parent.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_kb": round(file_path.stat().st_size / 1024, 2)
        })


file_inventory = pd.DataFrame(file_records)


# ------------------------------------------------------------
# 3. Show result in terminal
# ------------------------------------------------------------

print("\nNumber of files found:")
print(len(file_inventory))

print("\nFile inventory:")
print(file_inventory)


# ------------------------------------------------------------
# 4. Save file inventory
# ------------------------------------------------------------

output_file = NOTES_DIR / "file_inventory.csv"

file_inventory.to_csv(output_file, index=False, encoding="utf-8-sig")

print("\nSaved file inventory to:")
print(output_file)

# ------------------------------------------------------------
# 5. Read Prieto-Baños & Layton 2025 Table 1
# ------------------------------------------------------------

prieto_file = (
    RAW_DIR
    / "Prieto_Banos_Layton_2025"
    / "Prieto-Baños & Layton 2025 Table 1.xlsx"
)

print("\nReading Prieto-Baños & Layton 2025 Table 1...")
print(prieto_file)

prieto_raw = pd.read_excel(prieto_file)

print("\nPrieto table shape:")
print(prieto_raw.shape)

print("\nPrieto table columns:")
print(prieto_raw.columns.tolist())

print("\nFirst 5 rows:")
print(prieto_raw.head())

# ------------------------------------------------------------
# 6. Clean Prieto-Baños table
# ------------------------------------------------------------

prieto = prieto_raw.copy()

# Rename useful columns
prieto = prieto.rename(columns={
    "<b>Species</b>": "raw_species",
    "<b>Prey Group</b>": "prey_group",
    "<b>Chemical Acquisition</b>": "chemical_acquisition",
    "<b>Colour Pattern</b>": "colour_pattern"
})

# Keep only useful columns for now
prieto = prieto[[
    "raw_species",
    "prey_group",
    "chemical_acquisition",
    "colour_pattern"
]]

# Remove HTML tags from all text columns
for col in prieto.columns:
    prieto[col] = (
        prieto[col]
        .astype("string")
        .str.replace("<b>", "", regex=False)
        .str.replace("</b>", "", regex=False)
        .str.replace("<i>", "", regex=False)
        .str.replace("</i>", "", regex=False)
        .str.strip()
    )

# Convert empty strings and strange missing values to proper missing values
prieto = prieto.replace({
    "": pd.NA,
    "nan": pd.NA,
    "NaN": pd.NA,
    "<NA>": pd.NA
})

# Identify family rows
prieto["is_family_row"] = (
    prieto["raw_species"].notna()
    & prieto["raw_species"].str.endswith("idae")
)

# Create family column and fill down
prieto["family"] = prieto["raw_species"].where(prieto["is_family_row"])
prieto["family"] = prieto["family"].ffill()

# Keep only species rows
prieto_species = prieto[
    prieto["raw_species"].notna()
    & ~prieto["is_family_row"]
].copy()

# Rename raw_species to species
prieto_species = prieto_species.rename(columns={
    "raw_species": "species"
})

# Add source information
prieto_species["source_dataset"] = "Prieto_Banos_Layton_2025"
prieto_species["data_level"] = "species_or_representative_taxon"

# Reorder columns
prieto_species = prieto_species[[
    "species",
    "family",
    "prey_group",
    "chemical_acquisition",
    "colour_pattern",
    "source_dataset",
    "data_level"
]]

print("\nCleaned Prieto table:")
print(prieto_species.head(15))

print("\nNumber of cleaned Prieto rows:")
print(len(prieto_species))

# Save cleaned Prieto table
prieto_output = PROCESSED_DIR / "prieto_cleaned.csv"

prieto_species.to_csv(prieto_output, index=False, encoding="utf-8-sig")

print("\nSaved cleaned Prieto table to:")
print(prieto_output)

# ------------------------------------------------------------
# 7. Save first version of master table
# ------------------------------------------------------------

master_table_v1 = prieto_species.copy()

master_output = PROCESSED_DIR / "master_table_v1.csv"

master_table_v1.to_csv(master_output, index=False, encoding="utf-8-sig")

print("\nSaved first master table to:")
print(master_output)

# ------------------------------------------------------------
# 8. Read chemical defence modes Table_S1
# ------------------------------------------------------------

table_s1_file = (
    RAW_DIR
    / "UQ_datasets"
    / "chemical_defence_modes"
    / "Table_S1.xlsx"
)

print("\nReading chemical defence modes Table_S1...")
print(table_s1_file)

table_s1_raw = pd.read_excel(table_s1_file)

print("\nTable_S1 shape:")
print(table_s1_raw.shape)

print("\nTable_S1 columns:")
print(table_s1_raw.columns.tolist())

print("\nFirst 5 rows of Table_S1:")
print(table_s1_raw.head())

# Show more columns and rows for Table_S1 inspection
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print("\nFirst 15 rows of Table_S1 with all columns:")
print(table_s1_raw.head(15))

# ------------------------------------------------------------
# 9. Clean chemical defence modes Table_S1
# ------------------------------------------------------------

table_s1 = table_s1_raw.copy()

# Rename columns manually based on their positions
# This avoids problems caused by complex Excel headers such as "Unnamed: 9"
table_s1.columns = [
    "family",
    "species",
    "authority",
    "extract_id",
    "specimen_id",
    "experimenter",
    "body_part",
    "natural_concentration_mg_ml",
    "unpalatability_ps_ed50",
    "unpalatability_tf_ed50",
    "unpalatability_extra",
    "toxicity_ed50",
    "toxicity_extra",
    "chemical_defence_class",
    "number_of_individuals",
    "mean_size_mm_st_dev",
    "collection_location",
    "coordinates"
]

# Remove the first two rows because they are header notes, not species data
table_s1 = table_s1.iloc[2:].copy()

# Fill family name downwards
# In the original Excel, family is only written once for a group of species
table_s1["family"] = table_s1["family"].ffill()

# Keep only rows with a species name
table_s1 = table_s1[table_s1["species"].notna()].copy()

# Clean species names
table_s1["species_original"] = table_s1["species"].astype(str).str.strip()

# Remove duplicate labels such as "(1)" and "(2)" from species names
# Example: "Ardeadoris egretta (1)" -> "Ardeadoris egretta"
table_s1["species"] = (
    table_s1["species_original"]
    .str.replace(r"\s*\(\d+\)$", "", regex=True)
    .str.strip()
)

# Add source information
table_s1["source_dataset"] = "chemical_defence_modes_Table_S1"

# Select useful columns
table_s1_cleaned = table_s1[[
    "species",
    "species_original",
    "family",
    "authority",
    "extract_id",
    "body_part",
    "natural_concentration_mg_ml",
    "unpalatability_ps_ed50",
    "unpalatability_tf_ed50",
    "unpalatability_extra",
    "toxicity_ed50",
    "toxicity_extra",
    "chemical_defence_class",
    "number_of_individuals",
    "mean_size_mm_st_dev",
    "collection_location",
    "coordinates",
    "source_dataset"
]].copy()

print("\nCleaned Table_S1:")
print(table_s1_cleaned.head(15))

print("\nNumber of cleaned Table_S1 rows:")
print(len(table_s1_cleaned))

print("\nCleaned Table_S1 columns:")
print(table_s1_cleaned.columns.tolist())


# ------------------------------------------------------------
# 10. Save cleaned Table_S1
# ------------------------------------------------------------

table_s1_output = PROCESSED_DIR / "table_s1_cleaned.csv"

table_s1_cleaned.to_csv(table_s1_output, index=False, encoding="utf-8-sig")

print("\nSaved cleaned Table_S1 to:")
print(table_s1_output)

# ------------------------------------------------------------
# 11. Check species overlap between Prieto master table and Table_S1
# ------------------------------------------------------------

# Get unique species names from Prieto master table
prieto_species_list = (
    master_table_v1[["species"]]
    .drop_duplicates()
    .copy()
)

prieto_species_list["in_prieto_master"] = True

# Get unique species names from Table_S1
table_s1_species_list = (
    table_s1_cleaned[["species"]]
    .drop_duplicates()
    .copy()
)

table_s1_species_list["in_table_s1"] = True

# Full outer merge to see matches and non-matches
species_overlap = prieto_species_list.merge(
    table_s1_species_list,
    on="species",
    how="outer"
)

species_overlap["in_prieto_master"] = species_overlap["in_prieto_master"].fillna(False)
species_overlap["in_table_s1"] = species_overlap["in_table_s1"].fillna(False)

# Add match category
species_overlap["match_status"] = "unmatched"

species_overlap.loc[
    species_overlap["in_prieto_master"] & species_overlap["in_table_s1"],
    "match_status"
] = "matched"

species_overlap.loc[
    species_overlap["in_prieto_master"] & ~species_overlap["in_table_s1"],
    "match_status"
] = "only_in_prieto"

species_overlap.loc[
    ~species_overlap["in_prieto_master"] & species_overlap["in_table_s1"],
    "match_status"
] = "only_in_table_s1"

print("\nSpecies overlap summary:")
print(species_overlap["match_status"].value_counts())

print("\nMatched species:")
print(species_overlap[species_overlap["match_status"] == "matched"].head(20))

# Save species overlap table
species_overlap_output = PROCESSED_DIR / "species_overlap_prieto_table_s1.csv"

species_overlap.to_csv(species_overlap_output, index=False, encoding="utf-8-sig")

print("\nSaved species overlap table to:")
print(species_overlap_output)

# ------------------------------------------------------------
# 12. Save unmatched species lists for manual inspection
# ------------------------------------------------------------

only_in_prieto = species_overlap[
    species_overlap["match_status"] == "only_in_prieto"
].copy()

only_in_table_s1 = species_overlap[
    species_overlap["match_status"] == "only_in_table_s1"
].copy()

only_in_prieto_output = PROCESSED_DIR / "only_in_prieto.csv"
only_in_table_s1_output = PROCESSED_DIR / "only_in_table_s1.csv"

only_in_prieto.to_csv(only_in_prieto_output, index=False, encoding="utf-8-sig")
only_in_table_s1.to_csv(only_in_table_s1_output, index=False, encoding="utf-8-sig")

print("\nSaved unmatched Prieto species to:")
print(only_in_prieto_output)

print("\nSaved unmatched Table_S1 species to:")
print(only_in_table_s1_output)

print("\nFirst 20 species only in Prieto:")
print(only_in_prieto["species"].head(20).tolist())

print("\nFirst 20 species only in Table_S1:")
print(only_in_table_s1["species"].head(20).tolist())

# ------------------------------------------------------------
# 13. Summarise Table_S1 to species level
# ------------------------------------------------------------

table_s1_species_summary = (
    table_s1_cleaned
    .groupby("species", as_index=False)
    .agg({
        "species_original": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "family": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "authority": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "body_part": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "chemical_defence_class": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "unpalatability_ps_ed50": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "unpalatability_tf_ed50": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "unpalatability_extra": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "toxicity_ed50": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "toxicity_extra": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "number_of_individuals": "sum",
        "collection_location": lambda x: "; ".join(sorted(set(x.dropna().astype(str)))),
        "coordinates": lambda x: "; ".join(sorted(set(x.dropna().astype(str))))
    })
)

table_s1_species_summary["source_dataset"] = "chemical_defence_modes_Table_S1_species_summary"

print("\nTable_S1 species-level summary:")
print(table_s1_species_summary.head(15))

print("\nNumber of species in Table_S1 summary:")
print(len(table_s1_species_summary))

table_s1_species_summary_output = PROCESSED_DIR / "table_s1_species_summary.csv"

table_s1_species_summary.to_csv(
    table_s1_species_summary_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved Table_S1 species-level summary to:")
print(table_s1_species_summary_output)

# ------------------------------------------------------------
# 14. Check genus-level overlap between Prieto and Table_S1
# ------------------------------------------------------------

# Add genus column to Prieto master table
prieto_genus = master_table_v1.copy()
prieto_genus["genus"] = prieto_genus["species"].astype(str).str.split().str[0]

# Add genus column to Table_S1 species summary
table_s1_genus = table_s1_species_summary.copy()
table_s1_genus["genus"] = table_s1_genus["species"].astype(str).str.split().str[0]

# Unique genus lists
prieto_genus_list = (
    prieto_genus[["genus"]]
    .drop_duplicates()
    .copy()
)
prieto_genus_list["in_prieto_master"] = True

table_s1_genus_list = (
    table_s1_genus[["genus"]]
    .drop_duplicates()
    .copy()
)
table_s1_genus_list["in_table_s1"] = True

# Merge genus lists
genus_overlap = prieto_genus_list.merge(
    table_s1_genus_list,
    on="genus",
    how="outer"
)

genus_overlap["in_prieto_master"] = genus_overlap["in_prieto_master"].fillna(False)
genus_overlap["in_table_s1"] = genus_overlap["in_table_s1"].fillna(False)

genus_overlap["match_status"] = "unmatched"

genus_overlap.loc[
    genus_overlap["in_prieto_master"] & genus_overlap["in_table_s1"],
    "match_status"
] = "matched_genus"

genus_overlap.loc[
    genus_overlap["in_prieto_master"] & ~genus_overlap["in_table_s1"],
    "match_status"
] = "only_in_prieto"

genus_overlap.loc[
    ~genus_overlap["in_prieto_master"] & genus_overlap["in_table_s1"],
    "match_status"
] = "only_in_table_s1"

print("\nGenus overlap summary:")
print(genus_overlap["match_status"].value_counts())

print("\nMatched genera:")
print(genus_overlap[genus_overlap["match_status"] == "matched_genus"])

genus_overlap_output = PROCESSED_DIR / "genus_overlap_prieto_table_s1.csv"

genus_overlap.to_csv(genus_overlap_output, index=False, encoding="utf-8-sig")

print("\nSaved genus overlap table to:")
print(genus_overlap_output)

# ------------------------------------------------------------
# 15. Improve species-name matching between Prieto and Table_S1
# ------------------------------------------------------------

import re

def clean_species_name_for_matching(name):
    """
    Clean species names for matching.
    This removes annotations such as:
    - Ardeadoris egretta (1)
    - Dendrodoris krusensternii (=denisoni)
    - Notodoris (=Aegires) gardineri
    """
    if pd.isna(name):
        return pd.NA

    name = str(name).strip()

    # Remove numbering at the end, e.g. "Ardeadoris egretta (1)"
    name = re.sub(r"\s*\(\d+\)$", "", name)

    # Remove synonym notes in brackets, e.g. "(=denisoni)" or "(=Aegires)"
    name = re.sub(r"\s*\(=.*?\)", "", name)

    # Remove extra spaces
    name = re.sub(r"\s+", " ", name).strip()

    return name


# Make cleaned names in Prieto
prieto_name_check = master_table_v1[["species"]].drop_duplicates().copy()
prieto_name_check["species_clean"] = prieto_name_check["species"].apply(clean_species_name_for_matching)
prieto_name_check["genus"] = prieto_name_check["species_clean"].astype(str).str.split().str[0]
prieto_name_check["specific_epithet"] = prieto_name_check["species_clean"].astype(str).str.split().str[1]

# Make cleaned names in Table_S1 species summary
table_s1_name_check = table_s1_species_summary[["species"]].drop_duplicates().copy()
table_s1_name_check["species_clean"] = table_s1_name_check["species"].apply(clean_species_name_for_matching)
table_s1_name_check["genus"] = table_s1_name_check["species_clean"].astype(str).str.split().str[0]
table_s1_name_check["specific_epithet"] = table_s1_name_check["species_clean"].astype(str).str.split().str[1]


# Check exact match after cleaning
cleaned_species_overlap = prieto_name_check.merge(
    table_s1_name_check,
    on="species_clean",
    how="outer",
    suffixes=("_prieto", "_table_s1")
)

cleaned_species_overlap["in_prieto"] = cleaned_species_overlap["species_prieto"].notna()
cleaned_species_overlap["in_table_s1"] = cleaned_species_overlap["species_table_s1"].notna()

cleaned_species_overlap["match_status"] = "unmatched"

cleaned_species_overlap.loc[
    cleaned_species_overlap["in_prieto"] & cleaned_species_overlap["in_table_s1"],
    "match_status"
] = "matched_after_cleaning"

cleaned_species_overlap.loc[
    cleaned_species_overlap["in_prieto"] & ~cleaned_species_overlap["in_table_s1"],
    "match_status"
] = "only_in_prieto"

cleaned_species_overlap.loc[
    ~cleaned_species_overlap["in_prieto"] & cleaned_species_overlap["in_table_s1"],
    "match_status"
] = "only_in_table_s1"


print("\nCleaned species-name overlap summary:")
print(cleaned_species_overlap["match_status"].value_counts())

print("\nMatched species after name cleaning:")
print(
    cleaned_species_overlap[
        cleaned_species_overlap["match_status"] == "matched_after_cleaning"
    ][["species_clean", "species_prieto", "species_table_s1"]]
)


cleaned_species_overlap_output = PROCESSED_DIR / "cleaned_species_overlap_prieto_table_s1.csv"

cleaned_species_overlap.to_csv(
    cleaned_species_overlap_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved cleaned species overlap table to:")
print(cleaned_species_overlap_output)

# ------------------------------------------------------------
# 15. Read colour_defence_2024 dataset
# ------------------------------------------------------------

colour_defence_file = (
    RAW_DIR
    / "UQ_datasets"
    / "colour_defence_2024"
    / "Data for 'Chemical defences indicate distinct colour patterns with reduced variability in aposematic nudibranchs'.csv"
)

print("\nReading colour_defence_2024 dataset...")
print(colour_defence_file)

colour_defence_raw = pd.read_csv(colour_defence_file)

print("\nColour defence table shape:")
print(colour_defence_raw.shape)

print("\nColour defence table columns:")
print(colour_defence_raw.columns.tolist())

print("\nFirst 5 rows of key columns:")
print(colour_defence_raw[["Species", "Individual", "database", "site", "daytime"]].head())

# ------------------------------------------------------------
# 16. Clean colour_defence_2024 dataset
# ------------------------------------------------------------

colour_defence = colour_defence_raw.copy()

# Clean column names
colour_defence.columns = (
    colour_defence.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(".", "_", regex=False)
    .str.replace(" ", "_", regex=False)
    .str.replace("-", "_", regex=False)
)

print("\nCleaned colour_defence_2024 column names:")
print(colour_defence.columns.tolist()[-10:])

print("\nKey columns after cleaning:")
print(colour_defence[["species", "individual", "database", "site", "daytime"]].head())

# Add source information
colour_defence["source_dataset"] = "colour_defence_2024"

# Save cleaned individual-level dataset
colour_defence_output = PROCESSED_DIR / "colour_defence_2024_cleaned.csv"

colour_defence.to_csv(
    colour_defence_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved cleaned colour_defence_2024 dataset to:")
print(colour_defence_output)

print("\nNumber of rows in colour_defence_2024:")
print(len(colour_defence))

print("\nNumber of unique species in colour_defence_2024:")
print(colour_defence["species"].nunique())

print("\nFirst 20 species in colour_defence_2024:")
print(sorted(colour_defence["species"].dropna().unique())[:20])

# ------------------------------------------------------------
# 17. Summarise colour_defence_2024 to species level
# ------------------------------------------------------------

# Identify numeric columns
numeric_cols = colour_defence.select_dtypes(include="number").columns.tolist()

# Remove non-trait numeric columns if needed
# For now, keep all numeric visual metrics and summarise their mean by species

colour_defence_species_summary = (
    colour_defence
    .groupby("species", as_index=False)
    .agg(
        n_records=("species", "size"),
        n_individuals=("individual", "nunique"),
        databases=("database", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        sites=("site", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        daytimes=("daytime", lambda x: "; ".join(sorted(set(x.dropna().astype(str)))))
    )
)

colour_defence_species_summary["source_dataset"] = "colour_defence_2024_species_summary"

print("\nColour_defence_2024 species-level summary:")
print(colour_defence_species_summary.head(20))

print("\nNumber of species in colour_defence_2024 summary:")
print(len(colour_defence_species_summary))

colour_defence_species_summary_output = PROCESSED_DIR / "colour_defence_2024_species_summary.csv"

colour_defence_species_summary.to_csv(
    colour_defence_species_summary_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved colour_defence_2024 species-level summary to:")
print(colour_defence_species_summary_output)

# ------------------------------------------------------------
# 18. Check species overlap: D04 with Prieto and Table_S1
# ------------------------------------------------------------

# D04 species list
d04_species = colour_defence_species_summary[["species"]].drop_duplicates().copy()
d04_species["in_d04"] = True

# Prieto species list
prieto_species_for_d04 = master_table_v1[["species"]].drop_duplicates().copy()
prieto_species_for_d04["in_prieto"] = True

# Table_S1 species list
table_s1_species_for_d04 = table_s1_species_summary[["species"]].drop_duplicates().copy()
table_s1_species_for_d04["in_table_s1"] = True

# D04 vs Prieto
d04_prieto_overlap = d04_species.merge(
    prieto_species_for_d04,
    on="species",
    how="outer"
)

d04_prieto_overlap["in_d04"] = d04_prieto_overlap["in_d04"].fillna(False)
d04_prieto_overlap["in_prieto"] = d04_prieto_overlap["in_prieto"].fillna(False)

d04_prieto_overlap["match_status"] = "unmatched"

d04_prieto_overlap.loc[
    d04_prieto_overlap["in_d04"] & d04_prieto_overlap["in_prieto"],
    "match_status"
] = "matched"

d04_prieto_overlap.loc[
    d04_prieto_overlap["in_d04"] & ~d04_prieto_overlap["in_prieto"],
    "match_status"
] = "only_in_d04"

d04_prieto_overlap.loc[
    ~d04_prieto_overlap["in_d04"] & d04_prieto_overlap["in_prieto"],
    "match_status"
] = "only_in_prieto"

print("\nD04 vs Prieto species overlap summary:")
print(d04_prieto_overlap["match_status"].value_counts())

d04_prieto_overlap_output = PROCESSED_DIR / "species_overlap_d04_prieto.csv"

d04_prieto_overlap.to_csv(
    d04_prieto_overlap_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D04 vs Prieto overlap table to:")
print(d04_prieto_overlap_output)


# D04 vs Table_S1
d04_table_s1_overlap = d04_species.merge(
    table_s1_species_for_d04,
    on="species",
    how="outer"
)

d04_table_s1_overlap["in_d04"] = d04_table_s1_overlap["in_d04"].fillna(False)
d04_table_s1_overlap["in_table_s1"] = d04_table_s1_overlap["in_table_s1"].fillna(False)

d04_table_s1_overlap["match_status"] = "unmatched"

d04_table_s1_overlap.loc[
    d04_table_s1_overlap["in_d04"] & d04_table_s1_overlap["in_table_s1"],
    "match_status"
] = "matched"

d04_table_s1_overlap.loc[
    d04_table_s1_overlap["in_d04"] & ~d04_table_s1_overlap["in_table_s1"],
    "match_status"
] = "only_in_d04"

d04_table_s1_overlap.loc[
    ~d04_table_s1_overlap["in_d04"] & d04_table_s1_overlap["in_table_s1"],
    "match_status"
] = "only_in_table_s1"

print("\nD04 vs Table_S1 species overlap summary:")
print(d04_table_s1_overlap["match_status"].value_counts())

print("\nMatched species between D04 and Table_S1:")
print(d04_table_s1_overlap[d04_table_s1_overlap["match_status"] == "matched"])

d04_table_s1_overlap_output = PROCESSED_DIR / "species_overlap_d04_table_s1.csv"

d04_table_s1_overlap.to_csv(
    d04_table_s1_overlap_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D04 vs Table_S1 overlap table to:")
print(d04_table_s1_overlap_output)

# ------------------------------------------------------------
# 19. Create species-level mean colour metrics for D04
# ------------------------------------------------------------

# Columns that identify records, not visual metrics
non_metric_cols = [
    "roi",
    "dist",
    "species",
    "individual",
    "database",
    "site",
    "daytime",
    "source_dataset"
]

# Select numeric metric columns only
metric_cols = [
    col for col in colour_defence.columns
    if col not in non_metric_cols and pd.api.types.is_numeric_dtype(colour_defence[col])
]

print("\nNumber of numeric colour metric columns in D04:")
print(len(metric_cols))

print("\nFirst 20 numeric colour metric columns:")
print(metric_cols[:20])

# Mean of each numeric colour metric by species
d04_metric_means = (
    colour_defence
    .groupby("species", as_index=False)[metric_cols]
    .mean()
)

# Add prefix so these variables are clearly from D04
d04_metric_means = d04_metric_means.rename(
    columns={col: "d04_mean_" + col for col in metric_cols}
)

# Add sample size information
d04_sample_sizes = (
    colour_defence
    .groupby("species", as_index=False)
    .agg(
        d04_n_records=("species", "size"),
        d04_n_individuals=("individual", "nunique"),
        d04_databases=("database", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        d04_sites=("site", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        d04_daytimes=("daytime", lambda x: "; ".join(sorted(set(x.dropna().astype(str)))))
    )
)

# Merge sample size information with metric means
d04_species_metrics_summary = d04_sample_sizes.merge(
    d04_metric_means,
    on="species",
    how="left"
)

d04_species_metrics_summary["source_dataset"] = "colour_defence_2024_species_metrics_summary"

print("\nD04 species-level metrics summary shape:")
print(d04_species_metrics_summary.shape)

print("\nD04 species-level metrics summary first 5 rows:")
print(d04_species_metrics_summary.head())

d04_species_metrics_summary_output = PROCESSED_DIR / "colour_defence_2024_species_metrics_summary.csv"

d04_species_metrics_summary.to_csv(
    d04_species_metrics_summary_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D04 species-level metrics summary to:")
print(d04_species_metrics_summary_output)

# ------------------------------------------------------------
# 20. Save a short D04 summary report
# ------------------------------------------------------------

d04_summary_report = PROCESSED_DIR / "d04_summary_report.txt"

with open(d04_summary_report, "w", encoding="utf-8") as f:
    f.write("D04 colour_defence_2024 summary report\n")
    f.write("=====================================\n\n")

    f.write("Number of numeric colour metric columns in D04:\n")
    f.write(str(len(metric_cols)))
    f.write("\n\n")

    f.write("First 20 numeric colour metric columns:\n")
    f.write(str(metric_cols[:20]))
    f.write("\n\n")

    f.write("D04 species-level metrics summary shape:\n")
    f.write(str(d04_species_metrics_summary.shape))
    f.write("\n\n")

    f.write("D04 species-level metrics summary first 5 rows:\n")
    f.write(d04_species_metrics_summary.head().to_string())
    f.write("\n\n")

    f.write("Saved D04 species-level metrics summary file:\n")
    f.write(str(d04_species_metrics_summary_output))
    f.write("\n")

print("\n" + "=" * 60)
print("SHORT D04 SUMMARY SAVED TO:")
print(d04_summary_report)
print("=" * 60)

# ------------------------------------------------------------
# 21. Merge D03 Table_S1 chemical defence with D04 colour metrics
# ------------------------------------------------------------

d03_d04_matched = table_s1_species_summary.merge(
    d04_species_metrics_summary,
    on="species",
    how="inner",
    suffixes=("_d03", "_d04")
)

print("\nD03 + D04 matched species dataset shape:")
print(d03_d04_matched.shape)

print("\nMatched species in D03 + D04:")
print(d03_d04_matched["species"].tolist())

print("\nD03 + D04 first rows:")
print(d03_d04_matched[[
    "species",
    "chemical_defence_class",
    "unpalatability_ps_ed50",
    "toxicity_ed50",
    "d04_n_records",
    "d04_n_individuals",
    "d04_mean_col_mean",
    "d04_mean_lum_mean"
]].head(20))

d03_d04_output = PROCESSED_DIR / "chemical_defence_colour_metrics_matched_species.csv"

d03_d04_matched.to_csv(
    d03_d04_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D03 + D04 matched species dataset to:")
print(d03_d04_output)

# ------------------------------------------------------------
# 22. Read D05 detectability_boldness_2023 datasets
# ------------------------------------------------------------

d05_dir = RAW_DIR / "UQ_datasets" / "detectability_boldness_2023"

boldness_file = d05_dir / "data_boldness.csv"
detection_file = d05_dir / "data_detection.csv"
tox_file = d05_dir / "tox_data.xlsx"

print("\nReading D05 detectability_boldness_2023 datasets...")

print("\nBoldness file:")
print(boldness_file)
boldness_raw = pd.read_csv(boldness_file)

print("\nDetection file:")
print(detection_file)
detection_raw = pd.read_csv(detection_file)

print("\nToxicity file:")
print(tox_file)
tox_raw = pd.read_excel(tox_file)

print("\nD05 boldness shape:")
print(boldness_raw.shape)

print("\nD05 detection shape:")
print(detection_raw.shape)

print("\nD05 toxicity shape:")
print(tox_raw.shape)

print("\nD05 boldness columns:")
print(boldness_raw.columns.tolist())

print("\nD05 detection columns:")
print(detection_raw.columns.tolist())

print("\nD05 toxicity columns:")
print(tox_raw.columns.tolist())

# ------------------------------------------------------------
# 23. Save D05 summary report
# ------------------------------------------------------------

d05_summary_report = PROCESSED_DIR / "d05_summary_report.txt"

with open(d05_summary_report, "w", encoding="utf-8") as f:
    f.write("D05 detectability_boldness_2023 summary report\n")
    f.write("=============================================\n\n")

    f.write("Boldness table shape:\n")
    f.write(str(boldness_raw.shape))
    f.write("\n\n")

    f.write("Boldness columns:\n")
    f.write(str(boldness_raw.columns.tolist()))
    f.write("\n\n")

    f.write("Boldness first 5 rows:\n")
    f.write(boldness_raw.head().to_string())
    f.write("\n\n")

    f.write("Detection table shape:\n")
    f.write(str(detection_raw.shape))
    f.write("\n\n")

    f.write("Detection columns:\n")
    f.write(str(detection_raw.columns.tolist()))
    f.write("\n\n")

    f.write("Detection first 5 rows:\n")
    f.write(detection_raw.head().to_string())
    f.write("\n\n")

    f.write("Toxicity table shape:\n")
    f.write(str(tox_raw.shape))
    f.write("\n\n")

    f.write("Toxicity columns:\n")
    f.write(str(tox_raw.columns.tolist()))
    f.write("\n\n")

    f.write("Toxicity first 5 rows:\n")
    f.write(tox_raw.head().to_string())
    f.write("\n\n")

print("\n" + "=" * 60)
print("SHORT D05 SUMMARY SAVED TO:")
print(d05_summary_report)
print("=" * 60)

# ------------------------------------------------------------
# 24. Save compact D05 column and species check report
# ------------------------------------------------------------

d05_column_check_report = PROCESSED_DIR / "d05_column_check_report.txt"

with open(d05_column_check_report, "w", encoding="utf-8") as f:
    f.write("D05 column and species check report\n")
    f.write("==================================\n\n")

    f.write("Boldness shape:\n")
    f.write(str(boldness_raw.shape))
    f.write("\n\n")

    f.write("Detection shape:\n")
    f.write(str(detection_raw.shape))
    f.write("\n\n")

    f.write("Toxicity shape:\n")
    f.write(str(tox_raw.shape))
    f.write("\n\n")

    f.write("Boldness last 20 columns:\n")
    f.write(str(boldness_raw.columns.tolist()[-20:]))
    f.write("\n\n")

    f.write("Detection last 20 columns:\n")
    f.write(str(detection_raw.columns.tolist()[-20:]))
    f.write("\n\n")

    f.write("Boldness first 5 rows, last 10 columns:\n")
    f.write(boldness_raw.iloc[:, -10:].head().to_string())
    f.write("\n\n")

    f.write("Detection first 5 rows, last 10 columns:\n")
    f.write(detection_raw.iloc[:, -10:].head().to_string())
    f.write("\n\n")

    f.write("Toxicity full table:\n")
    f.write(tox_raw.to_string())
    f.write("\n\n")

print("\n" + "=" * 60)
print("D05 COLUMN CHECK REPORT SAVED TO:")
print(d05_column_check_report)
print("=" * 60)

# ------------------------------------------------------------
# 25. Clean D05 detectability_boldness_2023 datasets
# ------------------------------------------------------------

def clean_column_names(df):
    df = df.copy()
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(".", "_", regex=False)
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


boldness = clean_column_names(boldness_raw)
detection = clean_column_names(detection_raw)
tox = clean_column_names(tox_raw)

# Rename the unnamed index-like column if present
if "unnamed:_0" in boldness.columns:
    boldness = boldness.rename(columns={"unnamed:_0": "record_id"})

if "unnamed:_0" in detection.columns:
    detection = detection.rename(columns={"unnamed:_0": "record_id"})

# Rename toxicity column to a clearer name
tox = tox.rename(columns={
    "unpal_shrimp": "d05_unpal_shrimp"
})

# Add source dataset labels
boldness["source_dataset"] = "detectability_boldness_2023_boldness"
detection["source_dataset"] = "detectability_boldness_2023_detection"
tox["source_dataset"] = "detectability_boldness_2023_toxicity"

# Save cleaned files
boldness_output = PROCESSED_DIR / "d05_boldness_cleaned.csv"
detection_output = PROCESSED_DIR / "d05_detection_cleaned.csv"
tox_output = PROCESSED_DIR / "d05_tox_data_cleaned.csv"

boldness.to_csv(boldness_output, index=False, encoding="utf-8-sig")
detection.to_csv(detection_output, index=False, encoding="utf-8-sig")
tox.to_csv(tox_output, index=False, encoding="utf-8-sig")

print("\nSaved D05 cleaned boldness data to:")
print(boldness_output)

print("\nSaved D05 cleaned detection data to:")
print(detection_output)

print("\nSaved D05 cleaned toxicity data to:")
print(tox_output)

print("\nD05 boldness cleaned columns, last 5:")
print(boldness.columns.tolist()[-5:])

print("\nD05 detection cleaned columns, last 5:")
print(detection.columns.tolist()[-5:])

print("\nD05 toxicity cleaned:")
print(tox)

# ------------------------------------------------------------
# 26. Create D05 species-level metrics summaries
# ------------------------------------------------------------

def create_d05_species_metrics_summary(df, dataset_label):
    """
    Create species-level summary for D05 boldness/detection data.
    Each species gets one row.
    Numeric metric columns are averaged.
    """

    non_metric_cols = [
        "record_id",
        "species",
        "distance",
        "individual",
        "source_dataset"
    ]

    metric_cols = [
        col for col in df.columns
        if col not in non_metric_cols and pd.api.types.is_numeric_dtype(df[col])
    ]

    print(f"\nNumber of numeric metric columns in {dataset_label}:")
    print(len(metric_cols))

    metric_means = (
        df
        .groupby("species", as_index=False)[metric_cols]
        .mean()
    )

    metric_means = metric_means.rename(
        columns={col: f"{dataset_label}_mean_" + col for col in metric_cols}
    )

    sample_sizes = (
        df
        .groupby("species", as_index=False)
        .agg(
            **{
                f"{dataset_label}_n_records": ("species", "size"),
                f"{dataset_label}_n_individuals": ("individual", "nunique"),
                f"{dataset_label}_distances": ("distance", lambda x: "; ".join(sorted(set(x.dropna().astype(str)))))
            }
        )
    )

    summary = sample_sizes.merge(
        metric_means,
        on="species",
        how="left"
    )

    summary["source_dataset"] = f"detectability_boldness_2023_{dataset_label}_species_summary"

    return summary


d05_boldness_species_summary = create_d05_species_metrics_summary(
    boldness,
    "d05_boldness"
)

d05_detection_species_summary = create_d05_species_metrics_summary(
    detection,
    "d05_detection"
)

boldness_species_output = PROCESSED_DIR / "d05_boldness_species_metrics_summary.csv"
detection_species_output = PROCESSED_DIR / "d05_detection_species_metrics_summary.csv"

d05_boldness_species_summary.to_csv(
    boldness_species_output,
    index=False,
    encoding="utf-8-sig"
)

d05_detection_species_summary.to_csv(
    detection_species_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nD05 boldness species summary shape:")
print(d05_boldness_species_summary.shape)

print("\nD05 detection species summary shape:")
print(d05_detection_species_summary.shape)

print("\nSaved D05 boldness species summary to:")
print(boldness_species_output)

print("\nSaved D05 detection species summary to:")
print(detection_species_output)

print("\nFirst 10 species in D05 boldness:")
print(d05_boldness_species_summary["species"].head(10).tolist())

print("\nFirst 10 species in D05 detection:")
print(d05_detection_species_summary["species"].head(10).tolist())

# ------------------------------------------------------------
# 27. Save short D05 cleaned summary report
# ------------------------------------------------------------

d05_cleaned_summary_report = PROCESSED_DIR / "d05_cleaned_summary_report.txt"

with open(d05_cleaned_summary_report, "w", encoding="utf-8") as f:
    f.write("D05 cleaned summary report\n")
    f.write("==========================\n\n")

    f.write("Boldness cleaned shape:\n")
    f.write(str(boldness.shape))
    f.write("\n\n")

    f.write("Detection cleaned shape:\n")
    f.write(str(detection.shape))
    f.write("\n\n")

    f.write("Toxicity cleaned shape:\n")
    f.write(str(tox.shape))
    f.write("\n\n")

    f.write("D05 boldness species summary shape:\n")
    f.write(str(d05_boldness_species_summary.shape))
    f.write("\n\n")

    f.write("D05 detection species summary shape:\n")
    f.write(str(d05_detection_species_summary.shape))
    f.write("\n\n")

    f.write("D05 toxicity species list:\n")
    f.write(str(tox["species"].tolist()))
    f.write("\n\n")

    f.write("First 10 species in D05 boldness summary:\n")
    f.write(str(d05_boldness_species_summary["species"].head(10).tolist()))
    f.write("\n\n")

    f.write("First 10 species in D05 detection summary:\n")
    f.write(str(d05_detection_species_summary["species"].head(10).tolist()))
    f.write("\n\n")

print("\n" + "=" * 60)
print("D05 CLEANED SUMMARY SAVED TO:")
print(d05_cleaned_summary_report)
print("=" * 60)

# ------------------------------------------------------------
# 28. Merge D05 toxicity, boldness, and detection summaries
# ------------------------------------------------------------

d05_combined_species_summary = tox.merge(
    d05_boldness_species_summary,
    on="species",
    how="left",
    suffixes=("", "_boldness")
)

d05_combined_species_summary = d05_combined_species_summary.merge(
    d05_detection_species_summary,
    on="species",
    how="left",
    suffixes=("", "_detection")
)

print("\nD05 combined species summary shape:")
print(d05_combined_species_summary.shape)

print("\nD05 combined species:")
print(d05_combined_species_summary["species"].tolist())

d05_combined_output = PROCESSED_DIR / "d05_combined_species_summary.csv"

d05_combined_species_summary.to_csv(
    d05_combined_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D05 combined species summary to:")
print(d05_combined_output)

# ------------------------------------------------------------
# 29. Check D05 overlap with D03 and D04
# ------------------------------------------------------------

d05_species = d05_combined_species_summary[["species"]].drop_duplicates().copy()
d05_species["in_d05"] = True

d03_species = table_s1_species_summary[["species"]].drop_duplicates().copy()
d03_species["in_d03_table_s1"] = True

d04_species = d04_species_metrics_summary[["species"]].drop_duplicates().copy()
d04_species["in_d04_colour"] = True

# D05 vs D03
d05_d03_overlap = d05_species.merge(
    d03_species,
    on="species",
    how="outer"
)

d05_d03_overlap["in_d05"] = d05_d03_overlap["in_d05"].fillna(False)
d05_d03_overlap["in_d03_table_s1"] = d05_d03_overlap["in_d03_table_s1"].fillna(False)

d05_d03_overlap["match_status"] = "unmatched"

d05_d03_overlap.loc[
    d05_d03_overlap["in_d05"] & d05_d03_overlap["in_d03_table_s1"],
    "match_status"
] = "matched"

d05_d03_overlap.loc[
    d05_d03_overlap["in_d05"] & ~d05_d03_overlap["in_d03_table_s1"],
    "match_status"
] = "only_in_d05"

d05_d03_overlap.loc[
    ~d05_d03_overlap["in_d05"] & d05_d03_overlap["in_d03_table_s1"],
    "match_status"
] = "only_in_d03"

print("\nD05 vs D03 species overlap summary:")
print(d05_d03_overlap["match_status"].value_counts())

print("\nMatched species between D05 and D03:")
print(d05_d03_overlap[d05_d03_overlap["match_status"] == "matched"]["species"].tolist())

d05_d03_overlap_output = PROCESSED_DIR / "species_overlap_d05_d03.csv"

d05_d03_overlap.to_csv(
    d05_d03_overlap_output,
    index=False,
    encoding="utf-8-sig"
)


# D05 vs D04
d05_d04_overlap = d05_species.merge(
    d04_species,
    on="species",
    how="outer"
)

d05_d04_overlap["in_d05"] = d05_d04_overlap["in_d05"].fillna(False)
d05_d04_overlap["in_d04_colour"] = d05_d04_overlap["in_d04_colour"].fillna(False)

d05_d04_overlap["match_status"] = "unmatched"

d05_d04_overlap.loc[
    d05_d04_overlap["in_d05"] & d05_d04_overlap["in_d04_colour"],
    "match_status"
] = "matched"

d05_d04_overlap.loc[
    d05_d04_overlap["in_d05"] & ~d05_d04_overlap["in_d04_colour"],
    "match_status"
] = "only_in_d05"

d05_d04_overlap.loc[
    ~d05_d04_overlap["in_d05"] & d05_d04_overlap["in_d04_colour"],
    "match_status"
] = "only_in_d04"

print("\nD05 vs D04 species overlap summary:")
print(d05_d04_overlap["match_status"].value_counts())

print("\nMatched species between D05 and D04:")
print(d05_d04_overlap[d05_d04_overlap["match_status"] == "matched"]["species"].tolist())

d05_d04_overlap_output = PROCESSED_DIR / "species_overlap_d05_d04.csv"

d05_d04_overlap.to_csv(
    d05_d04_overlap_output,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 30. Save D05 combined overlap report
# ------------------------------------------------------------

d05_overlap_report = PROCESSED_DIR / "d05_overlap_report.txt"

with open(d05_overlap_report, "w", encoding="utf-8") as f:
    f.write("D05 combined and overlap report\n")
    f.write("===============================\n\n")

    f.write("D05 combined species summary shape:\n")
    f.write(str(d05_combined_species_summary.shape))
    f.write("\n\n")

    f.write("D05 combined species list:\n")
    f.write(str(d05_combined_species_summary["species"].tolist()))
    f.write("\n\n")

    f.write("D05 vs D03 overlap summary:\n")
    f.write(d05_d03_overlap["match_status"].value_counts().to_string())
    f.write("\n\n")

    f.write("Matched species between D05 and D03:\n")
    f.write(str(d05_d03_overlap[d05_d03_overlap["match_status"] == "matched"]["species"].tolist()))
    f.write("\n\n")

    f.write("D05 vs D04 overlap summary:\n")
    f.write(d05_d04_overlap["match_status"].value_counts().to_string())
    f.write("\n\n")

    f.write("Matched species between D05 and D04:\n")
    f.write(str(d05_d04_overlap[d05_d04_overlap["match_status"] == "matched"]["species"].tolist()))
    f.write("\n\n")

print("\n" + "=" * 60)
print("D05 OVERLAP REPORT SAVED TO:")
print(d05_overlap_report)
print("=" * 60)

# ------------------------------------------------------------
# 31. Merge D03 Table_S1 with D05 combined species summary
# ------------------------------------------------------------

d03_d05_matched = table_s1_species_summary.merge(
    d05_combined_species_summary,
    on="species",
    how="inner",
    suffixes=("_d03", "_d05")
)

print("\nD03 + D05 matched species dataset shape:")
print(d03_d05_matched.shape)

print("\nMatched species in D03 + D05:")
print(d03_d05_matched["species"].tolist())

d03_d05_output = PROCESSED_DIR / "chemical_defence_d05_boldness_detection_matched_species.csv"

d03_d05_matched.to_csv(
    d03_d05_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D03 + D05 matched species dataset to:")
print(d03_d05_output)

# ------------------------------------------------------------
# 32. Create core dataset: species shared by D03, D04, and D05
# ------------------------------------------------------------

d03_d04_d05_core = (
    table_s1_species_summary
    .merge(
        d04_species_metrics_summary,
        on="species",
        how="inner",
        suffixes=("_d03", "_d04")
    )
    .merge(
        d05_combined_species_summary,
        on="species",
        how="inner",
        suffixes=("", "_d05")
    )
)

print("\nD03 + D04 + D05 core matched dataset shape:")
print(d03_d04_d05_core.shape)

print("\nCore matched species in D03 + D04 + D05:")
print(d03_d04_d05_core["species"].tolist())

d03_d04_d05_output = PROCESSED_DIR / "core_d03_d04_d05_matched_species.csv"

d03_d04_d05_core.to_csv(
    d03_d04_d05_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D03 + D04 + D05 core matched dataset to:")
print(d03_d04_d05_output)

# ------------------------------------------------------------
# 33. Save combined dataset report
# ------------------------------------------------------------

combined_dataset_report = PROCESSED_DIR / "combined_dataset_report.txt"

with open(combined_dataset_report, "w", encoding="utf-8") as f:
    f.write("Combined dataset report\n")
    f.write("=======================\n\n")

    f.write("D03 + D05 matched dataset shape:\n")
    f.write(str(d03_d05_matched.shape))
    f.write("\n\n")

    f.write("D03 + D05 matched species:\n")
    f.write(str(d03_d05_matched["species"].tolist()))
    f.write("\n\n")

    f.write("D03 + D04 + D05 core matched dataset shape:\n")
    f.write(str(d03_d04_d05_core.shape))
    f.write("\n\n")

    f.write("D03 + D04 + D05 core matched species:\n")
    f.write(str(d03_d04_d05_core["species"].tolist()))
    f.write("\n\n")

    f.write("Saved D03 + D05 file:\n")
    f.write(str(d03_d05_output))
    f.write("\n\n")

    f.write("Saved D03 + D04 + D05 core file:\n")
    f.write(str(d03_d04_d05_output))
    f.write("\n")

print("\n" + "=" * 60)
print("COMBINED DATASET REPORT SAVED TO:")
print(combined_dataset_report)
print("=" * 60)

# ------------------------------------------------------------
# 34. Read D06 habitat_background_2024 dataset
# ------------------------------------------------------------

d06_file = (
    RAW_DIR
    / "UQ_datasets"
    / "habitat_background_2024"
    / "Data for Highly defended nudibranchs’ escape’ to visually distinct background habitats.csv"
)

print("\nReading D06 habitat_background_2024 dataset...")
print(d06_file)

d06_raw = pd.read_csv(d06_file)

print("\nD06 habitat background shape:")
print(d06_raw.shape)

print("\nD06 habitat background columns:")
print(d06_raw.columns.tolist())

print("\nD06 first 5 rows:")
print(d06_raw.head())

# ------------------------------------------------------------
# 35. Save D06 summary report
# ------------------------------------------------------------

d06_summary_report = PROCESSED_DIR / "d06_summary_report.txt"

with open(d06_summary_report, "w", encoding="utf-8") as f:
    f.write("D06 habitat_background_2024 summary report\n")
    f.write("=========================================\n\n")

    f.write("D06 shape:\n")
    f.write(str(d06_raw.shape))
    f.write("\n\n")

    f.write("D06 columns:\n")
    f.write(str(d06_raw.columns.tolist()))
    f.write("\n\n")

    f.write("D06 first 5 rows:\n")
    f.write(d06_raw.head().to_string())
    f.write("\n\n")

    f.write("D06 last 20 columns:\n")
    f.write(str(d06_raw.columns.tolist()[-20:]))
    f.write("\n\n")

    f.write("D06 first 5 rows, last 10 columns:\n")
    f.write(d06_raw.iloc[:, -10:].head().to_string())
    f.write("\n\n")

print("\n" + "=" * 60)
print("D06 SUMMARY REPORT SAVED TO:")
print(d06_summary_report)
print("=" * 60)

# ------------------------------------------------------------
# 36. Clean D06 habitat_background_2024 dataset
# ------------------------------------------------------------

d06 = d06_raw.copy()

# Clean column names
d06.columns = (
    d06.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(".", "_", regex=False)
    .str.replace(" ", "_", regex=False)
    .str.replace("-", "_", regex=False)
)

# Rename individual ID column for consistency
if "ind_id" in d06.columns:
    d06 = d06.rename(columns={"ind_id": "individual"})

# Clean species names: replace underscores with spaces
d06["species"] = (
    d06["species"]
    .astype(str)
    .str.replace("_", " ", regex=False)
    .str.strip()
)

# Add source dataset
d06["source_dataset"] = "habitat_background_2024"

# Save cleaned D06
d06_cleaned_output = PROCESSED_DIR / "d06_habitat_background_cleaned.csv"

d06.to_csv(
    d06_cleaned_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved cleaned D06 habitat background data to:")
print(d06_cleaned_output)

print("\nD06 cleaned shape:")
print(d06.shape)

print("\nD06 cleaned key columns:")
print(d06[["species", "pal", "tox", "distance", "database", "individual"]].head())

# ------------------------------------------------------------
# 37. Create D06 species-level metrics summary
# ------------------------------------------------------------

d06_non_metric_cols = [
    "species",
    "pal",
    "tox",
    "distance",
    "database",
    "individual",
    "source_dataset"
]

d06_metric_cols = [
    col for col in d06.columns
    if col not in d06_non_metric_cols and pd.api.types.is_numeric_dtype(d06[col])
]

print("\nNumber of numeric metric columns in D06:")
print(len(d06_metric_cols))

print("\nFirst 20 numeric metric columns in D06:")
print(d06_metric_cols[:20])

# Mean visual metrics by species
d06_metric_means = (
    d06
    .groupby("species", as_index=False)[d06_metric_cols]
    .mean()
)

d06_metric_means = d06_metric_means.rename(
    columns={col: "d06_mean_" + col for col in d06_metric_cols}
)

# Species-level sample size and categorical summaries
d06_sample_sizes = (
    d06
    .groupby("species", as_index=False)
    .agg(
        d06_n_records=("species", "size"),
        d06_n_individuals=("individual", "nunique"),
        d06_pal_values=("pal", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        d06_tox_values=("tox", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        d06_distances=("distance", lambda x: "; ".join(sorted(set(x.dropna().astype(str))))),
        d06_databases=("database", lambda x: "; ".join(sorted(set(x.dropna().astype(str)))))
    )
)

d06_species_metrics_summary = d06_sample_sizes.merge(
    d06_metric_means,
    on="species",
    how="left"
)

d06_species_metrics_summary["source_dataset"] = "habitat_background_2024_species_metrics_summary"

d06_species_summary_output = PROCESSED_DIR / "d06_habitat_background_species_metrics_summary.csv"

d06_species_metrics_summary.to_csv(
    d06_species_summary_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nD06 species-level metrics summary shape:")
print(d06_species_metrics_summary.shape)

print("\nFirst 10 species in D06:")
print(d06_species_metrics_summary["species"].head(10).tolist())

print("\nSaved D06 species-level metrics summary to:")
print(d06_species_summary_output)

# ------------------------------------------------------------
# 38. Save D06 cleaned summary report
# ------------------------------------------------------------

d06_cleaned_summary_report = PROCESSED_DIR / "d06_cleaned_summary_report.txt"

with open(d06_cleaned_summary_report, "w", encoding="utf-8") as f:
    f.write("D06 cleaned summary report\n")
    f.write("==========================\n\n")

    f.write("D06 cleaned shape:\n")
    f.write(str(d06.shape))
    f.write("\n\n")

    f.write("Number of numeric metric columns in D06:\n")
    f.write(str(len(d06_metric_cols)))
    f.write("\n\n")

    f.write("D06 species-level metrics summary shape:\n")
    f.write(str(d06_species_metrics_summary.shape))
    f.write("\n\n")

    f.write("First 20 species in D06:\n")
    f.write(str(d06_species_metrics_summary["species"].head(20).tolist()))
    f.write("\n\n")

    f.write("D06 pal values:\n")
    f.write(str(sorted(d06["pal"].dropna().astype(str).unique())))
    f.write("\n\n")

    f.write("D06 tox values:\n")
    f.write(str(sorted(d06["tox"].dropna().astype(str).unique())))
    f.write("\n\n")

    f.write("Saved D06 cleaned file:\n")
    f.write(str(d06_cleaned_output))
    f.write("\n\n")

    f.write("Saved D06 species metrics summary file:\n")
    f.write(str(d06_species_summary_output))
    f.write("\n")

print("\n" + "=" * 60)
print("D06 CLEANED SUMMARY SAVED TO:")
print(d06_cleaned_summary_report)
print("=" * 60)

# ------------------------------------------------------------
# 39. Check D06 overlap with D03, D04, and D05
# ------------------------------------------------------------

d06_species = d06_species_metrics_summary[["species"]].drop_duplicates().copy()
d06_species["in_d06"] = True

d03_species = table_s1_species_summary[["species"]].drop_duplicates().copy()
d03_species["in_d03_table_s1"] = True

d04_species = d04_species_metrics_summary[["species"]].drop_duplicates().copy()
d04_species["in_d04_colour"] = True

d05_species = d05_combined_species_summary[["species"]].drop_duplicates().copy()
d05_species["in_d05"] = True


def make_overlap_table(left_df, right_df, left_col, right_col, label_left, label_right):
    overlap = left_df.merge(
        right_df,
        on="species",
        how="outer"
    )

    overlap[left_col] = overlap[left_col].fillna(False)
    overlap[right_col] = overlap[right_col].fillna(False)

    overlap["match_status"] = "unmatched"

    overlap.loc[
        overlap[left_col] & overlap[right_col],
        "match_status"
    ] = "matched"

    overlap.loc[
        overlap[left_col] & ~overlap[right_col],
        "match_status"
    ] = f"only_in_{label_left}"

    overlap.loc[
        ~overlap[left_col] & overlap[right_col],
        "match_status"
    ] = f"only_in_{label_right}"

    return overlap


# D06 vs D03
d06_d03_overlap = make_overlap_table(
    d06_species,
    d03_species,
    "in_d06",
    "in_d03_table_s1",
    "d06",
    "d03"
)

# D06 vs D04
d06_d04_overlap = make_overlap_table(
    d06_species,
    d04_species,
    "in_d06",
    "in_d04_colour",
    "d06",
    "d04"
)

# D06 vs D05
d06_d05_overlap = make_overlap_table(
    d06_species,
    d05_species,
    "in_d06",
    "in_d05",
    "d06",
    "d05"
)

print("\nD06 vs D03 species overlap summary:")
print(d06_d03_overlap["match_status"].value_counts())

print("\nMatched species between D06 and D03:")
print(d06_d03_overlap[d06_d03_overlap["match_status"] == "matched"]["species"].tolist())

print("\nD06 vs D04 species overlap summary:")
print(d06_d04_overlap["match_status"].value_counts())

print("\nMatched species between D06 and D04:")
print(d06_d04_overlap[d06_d04_overlap["match_status"] == "matched"]["species"].tolist())

print("\nD06 vs D05 species overlap summary:")
print(d06_d05_overlap["match_status"].value_counts())

print("\nMatched species between D06 and D05:")
print(d06_d05_overlap[d06_d05_overlap["match_status"] == "matched"]["species"].tolist())


# Save overlap tables
d06_d03_overlap_output = PROCESSED_DIR / "species_overlap_d06_d03.csv"
d06_d04_overlap_output = PROCESSED_DIR / "species_overlap_d06_d04.csv"
d06_d05_overlap_output = PROCESSED_DIR / "species_overlap_d06_d05.csv"

d06_d03_overlap.to_csv(d06_d03_overlap_output, index=False, encoding="utf-8-sig")
d06_d04_overlap.to_csv(d06_d04_overlap_output, index=False, encoding="utf-8-sig")
d06_d05_overlap.to_csv(d06_d05_overlap_output, index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# 40. Save D06 overlap report
# ------------------------------------------------------------

d06_overlap_report = PROCESSED_DIR / "d06_overlap_report.txt"

with open(d06_overlap_report, "w", encoding="utf-8") as f:
    f.write("D06 overlap report\n")
    f.write("==================\n\n")

    f.write("D06 species list:\n")
    f.write(str(d06_species_metrics_summary["species"].tolist()))
    f.write("\n\n")

    f.write("D06 vs D03 overlap summary:\n")
    f.write(d06_d03_overlap["match_status"].value_counts().to_string())
    f.write("\n\n")

    f.write("Matched species between D06 and D03:\n")
    f.write(str(d06_d03_overlap[d06_d03_overlap["match_status"] == "matched"]["species"].tolist()))
    f.write("\n\n")

    f.write("D06 vs D04 overlap summary:\n")
    f.write(d06_d04_overlap["match_status"].value_counts().to_string())
    f.write("\n\n")

    f.write("Matched species between D06 and D04:\n")
    f.write(str(d06_d04_overlap[d06_d04_overlap["match_status"] == "matched"]["species"].tolist()))
    f.write("\n\n")

    f.write("D06 vs D05 overlap summary:\n")
    f.write(d06_d05_overlap["match_status"].value_counts().to_string())
    f.write("\n\n")

    f.write("Matched species between D06 and D05:\n")
    f.write(str(d06_d05_overlap[d06_d05_overlap["match_status"] == "matched"]["species"].tolist()))
    f.write("\n\n")

print("\n" + "=" * 60)
print("D06 OVERLAP REPORT SAVED TO:")
print(d06_overlap_report)
print("=" * 60)

# ------------------------------------------------------------
# 41. Merge D05 combined species summary with D06 species summary
# ------------------------------------------------------------

d05_d06_matched = d05_combined_species_summary.merge(
    d06_species_metrics_summary,
    on="species",
    how="inner",
    suffixes=("_d05", "_d06")
)

print("\nD05 + D06 matched species dataset shape:")
print(d05_d06_matched.shape)

print("\nMatched species in D05 + D06:")
print(d05_d06_matched["species"].tolist())

d05_d06_output = PROCESSED_DIR / "d05_d06_matched_species_summary.csv"

d05_d06_matched.to_csv(
    d05_d06_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D05 + D06 matched species dataset to:")
print(d05_d06_output)

# ------------------------------------------------------------
# 42. Create D03 + D05 + D06 core matched dataset
# ------------------------------------------------------------

d03_d05_d06_core = (
    table_s1_species_summary
    .merge(
        d05_combined_species_summary,
        on="species",
        how="inner",
        suffixes=("_d03", "_d05")
    )
    .merge(
        d06_species_metrics_summary,
        on="species",
        how="inner",
        suffixes=("", "_d06")
    )
)

print("\nD03 + D05 + D06 core matched dataset shape:")
print(d03_d05_d06_core.shape)

print("\nCore matched species in D03 + D05 + D06:")
print(d03_d05_d06_core["species"].tolist())

d03_d05_d06_output = PROCESSED_DIR / "core_d03_d05_d06_matched_species.csv"

d03_d05_d06_core.to_csv(
    d03_d05_d06_output,
    index=False,
    encoding="utf-8-sig"
)

print("\nSaved D03 + D05 + D06 core matched dataset to:")
print(d03_d05_d06_output)

# ------------------------------------------------------------
# 43. Save D05 + D06 and D03 + D05 + D06 report
# ------------------------------------------------------------

d05_d06_core_report = PROCESSED_DIR / "d05_d06_core_report.txt"

with open(d05_d06_core_report, "w", encoding="utf-8") as f:
    f.write("D05 + D06 and D03 + D05 + D06 report\n")
    f.write("====================================\n\n")

    f.write("D05 + D06 matched dataset shape:\n")
    f.write(str(d05_d06_matched.shape))
    f.write("\n\n")

    f.write("D05 + D06 matched species:\n")
    f.write(str(d05_d06_matched["species"].tolist()))
    f.write("\n\n")

    f.write("D03 + D05 + D06 core matched dataset shape:\n")
    f.write(str(d03_d05_d06_core.shape))
    f.write("\n\n")

    f.write("D03 + D05 + D06 core matched species:\n")
    f.write(str(d03_d05_d06_core["species"].tolist()))
    f.write("\n\n")

    f.write("Saved D05 + D06 file:\n")
    f.write(str(d05_d06_output))
    f.write("\n\n")

    f.write("Saved D03 + D05 + D06 core file:\n")
    f.write(str(d03_d05_d06_output))
    f.write("\n")

print("\n" + "=" * 60)
print("D05 + D06 CORE REPORT SAVED TO:")
print(d05_d06_core_report)
print("=" * 60)

# ------------------------------------------------------------
# 44. Save final dataset priority report
# ------------------------------------------------------------

final_dataset_priority_report = PROCESSED_DIR / "final_dataset_priority_report.txt"

with open(final_dataset_priority_report, "w", encoding="utf-8") as f:
    f.write("Final dataset priority report\n")
    f.write("=============================\n\n")

    f.write("1. Broad background dataset\n")
    f.write("---------------------------\n")
    f.write("D01 Prieto cleaned master table:\n")
    f.write("File: master_table_v1.csv\n")
    f.write(f"Shape: {master_table_v1.shape}\n")
    f.write("Role: Broad background table for prey group, chemical acquisition, and colour pattern.\n\n")

    f.write("2. Detailed chemical defence dataset\n")
    f.write("------------------------------------\n")
    f.write("D03 Table_S1 species summary:\n")
    f.write("File: table_s1_species_summary.csv\n")
    f.write(f"Shape: {table_s1_species_summary.shape}\n")
    f.write("Role: Species-level chemical defence, toxicity, and unpalatability information.\n\n")

    f.write("3. Detailed colour metrics dataset\n")
    f.write("----------------------------------\n")
    f.write("D04 colour_defence_2024 species metrics summary:\n")
    f.write("File: colour_defence_2024_species_metrics_summary.csv\n")
    f.write(f"Shape: {d04_species_metrics_summary.shape}\n")
    f.write("Role: Large species-level colour, luminance, and visual pattern metrics dataset.\n\n")

    f.write("4. D05 combined dataset\n")
    f.write("-----------------------\n")
    f.write("D05 combined species summary:\n")
    f.write("File: d05_combined_species_summary.csv\n")
    f.write(f"Shape: {d05_combined_species_summary.shape}\n")
    f.write("Role: Boldness, detection, and unpal shrimp data.\n\n")

    f.write("5. D06 habitat background dataset\n")
    f.write("---------------------------------\n")
    f.write("D06 habitat background species metrics summary:\n")
    f.write("File: d06_habitat_background_species_metrics_summary.csv\n")
    f.write(f"Shape: {d06_species_metrics_summary.shape}\n")
    f.write("Role: Habitat background, palatability, toxicity, and visual metrics.\n\n")

    f.write("6. Main candidate combined datasets\n")
    f.write("-----------------------------------\n\n")

    f.write("Candidate A: D03 + D05\n")
    f.write("File: chemical_defence_d05_boldness_detection_matched_species.csv\n")
    f.write(f"Shape: {d03_d05_matched.shape}\n")
    f.write("Species:\n")
    f.write(str(d03_d05_matched["species"].tolist()))
    f.write("\n")
    f.write("Role: Strongest main candidate dataset because it has 11 matched species.\n\n")

    f.write("Candidate B: D05 + D06\n")
    f.write("File: d05_d06_matched_species_summary.csv\n")
    f.write(f"Shape: {d05_d06_matched.shape}\n")
    f.write("Species:\n")
    f.write(str(d05_d06_matched["species"].tolist()))
    f.write("\n")
    f.write("Role: Strong exploratory dataset linking boldness/detection with habitat background variables.\n\n")

    f.write("Candidate C: D03 + D05 + D06\n")
    f.write("File: core_d03_d05_d06_matched_species.csv\n")
    f.write(f"Shape: {d03_d05_d06_core.shape}\n")
    f.write("Species:\n")
    f.write(str(d03_d05_d06_core["species"].tolist()))
    f.write("\n")
    f.write("Role: Most complete core dataset, but only 8 species.\n\n")

    f.write("Candidate D: D03 + D04 + D05\n")
    f.write("File: core_d03_d04_d05_matched_species.csv\n")
    f.write(f"Shape: {d03_d04_d05_core.shape}\n")
    f.write("Species:\n")
    f.write(str(d03_d04_d05_core["species"].tolist()))
    f.write("\n")
    f.write("Role: Very complete but small; likely supplementary only.\n\n")

    f.write("7. Current recommendation\n")
    f.write("-------------------------\n")
    f.write("Use D03 + D05 as the main candidate analysis dataset.\n")
    f.write("Use D03 + D05 + D06 as a stricter core exploratory dataset.\n")
    f.write("Use D01 Prieto as broad contextual/background information rather than forcing all datasets into it.\n")
    f.write("D04 is useful as a large colour metrics dataset, but overlap with the chemical defence datasets is limited.\n")

print("\n" + "=" * 60)
print("FINAL DATASET PRIORITY REPORT SAVED TO:")
print(final_dataset_priority_report)
print("=" * 60)