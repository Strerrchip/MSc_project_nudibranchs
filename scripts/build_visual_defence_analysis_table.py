from pathlib import Path
import re

import numpy as np
import pandas as pd


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFENCE_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "current_core"
    / "table_s1_species_summary_defence_cleaned.csv"
)

BOLDNESS_PCA_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "pca_results"
    / "boldness_pca_scores.csv"
)

DETECTABILITY_PCA_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "pca_results"
    / "detectability_pca_scores.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "visual_defence_analysis_table.csv"
)

EXPECTED_SPECIES = 30


# =========================
# Defence-score parsing
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


def build_strength_score(value):
    """
    Convert an ED50 or LD50 species-summary cell into a bounded
    0-1 defence-strength score when the information is sufficient.

    Rules:
    - exact x -> max(0, 1 - x)
    - nr -> 0
    - >1 (or > a threshold >= 1) -> 0
    - other right-censored values, e.g. >0.13 or >0.5 -> excluded
    - left-censored values, e.g. <0.25 -> excluded
    - multiple fully resolvable components are averaged
    - missing/inconclusive -> missing

    Higher values therefore mean stronger defence:
    greater unpalatability for ED50 and greater toxicity for LD50.

    This keeps ambiguous censoring out of the continuous analysis
    rather than pretending that the censoring threshold is an exact value.
    """
    raw = clean_text(value)

    if raw == "":
        return {
            "score": np.nan,
            "status": "missing",
            "n_components_used": 0,
        }

    components = [
        part.strip()
        for part in raw.split(";")
        if part.strip()
    ]

    component_scores = []
    unresolved = False
    inconclusive = False

    for component in components:
        token = component.strip()
        lower = token.lower()

        if lower == "nr":
            component_scores.append(0.0)
            continue

        if "inconclusive" in lower:
            inconclusive = True
            continue

        if PLAIN_NUMBER_RE.fullmatch(token):
            x = float(token)
            component_scores.append(
                max(0.0, min(1.0, 1.0 - x))
            )
            continue

        gt_match = GT_RE.match(token)

        if gt_match:
            threshold = float(
                gt_match.group(1)
            )

            if threshold >= 1.0:
                component_scores.append(0.0)
            else:
                unresolved = True

            continue

        lt_match = LT_RE.match(token)

        if lt_match:
            # Example: <0.25 means the true ED50/LD50 is only known
            # to lie below the threshold, so the transformed strength
            # is only known to lie above 0.75.
            unresolved = True
            continue

        unresolved = True

    if inconclusive:
        return {
            "score": np.nan,
            "status": "inconclusive",
            "n_components_used": 0,
        }

    if unresolved:
        return {
            "score": np.nan,
            "status": "censored_excluded",
            "n_components_used": len(
                component_scores
            ),
        }

    if not component_scores:
        return {
            "score": np.nan,
            "status": "missing",
            "n_components_used": 0,
        }

    score = float(
        np.mean(component_scores)
    )

    if len(component_scores) == 1:
        status = "resolved_single"
    else:
        status = "resolved_multiple"

    return {
        "score": score,
        "status": status,
        "n_components_used": len(
            component_scores
        ),
    }


# =========================
# Main workflow
# =========================

