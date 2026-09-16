from pathlib import Path

import pandas as pd


# ============================================================
# File paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# van den Berg et al. (2024) background dataset
VAN_DATA_DIR = (
    PROJECT_ROOT
    / "raw_data"
    / "UQ_datasets"
    / "habitat_background_2024"
)

# Metrics calculated from the final 295 online images
OUR_DATA_FILE = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "image_metrics"
    / "sam_scaled_ring120_image_metrics_final.csv"
)

# Output folder
OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "van_background_comparison"
)

OVERLAP_FILE = (
    OUTPUT_DIR
    / "van_background_species_overlap.csv"
)

VAN_MEANS_FILE = (
    OUTPUT_DIR
    / "van_background_species_metric_means.csv"
)

OUR_MEANS_FILE = (
    OUTPUT_DIR
    / "online_background_species_metric_means.csv"
)


# ============================================================
# Species-name cleaning
# ============================================================

def clean_species_name(value):
    """
    Make species names consistent between the two datasets.
    """

    name = str(value).replace("_", " ").strip()
    name = " ".join(name.split())

    # The two datasets use different spellings for this species.
    if name == "Dendrodoris krusensterni":
        name = "Dendrodoris krusensternii (=denisoni)"

    return name


# ============================================================
# Main analysis
# ============================================================

