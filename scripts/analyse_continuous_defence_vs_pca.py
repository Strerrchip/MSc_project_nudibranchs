from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "visual_defence_analysis_table.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "continuous_defence_results"
)

RESULTS_CSV = (
    OUTPUT_DIR
    / "pca_vs_continuous_defence_correlations.csv"
)

UNPALATABILITY_FIG = (
    OUTPUT_DIR
    / "unpalatability_pca_correlations.png"
)

TOXICITY_FIG = (
    OUTPUT_DIR
    / "toxicity_pca_correlations.png"
)

EXPECTED_SPECIES = 30

VISUAL_AXES = [
    "boldness_PC1",
    "boldness_PC2",
    "detectability_PC1",
    "detectability_PC2",
    "detectability_PC3",
    "detectability_PC4",
]

AXIS_LABELS = {
    "boldness_PC1": "Boldness PC1",
    "boldness_PC2": "Boldness PC2",
    "detectability_PC1": "Detectability PC1",
    "detectability_PC2": "Detectability PC2",
    "detectability_PC3": "Detectability PC3",
    "detectability_PC4": "Detectability PC4",
}

DEFENCE_VARIABLES = {
    "unpalatability_strength_0_1": "Unpalatability strength",
    "toxicity_strength_0_1": "Toxicity strength",
}


# =========================
# Statistics helpers
# =========================

def benjamini_hochberg(p_values):
    """
    Benjamini-Hochberg false-discovery-rate correction.
    Returns adjusted p-values in original order.
    """
    p = np.asarray(p_values, dtype=float)
    n = len(p)

    order = np.argsort(p)
    ranked = p[order]

    adjusted_ranked = np.empty(n, dtype=float)

    running_min = 1.0

    for i in range(n - 1, -1, -1):
        rank = i + 1
        adjusted = ranked[i] * n / rank
        running_min = min(running_min, adjusted)
        adjusted_ranked[i] = min(running_min, 1.0)

    adjusted = np.empty(n, dtype=float)
    adjusted[order] = adjusted_ranked

    return adjusted


def analyse_pair(df, defence_col, visual_col):
    subset = df[
        ["species", defence_col, visual_col]
    ].dropna()

    n = len(subset)

    if n < 3:
        raise ValueError(
            f"Not enough observations for {defence_col} vs {visual_col}."
        )

    x = subset[defence_col].astype(float).to_numpy()
    y = subset[visual_col].astype(float).to_numpy()

    pearson_r, pearson_p = pearsonr(x, y)
    spearman_rho, spearman_p = spearmanr(x, y)

    slope, intercept = np.polyfit(x, y, 1)

    return {
        "defence_variable": defence_col,
        "visual_axis": visual_col,
        "n_species": n,
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "pearson_r_squared": float(pearson_r ** 2),
        "linear_slope": float(slope),
        "linear_intercept": float(intercept),
        "spearman_rho": float(spearman_rho),
        "spearman_p": float(spearman_p),
    }


