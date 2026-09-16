"""Create the final 2 x 2 figure for composite scores and defence.

This version removes panel grids and marks only relationships that remain
significant after Benjamini-Hochberg correction across the four planned
comparisons. Pearson and Spearman families are corrected separately.
"""

from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def first_existing(*relative_paths: str) -> Path:
    candidates = [PROJECT_ROOT / path for path in relative_paths]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    choices = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(
        f"Could not find any of these files:\n{choices}"
    )


SCORES_CSV = first_existing(
    (
        "processed_data/automated_image_analysis/composite_scores/"
        "visibility_composite_scores.csv"
    ),
    (
        "processed_data/automated_image_analysis/composite_scores/"
        "visibility_mean_normalised_scores.csv"
    ),
    "composite_scores/visibility_composite_scores.csv",
    "visibility_mean_normalised_scores.csv",
)

DEFENCE_CSV = first_existing(
    "processed_data/current_core/"
    "table_s1_species_summary_defence_cleaned.csv",
    "current_core/table_s1_species_summary_defence_cleaned.csv",
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "mean_normalised_scores_vs_defence"
)

ANALYSIS_TABLE_CSV = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_table.csv"
)

CORRELATIONS_CSV = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_correlations.csv"
)

FIGURE_PNG = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_2x2_final.png"
)

FIGURE_PDF = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_2x2_final.pdf"
)

CAPTION_TXT = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_2x2_final_caption.txt"
)

SUMMARY_TXT = (
    OUTPUT_DIR
    / "mean_normalised_scores_vs_defence_summary.txt"
)


PLAIN_NUMBER_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$"
)

