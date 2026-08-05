from pathlib import Path
import re

import pandas as pd


INPUT_PATH = Path(
    "processed_data/current_core/table_s1_cleaned.csv"
)

OUTPUT_PATH = Path(
    "processed_data/analysis_preparation/"
    "d03_defence_response_species_audit.csv"
)


EXACT_NUMBER_PATTERN = re.compile(
    r"^[0-9]*\.?[0-9]+$"
)

GREATER_THAN_PATTERN = re.compile(
    r"^>\s*([0-9]*\.?[0-9]+)"
)

LESS_THAN_PATTERN = re.compile(
    r"^<\s*([0-9]*\.?[0-9]+)"
)


def unique_non_empty(values: pd.Series) -> list[str]:
    """Return unique non-empty strings in their original order."""

    result = []

    for value in values.astype(str):
        cleaned = value.strip()

        if cleaned and cleaned not in result:
            result.append(cleaned)

    return result


def classify_assay_value(
    value: str,
) -> tuple[str, float | None]:
    """Classify one raw ED50 or LD50 value."""

    cleaned = str(value).strip()

    if cleaned == "":
        return "missing", None

    if cleaned.lower() == "nr":
        return "no_response", None

    if "inconclusive" in cleaned.lower():
        return "inconclusive", None

    if EXACT_NUMBER_PATTERN.fullmatch(cleaned):
        return "exact_numeric", float(cleaned)

    greater_match = GREATER_THAN_PATTERN.match(cleaned)

    if greater_match:
        return (
            "right_censored",
            float(greater_match.group(1)),
        )

    less_match = LESS_THAN_PATTERN.match(cleaned)

    if less_match:
        return (
            "left_censored",
            float(less_match.group(1)),
        )

    return "unclassified", None


def summarise_assay(
    group: pd.DataFrame,
    value_column: str,
    output_prefix: str,
) -> dict:
    """Summarise one assay for one species."""

    classified = group[value_column].apply(
        classify_assay_value
    )

    statuses = pd.Series(
        [item[0] for item in classified],
        index=group.index,
    )

    parsed_values = pd.Series(
        [item[1] for item in classified],
        index=group.index,
        dtype="float64",
    )

    exact_values = (
        parsed_values[statuses == "exact_numeric"]
        .dropna()
        .tolist()
    )

    right_bounds = (
        parsed_values[statuses == "right_censored"]
        .dropna()
        .tolist()
    )

    left_bounds = (
        parsed_values[statuses == "left_censored"]
        .dropna()
        .tolist()
    )

    status_counts = statuses.value_counts().to_dict()

    if exact_values:
        species_status = "exact_numeric_available"
    elif left_bounds and right_bounds:
        species_status = "mixed_censored_only"
    elif left_bounds:
        species_status = "left_censored_only"
    elif right_bounds:
        species_status = "right_censored_only"
    elif status_counts.get("no_response", 0) > 0:
        species_status = "no_response"
    elif status_counts.get("inconclusive", 0) > 0:
        species_status = "inconclusive"
    elif status_counts.get("unclassified", 0) > 0:
        species_status = "unclassified"
    else:
        species_status = "missing"

    return {
        f"{output_prefix}_raw_values": "; ".join(
            unique_non_empty(group[value_column])
        ),
        f"{output_prefix}_species_status": species_status,
        f"n_{output_prefix}_exact": len(exact_values),
        f"{output_prefix}_exact_values": "; ".join(
            str(value) for value in exact_values
        ),
        f"{output_prefix}_exact_mean": (
            sum(exact_values) / len(exact_values)
            if exact_values
            else None
        ),
        f"n_{output_prefix}_left_censored": len(
            left_bounds
        ),
        f"{output_prefix}_left_censored_bounds": "; ".join(
            str(value) for value in left_bounds
        ),
        f"n_{output_prefix}_right_censored": len(
            right_bounds
        ),
        f"{output_prefix}_right_censored_bounds": "; ".join(
            str(value) for value in right_bounds
        ),
        f"n_{output_prefix}_no_response": status_counts.get(
            "no_response",
            0,
        ),
        f"n_{output_prefix}_inconclusive": status_counts.get(
            "inconclusive",
            0,
        ),
        f"n_{output_prefix}_missing": status_counts.get(
            "missing",
            0,
        ),
        f"n_{output_prefix}_unclassified": status_counts.get(
            "unclassified",
            0,
        ),
    }


def main() -> None:
    """Create a unified species-level D03 defence audit."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_PATH.resolve()}"
        )

    df = pd.read_csv(
        INPUT_PATH,
        dtype=str,
        keep_default_na=False,
    )

    required_columns = [
        "species",
        "extract_id",
        "body_part",
        "unpalatability_ps_ed50",
        "toxicity_bs_ld50",
        "toxicity_df_wm",
        "chemical_defence_class",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing_columns)
        )

    # Use whole-body records only.
    wb = df[
        df["body_part"].str.strip().str.upper() == "WB"
    ].copy()

    species_rows = []

    for species, group in wb.groupby(
        "species",
        sort=True,
    ):
        row = {
            "species": species,
            "n_whole_body_extracts": len(group),
            "whole_body_extract_ids": "; ".join(
                unique_non_empty(group["extract_id"])
            ),
            "chemical_defence_class_raw": "; ".join(
                unique_non_empty(
                    group["chemical_defence_class"]
                )
            ),
            "toxicity_df_wm_raw_values": "; ".join(
                unique_non_empty(group["toxicity_df_wm"])
            ),
        }

        toxicity_summary = summarise_assay(
            group=group,
            value_column="toxicity_bs_ld50",
            output_prefix="toxicity_bs_ld50",
        )

        unpalatability_summary = summarise_assay(
            group=group,
            value_column="unpalatability_ps_ed50",
            output_prefix="unpalatability_ps_ed50",
        )

        row.update(toxicity_summary)
        row.update(unpalatability_summary)

        species_rows.append(row)

    result = pd.DataFrame(species_rows)

    if result["species"].duplicated().any():
        raise ValueError(
            "Duplicate species were found in the output."
        )

    if len(result) != 30:
        raise ValueError(
            f"Expected 30 species, but found {len(result)}."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("D03 defence response audit completed.")
    print(f"Whole-body extract rows: {len(wb)}")
    print(f"Species: {len(result)}")

    print("\nBS LD50 toxicity status:")
    print(
        result["toxicity_bs_ld50_species_status"]
        .value_counts()
        .to_string()
    )

    print("\nPalaemon ED50 unpalatability status:")
    print(
        result["unpalatability_ps_ed50_species_status"]
        .value_counts()
        .to_string()
    )

    pilot_species = result[
        result["species"].isin(
            [
                "Aphelodoris varia",
                "Doriprismatica atromarginata",
            ]
        )
    ]

    print("\nPilot species:")
    print(
        pilot_species[
            [
                "species",
                "toxicity_bs_ld50_raw_values",
                "toxicity_bs_ld50_species_status",
                "toxicity_bs_ld50_exact_mean",
                "unpalatability_ps_ed50_raw_values",
                "unpalatability_ps_ed50_species_status",
                "unpalatability_ps_ed50_exact_mean",
                "chemical_defence_class_raw",
            ]
        ].to_string(index=False)
    )

    print(f"\nOutput saved to:\n{OUTPUT_PATH}")


if __name__ == "__main__":
    main()