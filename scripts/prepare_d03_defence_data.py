from pathlib import Path
import re

import numpy as np
import pandas as pd


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "current_core"
    / "table_s1_species_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "current_core"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "table_s1_species_summary_defence_cleaned.csv"
)

COVERAGE_CSV = (
    OUTPUT_DIR
    / "table_s1_defence_coverage_summary.csv"
)

EXPECTED_SPECIES = 30

ASSAY_COLUMNS = [
    "unpalatability_ps_ed50",
    "unpalatability_tf_ed50",
    "unpalatability_trf_ed50",
    "toxicity_bs_ld50",
    "toxicity_df_wm",
]


# =========================
# Parsing helpers
# =========================

PLAIN_NUMBER_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$"
)

GT_RE = re.compile(
    r"^>\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)

LT_RE = re.compile(
    r"^<\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def join_numbers(values):
    if not values:
        return ""

    return "; ".join(
        f"{value:g}"
        for value in values
    )


def parse_assay_value(value):
    """
    Parse one Table S1 assay cell conservatively.

    Important:
    - The original raw text is always retained.
    - Bare numeric values are treated as exact reported values.
    - >x and <x are retained as censored bounds, not converted to x.
    - 'nr' is retained as 'nr'; it is NOT converted to zero.
    - 'NA (inconclusive)' is retained as inconclusive.
    - For mixed cells such as '0.65; >1' or '0.52; nr',
      all components are retained separately.
    - exact_mean is only the mean of exact bare numeric components.
      It is a descriptive helper and is NOT automatically the final
      statistical analysis value.
    """
    raw = clean_text(value)
    normalized = raw.lower().strip()

    result = {
        "raw": raw,
        "status": "",
        "exact_values": "",
        "exact_n": 0,
        "exact_mean": np.nan,
        "gt_thresholds": "",
        "lt_thresholds": "",
        "has_nr": False,
        "has_inconclusive": False,
        "unparsed_components": "",
    }

    if normalized == "":
        result["status"] = "missing"
        return result

    if "inconclusive" in normalized:
        result["has_inconclusive"] = True

    components = [
        part.strip()
        for part in raw.split(";")
        if part.strip()
    ]

    exact_values = []
    gt_thresholds = []
    lt_thresholds = []
    unparsed = []
    has_nr = False
    has_inconclusive = False

    for component in components:
        token = component.strip()
        token_lower = token.lower().strip()

        if token_lower == "nr":
            has_nr = True
            continue

        if "inconclusive" in token_lower:
            has_inconclusive = True
            continue

        if PLAIN_NUMBER_RE.fullmatch(token):
            exact_values.append(
                float(token)
            )
            continue

        gt_match = GT_RE.match(token)

        if gt_match:
            gt_thresholds.append(
                float(gt_match.group(1))
            )

            # Keep any extra note, e.g. ">1 (1.41)",
            # in the raw field. We do not interpret the
            # parenthetical value as an exact measurement.
            continue

        lt_match = LT_RE.match(token)

        if lt_match:
            lt_thresholds.append(
                float(lt_match.group(1))
            )
            continue

        unparsed.append(token)

    result["exact_values"] = (
        join_numbers(exact_values)
    )
    result["exact_n"] = len(
        exact_values
    )

    if exact_values:
        result["exact_mean"] = float(
            np.mean(exact_values)
        )

    result["gt_thresholds"] = (
        join_numbers(gt_thresholds)
    )
    result["lt_thresholds"] = (
        join_numbers(lt_thresholds)
    )
    result["has_nr"] = has_nr
    result["has_inconclusive"] = (
        has_inconclusive
    )
    result["unparsed_components"] = (
        "; ".join(unparsed)
    )

    # Build a transparent status label.
    flags = []

    if exact_values:
        flags.append(
            "measured_multiple"
            if len(exact_values) > 1
            else "measured"
        )

    if gt_thresholds:
        flags.append("greater_than")

    if lt_thresholds:
        flags.append("less_than")

    if has_nr:
        flags.append("nr")

    if has_inconclusive:
        flags.append("inconclusive")

    if unparsed:
        flags.append("unparsed")

    if not flags:
        result["status"] = "unparsed"
    elif len(flags) == 1:
        result["status"] = flags[0]
    else:
        result["status"] = (
            "_plus_".join(flags)
        )

    return result


def classify_defence_class(value):
    raw = clean_text(value)

    if raw == "":
        return "missing"

    simple_classes = {
        "I&II",
        "I",
        "II",
        "WR",
        "NR",
    }

    if raw in simple_classes:
        return "simple"

    return "mixed_or_uncertain"


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find input file: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(
        INPUT_CSV,
        dtype=str,
        keep_default_na=False,
    )

    if len(df) != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {len(df)}."
        )

    if "species" not in df.columns:
        raise KeyError(
            "Missing required column: species"
        )

    if df["species"].duplicated().any():
        duplicated = (
            df.loc[
                df["species"].duplicated(
                    keep=False
                ),
                "species",
            ]
            .astype(str)
            .tolist()
        )

        raise ValueError(
            "Duplicate species rows found: "
            + ", ".join(duplicated)
        )

    missing_assays = [
        column
        for column in ASSAY_COLUMNS
        if column not in df.columns
    ]

    if missing_assays:
        raise KeyError(
            "Missing assay columns: "
            + ", ".join(missing_assays)
        )

    cleaned = df.copy()

    if "chemical_defence_class" in cleaned.columns:
        cleaned[
            "chemical_defence_class_raw"
        ] = cleaned[
            "chemical_defence_class"
        ].apply(clean_text)

        cleaned[
            "chemical_defence_class_status"
        ] = cleaned[
            "chemical_defence_class"
        ].apply(
            classify_defence_class
        )

    coverage_rows = []

    for assay in ASSAY_COLUMNS:
        parsed_rows = [
            parse_assay_value(value)
            for value in cleaned[assay]
        ]

        parsed_df = pd.DataFrame(
            parsed_rows
        )

        for parsed_column in parsed_df.columns:
            cleaned[
                f"{assay}_{parsed_column}"
            ] = parsed_df[
                parsed_column
            ].values

        any_exact = (
            parsed_df["exact_n"] > 0
        )

        any_censored = (
            parsed_df["gt_thresholds"].ne("")
            | parsed_df["lt_thresholds"].ne("")
        )

        coverage_rows.append(
            {
                "assay": assay,
                "n_species_total": len(cleaned),
                "n_with_any_exact_numeric": int(
                    any_exact.sum()
                ),
                "n_exact_only": int(
                    parsed_df["status"].isin(
                        [
                            "measured",
                            "measured_multiple",
                        ]
                    ).sum()
                ),
                "n_with_any_censoring": int(
                    any_censored.sum()
                ),
                "n_with_nr": int(
                    parsed_df["has_nr"].sum()
                ),
                "n_inconclusive": int(
                    parsed_df[
                        "has_inconclusive"
                    ].sum()
                ),
                "n_missing": int(
                    parsed_df[
                        "status"
                    ].eq(
                        "missing"
                    ).sum()
                ),
                "n_unparsed": int(
                    parsed_df[
                        "unparsed_components"
                    ].ne("")
                    .sum()
                ),
            }
        )

    cleaned.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    coverage_df = pd.DataFrame(
        coverage_rows
    )

    coverage_df.to_csv(
        COVERAGE_CSV,
        index=False,
    )

    print("=" * 72)
    print("D03 DEFENCE PREPARATION COMPLETE")
    print("=" * 72)
    print(
        f"Species: {len(cleaned)}"
    )

    if (
        "chemical_defence_class_status"
        in cleaned.columns
    ):
        print()
        print(
            "Chemical-defence class status:"
        )
        print(
            cleaned[
                "chemical_defence_class_status"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    print()
    print("Assay coverage:")
    print(
        coverage_df.to_string(
            index=False
        )
    )

    print()
    print("Saved:")
    print(
        OUTPUT_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        COVERAGE_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )

    print()
    print(
        "IMPORTANT: *_exact_mean columns are "
        "descriptive summaries of exact numeric "
        "components only. Censored values such as "
        ">1 or <0.25 and 'nr' have NOT been "
        "converted into numeric values."
    )


if __name__ == "__main__":
    main()