GT_RE = re.compile(
    r"^>\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)

LT_RE = re.compile(
    r"^<\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip()


def build_strength_score(
    value: object,
) -> tuple[float, str]:
    """Convert an ED50 or LD50 cell into a 0-1 strength score."""

    raw = clean_text(value)

    if not raw:
        return np.nan, "missing"

    component_scores = []
    unresolved = False

    components = [
        part.strip()
        for part in raw.split(";")
        if part.strip()
    ]

    for component in components:
        lower = component.lower()

        if lower == "nr":
            component_scores.append(0.0)

        elif "inconclusive" in lower:
            return np.nan, "inconclusive"

        elif PLAIN_NUMBER_RE.fullmatch(component):
            value_number = float(component)

            strength = max(
                0.0,
                min(1.0, 1.0 - value_number),
            )

            component_scores.append(strength)

        elif (
            match := GT_RE.match(component)
        ) is not None:
            threshold = float(match.group(1))

            if threshold >= 1.0:
                component_scores.append(0.0)
            else:
                unresolved = True

        elif LT_RE.match(component) is not None:
            unresolved = True

        else:
            unresolved = True

    if unresolved:
        return np.nan, "censored_excluded"

    if not component_scores:
        return np.nan, "missing"

    return (
        float(np.mean(component_scores)),
        "resolved",
    )


def benjamini_hochberg(
    p_values: list[float],
) -> np.ndarray:
    """Calculate Benjamini-Hochberg adjusted p-values."""

    values = np.asarray(
        p_values,
        dtype=float,
    )

    order = np.argsort(values)
    ranked = values[order]

    adjusted_ranked = (
        ranked
        * len(values)
        / np.arange(1, len(values) + 1)
    )

    adjusted_ranked = np.minimum.accumulate(
        adjusted_ranked[::-1]
    )[::-1]

    adjusted_ranked = np.clip(
        adjusted_ranked,
        0.0,
        1.0,
    )

    adjusted = np.empty_like(
        adjusted_ranked
    )

    adjusted[order] = adjusted_ranked

    return adjusted


def build_analysis_table() -> pd.DataFrame:
    scores = pd.read_csv(SCORES_CSV)

    defence = pd.read_csv(
        DEFENCE_CSV,
        dtype=str,
        keep_default_na=False,
    )

    score_columns = [
        "species",
        "n_images",
        "mean_normalised_boldness",
        "mean_normalised_detectability",
    ]

    missing_scores = [
        column
        for column in score_columns
        if column not in scores
    ]

    if missing_scores:
        raise KeyError(
            "Missing composite-score columns: "
            + ", ".join(missing_scores)
        )

    defence_columns = [
        "species",
        "unpalatability_ps_ed50",
        "toxicity_bs_ld50",
    ]

    missing_defence = [
        column
        for column in defence_columns
        if column not in defence
    ]

    if missing_defence:
        raise KeyError(
            "Missing defence columns: "
            + ", ".join(missing_defence)
        )

    if scores["species"].duplicated().any():
        raise ValueError(
            "Duplicate species rows found in score table."
        )

    if defence["species"].duplicated().any():
        raise ValueError(
            "Duplicate species rows found in defence table."
        )

    conversions = [
        (
            "unpalatability_ps_ed50",
            "unpalatability_strength_0_1",
        ),
        (
            "toxicity_bs_ld50",
            "toxicity_strength_0_1",
        ),
    ]

    for source, output in conversions:
        parsed = defence[source].map(
            build_strength_score
        )

        defence[output] = [
            item[0]
            for item in parsed
        ]

        defence[f"{output}_status"] = [
            item[1]
            for item in parsed
        ]

    selected_defence_columns = (
        defence_columns
        + [
            "unpalatability_strength_0_1",
            "unpalatability_strength_0_1_status",
            "toxicity_strength_0_1",
            "toxicity_strength_0_1_status",
        ]
    )

    merged = defence[
        selected_defence_columns
    ].merge(
        scores[score_columns],
        on="species",
        how="inner",
        validate="one_to_one",
    )

    if len(merged) != 30:
        raise ValueError(
            "Expected 30 matched species, "
            f"but found {len(merged)}."
        )

    return (
        merged
        .sort_values("species")
        .reset_index(drop=True)
    )


def calculate_correlations(
    table: pd.DataFrame,
) -> pd.DataFrame:
    comparisons = [
        (
            "A",
            "unpalatability_strength_0_1",
            "mean_normalised_boldness",
            "Unpalatability and boldness",
        ),
        (
            "B",
            "unpalatability_strength_0_1",
            "mean_normalised_detectability",
            "Unpalatability and detectability",
        ),
        (
            "C",
            "toxicity_strength_0_1",
            "mean_normalised_boldness",
            "Toxicity and boldness",
        ),
        (
            "D",
            "toxicity_strength_0_1",
            "mean_normalised_detectability",
            "Toxicity and detectability",
        ),
    ]

    rows = []

    for (
        panel,
        defence_column,
        visual_column,
        title,
    ) in comparisons:
        subset = table[
            [
                defence_column,
                visual_column,
            ]
        ].dropna()

        x = subset[
            defence_column
        ].to_numpy(dtype=float)

        y = subset[
            visual_column
        ].to_numpy(dtype=float)

        pearson = pearsonr(x, y)
        spearman = spearmanr(x, y)

        slope, intercept = np.polyfit(
            x,
            y,
            1,
        )

        rows.append(
            {
                "panel": panel,
                "title": title,
                "defence_variable": defence_column,
                "visual_score": visual_column,
                "n_species": len(subset),
                "pearson_r": pearson.statistic,
                "pearson_p": pearson.pvalue,
                "pearson_r_squared": (
                    pearson.statistic ** 2
                ),
                "spearman_rho": spearman.statistic,
                "spearman_p": spearman.pvalue,
                "linear_slope": slope,
                "linear_intercept": intercept,
            }
        )

    results = pd.DataFrame(rows)

    results[
        "pearson_q_bh_4_tests"
    ] = benjamini_hochberg(
        results["pearson_p"].tolist()
    )

    results[
        "spearman_q_bh_4_tests"
    ] = benjamini_hochberg(
        results["spearman_p"].tolist()
    )

    results[
        "significant_after_bh"
    ] = (
        (
            results[
                "pearson_q_bh_4_tests"
            ] < 0.05
        )
        |
        (
            results[
                "spearman_q_bh_4_tests"
            ] < 0.05
        )
    )

    return results


def make_figure(
    table: pd.DataFrame,
    results: pd.DataFrame,
) -> None:
    colours = {
        "mean_normalised_boldness": "#0072B2",
        "mean_normalised_detectability": "#D55E00",
    }

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12, 10),
        sharex=True,
    )

    for ax, row in zip(
        axes.flat,
        results.itertuples(index=False),
    ):
        subset = table[
            [
                row.defence_variable,
                row.visual_score,
            ]
        ].dropna()

        x = subset[
            row.defence_variable
        ].to_numpy(dtype=float)

        y = subset[
            row.visual_score
        ].to_numpy(dtype=float)

        colour = colours[
            row.visual_score
        ]

        ax.scatter(
            x,
            y,
            s=46,
            color=colour,
            edgecolor="white",
            linewidth=0.5,
            alpha=0.88,
            zorder=3,
        )

        x_line = np.linspace(
            x.min(),
            x.max(),
            100,
        )

        ax.plot(
            x_line,
            (
                row.linear_intercept
                + row.linear_slope * x_line
            ),
            color=colour,
            linewidth=2,
            zorder=2,
        )

        # James requested that the grey panel grid lines be removed.
        ax.grid(False)
        ax.xaxis.grid(False)
        ax.yaxis.grid(False)

        ax.set_xlim(
            -0.04,
            1.04,
        )

        title = row.title

        if row.significant_after_bh:
            title = title + " *"

        ax.set_title(
            title,
            fontsize=13,
            pad=36,
        )

        statistics_text = (
            f"n = {row.n_species}   "
            f"r = {row.pearson_r:.2f}, "
            f"p = {row.pearson_p:.3f}, "
            f"q = {row.pearson_q_bh_4_tests:.3f}\n"
            f"Spearman ρ = {row.spearman_rho:.2f}, "
            f"p = {row.spearman_p:.3f}, "
            f"q = {row.spearman_q_bh_4_tests:.3f}"
        )

        ax.text(
            0.5,
            1.03,
            statistics_text,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=9.5,
        )

        ax.text(
            0.02,
            0.96,
            row.panel,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=17,
            fontweight="bold",
        )

    axes[0, 0].set_ylabel(
        "Mean normalised boldness"
    )

    axes[1, 0].set_ylabel(
        "Mean normalised boldness"
    )

    axes[0, 1].set_ylabel(
        "Mean normalised detectability"
    )

    axes[1, 1].set_ylabel(
        "Mean normalised detectability"
    )

    for ax in axes[1, :]:
        ax.set_xlabel(
            "Defence strength "
            "(0-1; higher values indicate stronger defence)"
        )

    fig.suptitle(
        (
            "Mean normalised colour-pattern scores "
            "and chemical defence"
        ),
        fontsize=17,
        y=0.995,
    )

    fig.tight_layout(
        rect=(0, 0, 1, 0.97),
        h_pad=3.4,
        w_pad=2.2,
    )

    fig.savefig(
        FIGURE_PNG,
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        FIGURE_PDF,
        bbox_inches="tight",
    )

    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = build_analysis_table()

    results = calculate_correlations(
        table
    )

    table.to_csv(
        ANALYSIS_TABLE_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    results.to_csv(
        CORRELATIONS_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    make_figure(
        table,
        results,
    )

    caption = (
        "Relationships between species-level mean normalised "
        "colour-pattern scores and continuous chemical-defence "
        "strength. (A) unpalatability and boldness; "
        "(B) unpalatability and detectability; "
        "(C) toxicity and boldness; and "
        "(D) toxicity and detectability. Each point represents "
        "one species, and solid lines show ordinary least-squares "
        "fits. Pearson and Spearman tests were corrected "
        "separately across the four planned relationships using "
        "the Benjamini-Hochberg method. The asterisk marks a "
        "relationship with q < 0.05 after correction."
    )

    CAPTION_TXT.write_text(
        caption + "\n",
        encoding="utf-8",
    )

    significant = results.loc[
        results["significant_after_bh"],
        "panel",
    ].tolist()

    summary = [
        "Mean normalised scores versus defence",
        "=======================================",
        "",
        results.to_string(index=False),
        "",
        (
            "Panels significant after BH correction: "
            + (
                ", ".join(significant)
                if significant
                else "none"
            )
        ),
        (
            "Grey panel grids were removed "
            "from the final figure."
        ),
    ]

    SUMMARY_TXT.write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )

    print("=" * 76)
    print(
        "FINAL COMPOSITE-SCORE FIGURE COMPLETE"
    )
    print("=" * 76)
    print(
        results.to_string(index=False)
    )
    print(
        f"\nSaved figure: {FIGURE_PNG}"
    )
    print(
        f"Saved correlations: {CORRELATIONS_CSV}"
    )


if __name__ == "__main__":
    main()