from pathlib import Path

import pandas as pd


VISIBILITY_PATH = Path(
    "processed_data/automated_image_analysis/image_metrics/"
    "sam_scaled_ring120_visibility_metrics_species_pilot.csv"
)

DEFENCE_PATH = Path(
    "processed_data/analysis_preparation/"
    "d03_defence_response_species_audit.csv"
)

OUTPUT_PATH = Path(
    "processed_data/analysis_preparation/"
    "pilot_visibility_defence_merged.csv"
)


def main() -> None:
    """Merge pilot species-level visibility metrics with D03 defence data."""

    for path in [VISIBILITY_PATH, DEFENCE_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input file not found:\n{path.resolve()}"
            )

    visibility = pd.read_csv(VISIBILITY_PATH)
    defence = pd.read_csv(
        DEFENCE_PATH,
        dtype={
            "species": str,
        },
    )

    if "species" not in visibility.columns:
        raise ValueError(
            "The visibility table does not contain a species column."
        )

    if "species" not in defence.columns:
        raise ValueError(
            "The defence table does not contain a species column."
        )

    if visibility["species"].duplicated().any():
        duplicates = visibility.loc[
            visibility["species"].duplicated(keep=False),
            "species",
        ]

        raise ValueError(
            "Duplicate species were found in the visibility table:\n"
            + duplicates.to_string(index=False)
        )

    if defence["species"].duplicated().any():
        duplicates = defence.loc[
            defence["species"].duplicated(keep=False),
            "species",
        ]

        raise ValueError(
            "Duplicate species were found in the defence table:\n"
            + duplicates.to_string(index=False)
        )

    result = visibility.merge(
        defence,
        on="species",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    unmatched = result.loc[
        result["_merge"] != "both",
        "species",
    ].tolist()

    if unmatched:
        raise ValueError(
            "These visibility species did not match the D03 defence table:\n"
            + "\n".join(unmatched)
        )

    result = result.drop(columns="_merge")

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    display_columns = [
        "species",
        "n_images",
        "toxicity_bs_ld50_raw_values",
        "toxicity_bs_ld50_species_status",
        "toxicity_bs_ld50_exact_mean",
        "unpalatability_ps_ed50_raw_values",
        "unpalatability_ps_ed50_species_status",
        "unpalatability_ps_ed50_exact_mean",
        "chemical_defence_class_raw",
    ]

    print("Pilot visibility–defence merge completed.")
    print(f"Visibility species: {len(visibility)}")
    print(f"Matched species: {len(result)}")
    print(f"Unmatched species: 0")

    print("\nMerged pilot species:")
    print(
        result[display_columns].to_string(index=False)
    )

    print(f"\nOutput saved to:\n{OUTPUT_PATH}")


if __name__ == "__main__":
    main()