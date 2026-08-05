from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "processed_data/automated_image_analysis/image_metrics/"
    "sam_scaled_ring120_visibility_metrics_pilot.csv"
)

OUTPUT_PATH = Path(
    "processed_data/automated_image_analysis/image_metrics/"
    "sam_scaled_ring120_visibility_metrics_species_pilot.csv"
)


def main() -> None:
    """Summarise image-level boldness and detectability metrics by species."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_PATH.resolve()}"
        )

    df = pd.read_csv(INPUT_PATH)

    required_identifiers = ["species", "image_id"]

    missing_identifiers = [
        column
        for column in required_identifiers
        if column not in df.columns
    ]

    if missing_identifiers:
        raise ValueError(
            "Missing identifier columns:\n"
            + "\n".join(missing_identifiers)
        )

    metric_columns = [
        column
        for column in df.columns
        if column.startswith("boldness_")
        or column.startswith("detectability_")
    ]

    if not metric_columns:
        raise ValueError(
            "No boldness or detectability metric columns were found."
        )

    # Check that every image appears only once.
    duplicated_images = df["image_id"].duplicated(keep=False)

    if duplicated_images.any():
        duplicate_values = (
            df.loc[
                duplicated_images,
                ["species", "image_id"],
            ]
            .sort_values(["species", "image_id"])
        )

        raise ValueError(
            "Duplicate image IDs were found:\n"
            + duplicate_values.to_string(index=False)
        )

    # Count images for each species.
    species_counts = (
        df.groupby("species")
        .size()
        .rename("n_images")
    )

    # Calculate the species-level mean of every image metric.
    species_means = (
        df.groupby("species")[metric_columns]
        .mean()
        .add_suffix("_species_mean")
    )

    # Calculate variation among images belonging to each species.
    species_sds = (
        df.groupby("species")[metric_columns]
        .std(ddof=1)
        .add_suffix("_species_sd")
    )

    result = pd.concat(
        [
            species_counts,
            species_means,
            species_sds,
        ],
        axis=1,
    ).reset_index()

    # A species represented by one image will have NA species SD values.
    # This is expected because an SD cannot be calculated from one image.
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("Species-level visibility summary completed.")
    print(f"Input images: {len(df)}")
    print(f"Species: {result['species'].nunique()}")
    print(f"Image-level metrics: {len(metric_columns)}")
    print(f"Species-level mean columns: {len(metric_columns)}")
    print(f"Species-level SD columns: {len(metric_columns)}")
    print()

    print(
        result[
            ["species", "n_images"]
        ].to_string(index=False)
    )

    print()
    print(f"Output saved to:\n{OUTPUT_PATH}")


if __name__ == "__main__":
    main()