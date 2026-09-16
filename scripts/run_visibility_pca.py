from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "species_metrics"
    / "sam_scaled_ring120_visibility_species_summary_final.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "pca_results"
)

EXPECTED_SPECIES = 30


# =========================
# Metric definitions
# =========================

BOLDNESS_BASE = [
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_edge_density",
    "animal_luminance_edge_cv",
    "animal_chromatic_edge_mean",
    "animal_chromatic_edge_cv",
]

DETECTABILITY_BASE = [
    "gray_contrast_abs",
    "saturation_contrast_abs",
    "lab_colour_distance",
    "luminance_edge_cv_difference",
    "chromatic_edge_cv_difference",
    "gray_sd_difference",
    "saturation_sd_difference",
    "edge_density_difference",
    "chromatic_edge_mean_difference",
]

BOLDNESS_LABELS = [
    "Gray SD",
    "Saturation SD",
    "Edge density",
    "Luminance edge CV",
    "Chromatic edge mean",
    "Chromatic edge CV",
]

DETECTABILITY_LABELS = [
    "Gray contrast",
    "Saturation contrast",
    "CIELAB distance",
    "Luminance edge CV diff.",
    "Chromatic edge CV diff.",
    "Gray SD diff.",
    "Saturation SD diff.",
    "Edge density diff.",
    "Chromatic edge mean diff.",
]


# =========================
# PCA helpers
# =========================

def standardise_matrix(df):
    means = df.mean(axis=0)
    sds = df.std(axis=0, ddof=1)

    if (sds <= 0).any():
        bad = sds[sds <= 0].index.tolist()
        raise ValueError(
            "Zero-variance metrics cannot be used in PCA: "
            + ", ".join(bad)
        )

    z = (df - means) / sds
    return z, means, sds


def run_pca(z_df):
    """
    PCA by singular value decomposition on the standardised
    species-by-metric matrix.
    """
    x = z_df.to_numpy(dtype=float)

    # z-scored columns are already centred, but subtracting tiny numerical
    # residual means makes the calculation explicit.
    x = x - x.mean(axis=0, keepdims=True)

    u, s, vt = np.linalg.svd(
        x,
        full_matrices=False,
    )

    scores = u * s
    loadings = vt.T

    eigenvalues = (s ** 2) / (x.shape[0] - 1)
    explained_ratio = (
        eigenvalues / eigenvalues.sum()
    )

    return (
        scores,
        loadings,
        eigenvalues,
        explained_ratio,
    )