def main():

    # --------------------------------------------------------
    # Find the Van background CSV
    # --------------------------------------------------------

    van_files = list(
        VAN_DATA_DIR.glob("*.csv")
    )

    if len(van_files) != 1:
        raise ValueError(
            "Expected one CSV in the Van background folder, "
            f"but found {len(van_files)}."
        )

    van_file = van_files[0]

    print("=" * 70)
    print("INPUT FILES")
    print("=" * 70)

    print("\nVan background file:")
    print(van_file)

    print("\nOnline-image metrics file:")
    print(OUR_DATA_FILE)

    if not OUR_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find online-image metrics file: "
            f"{OUR_DATA_FILE}"
        )

    # --------------------------------------------------------
    # Read the two datasets
    # --------------------------------------------------------

    van_data = pd.read_csv(
        van_file
    )

    our_data = pd.read_csv(
        OUR_DATA_FILE
    )

    # Check that the required columns exist.
    required_van_columns = [
        "species",
        "distance",
        "ind_ID",
        "BSA.BML",
        "BSA.BCVL",
        "BSA.BMS",
        "BSA.BCVS",
    ]

    required_our_columns = [
        "species",
        "image_id",
        "background_luminance_edge_mean",
        "background_luminance_edge_cv",
        "background_chromatic_edge_mean",
        "background_chromatic_edge_cv",
    ]

    missing_van_columns = [
        column
        for column in required_van_columns
        if column not in van_data.columns
    ]

    missing_our_columns = [
        column
        for column in required_our_columns
        if column not in our_data.columns
    ]

    if missing_van_columns:
        raise KeyError(
            "Missing columns in Van data: "
            + ", ".join(missing_van_columns)
        )

    if missing_our_columns:
        raise KeyError(
            "Missing columns in online-image data: "
            + ", ".join(missing_our_columns)
        )

    # --------------------------------------------------------
    # Clean species names
    # --------------------------------------------------------

    van_data["species_clean"] = (
        van_data["species"]
        .map(clean_species_name)
    )

    our_data["species_clean"] = (
        our_data["species"]
        .map(clean_species_name)
    )

    van_data["distance"] = (
        van_data["distance"]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Find overlapping species
    # --------------------------------------------------------

    van_species = sorted(
        van_data[
            "species_clean"
        ]
        .dropna()
        .unique()
    )

    our_species = sorted(
        our_data[
            "species_clean"
        ]
        .dropna()
        .unique()
    )

    overlap_species = sorted(
        set(van_species)
        & set(our_species)
    )

    print("\n" + "=" * 70)
    print("SPECIES OVERLAP")
    print("=" * 70)

    print(
        f"\nNumber of Van background species: "
        f"{len(van_species)}"
    )

    print(
        f"Number of species in our dataset: "
        f"{len(our_species)}"
    )

    print(
        f"Number of overlapping species: "
        f"{len(overlap_species)}"
    )

    print("\nOverlapping species:")

    for species in overlap_species:
        print(f"- {species}")

    if len(van_species) != 12:
        raise ValueError(
            "Expected 12 species in the Van dataset, "
            f"but found {len(van_species)}."
        )

    if len(our_species) != 30:
        raise ValueError(
            "Expected 30 species in the online-image dataset, "
            f"but found {len(our_species)}."
        )

    if len(overlap_species) != 9:
        raise ValueError(
            "Expected 9 overlapping species, "
            f"but found {len(overlap_species)}."
        )

    # --------------------------------------------------------
    # Save the overlap table
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    overlap_table = pd.DataFrame(
        {
            "species": overlap_species
        }
    )

    overlap_table.to_csv(
        OVERLAP_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Keep only the nine overlapping species
    # --------------------------------------------------------

    van_overlap = van_data[
        van_data[
            "species_clean"
        ].isin(overlap_species)
    ].copy()

    our_overlap = our_data[
        our_data[
            "species_clean"
        ].isin(overlap_species)
    ].copy()

    # --------------------------------------------------------
    # Calculate Van species-level means
    # --------------------------------------------------------

    van_species_means = (
        van_overlap
        .groupby(
            [
                "species_clean",
                "distance",
            ],
            as_index=False,
        )
        .agg(
            van_n_records=(
                "species_clean",
                "size",
            ),
            van_n_individuals=(
                "ind_ID",
                "nunique",
            ),
            van_luminance_edge_mean=(
                "BSA.BML",
                "mean",
            ),
            van_luminance_edge_cv=(
                "BSA.BCVL",
                "mean",
            ),
            van_chromatic_edge_mean=(
                "BSA.BMS",
                "mean",
            ),
            van_chromatic_edge_cv=(
                "BSA.BCVS",
                "mean",
            ),
        )
        .rename(
            columns={
                "species_clean": "species"
            }
        )
        .sort_values(
            [
                "species",
                "distance",
            ]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Calculate online-image species-level means
    # --------------------------------------------------------

    our_species_means = (
        our_overlap
        .groupby(
            "species_clean",
            as_index=False,
        )
        .agg(
            our_n_images=(
                "image_id",
                "nunique",
            ),
            online_luminance_edge_mean=(
                "background_luminance_edge_mean",
                "mean",
            ),
            online_luminance_edge_cv=(
                "background_luminance_edge_cv",
                "mean",
            ),
            online_chromatic_edge_mean=(
                "background_chromatic_edge_mean",
                "mean",
            ),
            online_chromatic_edge_cv=(
                "background_chromatic_edge_cv",
                "mean",
            ),
        )
        .rename(
            columns={
                "species_clean": "species"
            }
        )
        .sort_values(
            "species"
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Check output sizes
    # --------------------------------------------------------

    # Nine species at two viewing distances:
    # 9 x 2 = 18 rows.
    if len(van_species_means) != 18:
        raise ValueError(
            "Expected 18 Van species-distance rows, "
            f"but found {len(van_species_means)}."
        )

    if len(our_species_means) != 9:
        raise ValueError(
            "Expected 9 online-image species rows, "
            f"but found {len(our_species_means)}."
        )

    if (
        van_species_means.isna().any().any()
    ):
        raise ValueError(
            "Missing values found in the Van species means."
        )

    if (
        our_species_means.isna().any().any()
    ):
        raise ValueError(
            "Missing values found in the online-image "
            "species means."
        )

    # --------------------------------------------------------
    # Save species-level means
    # --------------------------------------------------------

    van_species_means.to_csv(
        VAN_MEANS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    our_species_means.to_csv(
        OUR_MEANS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("VAN SPECIES-LEVEL MEANS")
    print("=" * 70)

    print(
        van_species_means.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("ONLINE-IMAGE SPECIES-LEVEL MEANS")
    print("=" * 70)

    print(
        our_species_means.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print("\nOverlap file:")
    print(OVERLAP_FILE)

    print("\nVan species means:")
    print(VAN_MEANS_FILE)

    print("\nOnline-image species means:")
    print(OUR_MEANS_FILE)


if __name__ == "__main__":
    main()