def main():
    for path in [
        DEFENCE_CSV,
        BOLDNESS_PCA_CSV,
        DETECTABILITY_PCA_CSV,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Cannot find required file: {path}"
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    defence = pd.read_csv(
        DEFENCE_CSV,
        dtype=str,
        keep_default_na=False,
    )

    boldness = pd.read_csv(
        BOLDNESS_PCA_CSV
    )

    detectability = pd.read_csv(
        DETECTABILITY_PCA_CSV
    )

    for name, df in [
        ("defence", defence),
        ("boldness PCA", boldness),
        ("detectability PCA", detectability),
    ]:
        if "species" not in df.columns:
            raise KeyError(
                f"{name} table is missing species."
            )

        if df["species"].duplicated().any():
            raise ValueError(
                f"Duplicate species found in {name} table."
            )

    if len(defence) != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} defence species, "
            f"found {len(defence)}."
        )

    # -------------------------
    # Build continuous defence scores
    # -------------------------

    assay_map = {
        "unpalatability_ps_ed50":
            "unpalatability_strength",
        "toxicity_bs_ld50":
            "toxicity_strength",
    }

    for source_column, output_prefix in assay_map.items():
        if source_column not in defence.columns:
            raise KeyError(
                f"Missing defence column: {source_column}"
            )

        parsed = pd.DataFrame(
            [
                build_strength_score(value)
                for value in defence[
                    source_column
                ]
            ]
        )

        defence[
            f"{output_prefix}_0_1"
        ] = parsed["score"].values

        defence[
            f"{output_prefix}_status"
        ] = parsed["status"].values

        defence[
            f"{output_prefix}_n_components"
        ] = parsed[
            "n_components_used"
        ].values

    # -------------------------
    # Select PCA columns
    # -------------------------

    boldness_pc_cols = [
        column
        for column in boldness.columns
        if re.fullmatch(
            r"PC\d+",
            str(column),
        )
    ]

    detectability_pc_cols = [
        column
        for column in detectability.columns
        if re.fullmatch(
            r"PC\d+",
            str(column),
        )
    ]

    if len(boldness_pc_cols) < 2:
        raise ValueError(
            "Boldness PCA table has fewer than two PCs."
        )

    if len(detectability_pc_cols) < 4:
        raise ValueError(
            "Detectability PCA table has fewer than four PCs."
        )

    boldness_keep = boldness[
        [
            "species",
            *boldness_pc_cols,
        ]
    ].copy()

    boldness_keep = boldness_keep.rename(
        columns={
            column: f"boldness_{column}"
            for column in boldness_pc_cols
        }
    )

    detectability_keep = detectability[
        [
            "species",
            *detectability_pc_cols,
        ]
    ].copy()

    detectability_keep = detectability_keep.rename(
        columns={
            column: f"detectability_{column}"
            for column in detectability_pc_cols
        }
    )

    # -------------------------
    # Merge
    # -------------------------

    merged = defence.merge(
        boldness_keep,
        on="species",
        how="left",
        validate="one_to_one",
    )

    merged = merged.merge(
        detectability_keep,
        on="species",
        how="left",
        validate="one_to_one",
    )

    if len(merged) != EXPECTED_SPECIES:
        raise ValueError(
            "Merged table does not contain 30 species."
        )

    pca_check_cols = [
        "boldness_PC1",
        "boldness_PC2",
        "detectability_PC1",
        "detectability_PC2",
        "detectability_PC3",
        "detectability_PC4",
    ]

    missing_pca = (
        merged[
            pca_check_cols
        ]
        .isna()
        .any(axis=1)
    )

    if missing_pca.any():
        bad_species = (
            merged.loc[
                missing_pca,
                "species",
            ]
            .astype(str)
            .tolist()
        )

        raise ValueError(
            "PCA scores failed to match for: "
            + ", ".join(bad_species)
        )

    merged.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print("=" * 72)
    print("VISUAL + DEFENCE ANALYSIS TABLE COMPLETE")
    print("=" * 72)
    print(
        f"Species: {len(merged)}"
    )

    print()
    print("Unpalatability score status:")
    print(
        merged[
            "unpalatability_strength_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "Usable continuous unpalatability scores: "
        f"{merged['unpalatability_strength_0_1'].notna().sum()}"
    )

    print()
    print("Toxicity score status:")
    print(
        merged[
            "toxicity_strength_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "Usable continuous toxicity scores: "
        f"{merged['toxicity_strength_0_1'].notna().sum()}"
    )

    print()
    print("Saved:")
    print(
        OUTPUT_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )

    print()
    print(
        "Higher 0-1 scores mean stronger defence. "
        "Ambiguous censored values such as >0.13, >0.5, "
        "or <0.25 are left missing for continuous analysis."
    )


if __name__ == "__main__":
    main()