def make_correlation_figure(
    results_df,
    defence_col,
    title,
    output_path,
):
    subset = (
        results_df[
            results_df["defence_variable"]
            == defence_col
        ]
        .set_index("visual_axis")
        .loc[VISUAL_AXES]
    )

    values = subset[
        "pearson_r"
    ].to_numpy().reshape(-1, 1)

    labels = [
        AXIS_LABELS[axis]
        for axis in VISUAL_AXES
    ]

    fig, ax = plt.subplots(
        figsize=(5.5, 7.5)
    )

    im = ax.imshow(
        values,
        vmin=-1,
        vmax=1,
        aspect="auto",
    )

    ax.set_yticks(
        np.arange(len(labels))
    )
    ax.set_yticklabels(
        labels
    )

    ax.set_xticks([0])
    ax.set_xticklabels(
        [DEFENCE_VARIABLES[defence_col]]
    )

    ax.set_title(title)

    for i, axis in enumerate(VISUAL_AXES):
        row = subset.loc[axis]

        ax.text(
            0,
            i,
            (
                f"r={row['pearson_r']:.2f}\n"
                f"p={row['pearson_p']:.3f}\n"
                f"FDR={row['pearson_p_fdr']:.3f}"
            ),
            ha="center",
            va="center",
            fontsize=9,
        )

    cbar = fig.colorbar(
        im,
        ax=ax,
    )
    cbar.set_label(
        "Pearson correlation (r)"
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def make_scatterplot(
    df,
    defence_col,
    visual_col,
    result_row,
):
    subset = df[
        ["species", defence_col, visual_col]
    ].dropna()

    x = subset[
        defence_col
    ].astype(float).to_numpy()

    y = subset[
        visual_col
    ].astype(float).to_numpy()

    fig, ax = plt.subplots(
        figsize=(7, 5.5)
    )

    ax.scatter(
        x,
        y,
    )

    x_line = np.linspace(
        x.min(),
        x.max(),
        100,
    )

    y_line = (
        result_row["linear_intercept"]
        + result_row["linear_slope"] * x_line
    )

    ax.plot(
        x_line,
        y_line,
    )

    ax.set_xlabel(
        DEFENCE_VARIABLES[defence_col]
        + " (0-1; higher = stronger defence)"
    )

    ax.set_ylabel(
        AXIS_LABELS[visual_col]
    )

    ax.set_title(
        f"{AXIS_LABELS[visual_col]} vs "
        f"{DEFENCE_VARIABLES[defence_col].lower()}"
    )

    annotation = (
        f"n = {int(result_row['n_species'])}\n"
        f"Pearson r = {result_row['pearson_r']:.3f}\n"
        f"p = {result_row['pearson_p']:.3f}\n"
        f"FDR p = {result_row['pearson_p_fdr']:.3f}\n"
        f"Spearman rho = {result_row['spearman_rho']:.3f}"
    )

    ax.text(
        0.03,
        0.97,
        annotation,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
    )

    fig.tight_layout()

    filename = (
        f"{defence_col}_vs_{visual_col}.png"
    )

    output_path = (
        OUTPUT_DIR
        / "scatterplots"
        / filename
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find analysis table: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(
        INPUT_CSV
    )

    if len(df) != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {len(df)}."
        )

    required_columns = [
        "species",
        *VISUAL_AXES,
        *DEFENCE_VARIABLES.keys(),
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    result_rows = []

    for defence_col in DEFENCE_VARIABLES:
        for visual_col in VISUAL_AXES:
            result_rows.append(
                analyse_pair(
                    df,
                    defence_col,
                    visual_col,
                )
            )

    results = pd.DataFrame(
        result_rows
    )

    # Correct the six PCA-axis tests separately within
    # each defence variable.
    results[
        "pearson_p_fdr"
    ] = np.nan

    results[
        "spearman_p_fdr"
    ] = np.nan

    for defence_col in DEFENCE_VARIABLES:
        mask = (
            results[
                "defence_variable"
            ]
            == defence_col
        )

        results.loc[
            mask,
            "pearson_p_fdr",
        ] = benjamini_hochberg(
            results.loc[
                mask,
                "pearson_p",
            ].to_numpy()
        )

        results.loc[
            mask,
            "spearman_p_fdr",
        ] = benjamini_hochberg(
            results.loc[
                mask,
                "spearman_p",
            ].to_numpy()
        )

    results.to_csv(
        RESULTS_CSV,
        index=False,
    )

    make_correlation_figure(
        results,
        "unpalatability_strength_0_1",
        "PCA axes vs unpalatability strength",
        UNPALATABILITY_FIG,
    )

    make_correlation_figure(
        results,
        "toxicity_strength_0_1",
        "PCA axes vs toxicity strength",
        TOXICITY_FIG,
    )

    for _, row in results.iterrows():
        make_scatterplot(
            df,
            row["defence_variable"],
            row["visual_axis"],
            row,
        )

    print("=" * 88)
    print("CONTINUOUS DEFENCE ANALYSIS COMPLETE")
    print("=" * 88)

    for defence_col, defence_label in DEFENCE_VARIABLES.items():
        print()
        print(defence_label.upper())
        print("-" * 88)

        subset = (
            results[
                results["defence_variable"]
                == defence_col
            ]
            .copy()
        )

        subset["axis"] = subset[
            "visual_axis"
        ].map(
            AXIS_LABELS
        )

        display_cols = [
            "axis",
            "n_species",
            "pearson_r",
            "pearson_p",
            "pearson_p_fdr",
            "spearman_rho",
            "spearman_p",
        ]

        print(
            subset[
                display_cols
            ].to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}",
            )
        )

    print()
    print("Saved:")
    print(
        RESULTS_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        UNPALATABILITY_FIG.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        TOXICITY_FIG.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        (
            OUTPUT_DIR
            / "scatterplots"
        )
        .relative_to(
            PROJECT_ROOT
        )
        .as_posix()
    )

    print()
    print(
        "Interpretation note: PCA axis signs are arbitrary. "
        "Any biological interpretation must use the PCA loadings, "
        "not the sign of a correlation alone."
    )


if __name__ == "__main__":
    main()