def save_pca_outputs(
    df,
    metric_columns,
    metric_labels,
    prefix,
):
    raw = df[metric_columns].copy()
    z, means, sds = standardise_matrix(raw)

    (
        scores,
        loadings,
        eigenvalues,
        explained_ratio,
    ) = run_pca(z)

    n_components = loadings.shape[1]
    pc_names = [
        f"PC{i}"
        for i in range(1, n_components + 1)
    ]

    # Scores
    scores_df = pd.DataFrame(
        scores,
        columns=pc_names,
    )
    scores_df.insert(
        0,
        "species",
        df["species"].values,
    )

    scores_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_scores.csv"
    )
    scores_df.to_csv(
        scores_path,
        index=False,
    )

    # Loadings
    loadings_df = pd.DataFrame(
        loadings,
        index=metric_labels,
        columns=pc_names,
    )
    loadings_df.index.name = "metric"

    loadings_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_loadings.csv"
    )
    loadings_df.to_csv(
        loadings_path
    )

    # Explained variance
    explained_df = pd.DataFrame(
        {
            "component": pc_names,
            "eigenvalue": eigenvalues,
            "explained_variance_ratio": explained_ratio,
            "explained_variance_percent": explained_ratio * 100,
            "cumulative_variance_percent": np.cumsum(
                explained_ratio
            ) * 100,
        }
    )

    explained_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_explained_variance.csv"
    )
    explained_df.to_csv(
        explained_path,
        index=False,
    )

    # Standardisation parameters
    standardisation_df = pd.DataFrame(
        {
            "metric": metric_labels,
            "mean": means.values,
            "sd": sds.values,
        }
    )

    standardisation_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_standardisation.csv"
    )
    standardisation_df.to_csv(
        standardisation_path,
        index=False,
    )

    # Scree plot
    fig, ax = plt.subplots(
        figsize=(7, 5)
    )

    ax.plot(
        np.arange(1, n_components + 1),
        explained_ratio * 100,
        marker="o",
    )

    ax.set_xlabel(
        "Principal component"
    )
    ax.set_ylabel(
        "Explained variance (%)"
    )
    ax.set_title(
        f"{prefix.capitalize()} PCA: explained variance"
    )

    ax.set_xticks(
        np.arange(1, n_components + 1)
    )

    fig.tight_layout()

    scree_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_scree.png"
    )

    fig.savefig(
        scree_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # PC1-PC2 species plot
    fig, ax = plt.subplots(
        figsize=(9, 7)
    )

    ax.scatter(
        scores[:, 0],
        scores[:, 1],
    )

    for i, species in enumerate(
        df["species"].astype(str)
    ):
        ax.annotate(
            species,
            (
                scores[i, 0],
                scores[i, 1],
            ),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=7,
        )

    pc1_pct = explained_ratio[0] * 100
    pc2_pct = explained_ratio[1] * 100

    ax.set_xlabel(
        f"PC1 ({pc1_pct:.1f}% variance)"
    )
    ax.set_ylabel(
        f"PC2 ({pc2_pct:.1f}% variance)"
    )
    ax.set_title(
        f"{prefix.capitalize()} PCA: species scores"
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )
    ax.axvline(
        0,
        linewidth=0.8,
    )

    fig.tight_layout()

    scores_fig_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_species_pc1_pc2.png"
    )

    fig.savefig(
        scores_fig_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    # PC1/PC2 loading plot
    fig, ax = plt.subplots(
        figsize=(8, 7)
    )

    ax.scatter(
        loadings[:, 0],
        loadings[:, 1],
    )

    for i, label in enumerate(
        metric_labels
    ):
        ax.annotate(
            label,
            (
                loadings[i, 0],
                loadings[i, 1],
            ),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_xlabel(
        "PC1 loading"
    )
    ax.set_ylabel(
        "PC2 loading"
    )
    ax.set_title(
        f"{prefix.capitalize()} PCA: metric loadings"
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )
    ax.axvline(
        0,
        linewidth=0.8,
    )

    fig.tight_layout()

    loadings_fig_path = (
        OUTPUT_DIR
        / f"{prefix}_pca_loadings_pc1_pc2.png"
    )

    fig.savefig(
        loadings_fig_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)

    print()
    print("-" * 72)
    print(f"{prefix.upper()} PCA")
    print("-" * 72)
    print(
        f"PC1 explained variance: "
        f"{pc1_pct:.2f}%"
    )
    print(
        f"PC2 explained variance: "
        f"{pc2_pct:.2f}%"
    )
    print(
        f"PC1 + PC2 cumulative: "
        f"{(pc1_pct + pc2_pct):.2f}%"
    )

    print("\nPC1 loadings:")
    pc1_order = np.argsort(
        np.abs(loadings[:, 0])
    )[::-1]

    for i in pc1_order:
        print(
            f"  {metric_labels[i]}: "
            f"{loadings[i, 0]:.3f}"
        )

    print("\nPC2 loadings:")
    pc2_order = np.argsort(
        np.abs(loadings[:, 1])
    )[::-1]

    for i in pc2_order:
        print(
            f"  {metric_labels[i]}: "
            f"{loadings[i, 1]:.3f}"
        )

    return {
        "scores": scores_path,
        "loadings": loadings_path,
        "explained": explained_path,
        "standardisation": standardisation_path,
        "scree": scree_path,
        "scores_figure": scores_fig_path,
        "loadings_figure": loadings_fig_path,
    }


# =========================
# Main workflow
# =========================

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find species summary: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_CSV)

    if len(df) != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {len(df)}."
        )

    if df["species"].duplicated().any():
        raise ValueError(
            "Duplicate species rows found."
        )

    boldness_cols = [
        f"{metric}_mean"
        for metric in BOLDNESS_BASE
    ]

    detectability_cols = [
        f"{metric}_mean"
        for metric in DETECTABILITY_BASE
    ]

    missing_columns = [
        c
        for c in boldness_cols + detectability_cols
        if c not in df.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing columns: "
            + ", ".join(missing_columns)
        )

    if df[
        boldness_cols + detectability_cols
    ].isna().any().any():
        raise ValueError(
            "Missing values found in PCA inputs."
        )

    # Keep one neutral species order across both PCAs.
    df = (
        df.sort_values("species")
        .reset_index(drop=True)
    )

    print("=" * 72)
    print("SEPARATE VISIBILITY PCAs")
    print("=" * 72)
    print(
        "Using species-level means, z-standardised "
        "within each PCA."
    )
    print(
        f"Species: {len(df)}"
    )

    boldness_outputs = save_pca_outputs(
        df,
        boldness_cols,
        BOLDNESS_LABELS,
        "boldness",
    )

    detectability_outputs = save_pca_outputs(
        df,
        detectability_cols,
        DETECTABILITY_LABELS,
        "detectability",
    )

    print()
    print("=" * 72)
    print("PCA COMPLETE")
    print("=" * 72)
    print("Outputs saved in:")
    print(
        OUTPUT_DIR.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )


if __name__ == "__main__":
    main()
