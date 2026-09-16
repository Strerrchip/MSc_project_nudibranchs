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
    / "descriptive_results"
)

BOLDNESS_FIGURE = (
    OUTPUT_DIR
    / "species_boldness_heatmap.png"
)

DETECTABILITY_FIGURE = (
    OUTPUT_DIR
    / "species_detectability_heatmap.png"
)

IMAGE_COUNT_FIGURE = (
    OUTPUT_DIR
    / "species_image_counts.png"
)

ZSCORE_CSV = (
    OUTPUT_DIR
    / "species_visibility_metric_zscores.csv"
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
# Helper functions
# =========================

def zscore_columns(dataframe):
    means = dataframe.mean(axis=0)
    sds = dataframe.std(axis=0, ddof=1)

    if (sds <= 0).any():
        bad = sds[sds <= 0].index.tolist()
        raise ValueError(
            "Cannot z-score zero-variance metrics: "
            + ", ".join(bad)
        )

    return (dataframe - means) / sds


def make_heatmap(
    matrix,
    species_names,
    metric_labels,
    title,
    output_path,
):
    fig, ax = plt.subplots(
        figsize=(11, 12)
    )

    image = ax.imshow(
        matrix,
        aspect="auto",
    )

    ax.set_yticks(
        np.arange(len(species_names))
    )
    ax.set_yticklabels(
        species_names,
        fontsize=8,
    )

    ax.set_xticks(
        np.arange(len(metric_labels))
    )
    ax.set_xticklabels(
        metric_labels,
        rotation=45,
        ha="right",
        fontsize=9,
    )

    ax.set_xlabel(
        "Visual metric"
    )
    ax.set_ylabel(
        "Species"
    )
    ax.set_title(title)

    cbar = fig.colorbar(
        image,
        ax=ax,
    )
    cbar.set_label(
        "Standardised species mean (z-score)"
    )

    fig.tight_layout()

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

    boldness_mean_cols = [
        f"{metric}_mean"
        for metric in BOLDNESS_BASE
    ]

    detectability_mean_cols = [
        f"{metric}_mean"
        for metric in DETECTABILITY_BASE
    ]

    required_columns = [
        "species",
        "n_images",
        *boldness_mean_cols,
        *detectability_mean_cols,
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

    if df[required_columns].isna().any().any():
        raise ValueError(
            "Missing values found in descriptive-result inputs."
        )

    # Alphabetical order keeps the figure neutral and easy to compare
    # with tables and later analyses.
    df = (
        df.sort_values("species")
        .reset_index(drop=True)
    )

    species_names = (
        df["species"]
        .astype(str)
        .tolist()
    )

    boldness_raw = df[
        boldness_mean_cols
    ].copy()

    detectability_raw = df[
        detectability_mean_cols
    ].copy()

    boldness_z = zscore_columns(
        boldness_raw
    )

    detectability_z = zscore_columns(
        detectability_raw
    )

    zscore_output = pd.DataFrame(
        {
            "species": species_names,
            "n_images": df["n_images"],
        }
    )

    for metric, column in zip(
        BOLDNESS_BASE,
        boldness_z.columns,
    ):
        zscore_output[
            f"{metric}_z"
        ] = boldness_z[column].values

    for metric, column in zip(
        DETECTABILITY_BASE,
        detectability_z.columns,
    ):
        zscore_output[
            f"{metric}_z"
        ] = detectability_z[column].values

    zscore_output.to_csv(
        ZSCORE_CSV,
        index=False,
    )

    make_heatmap(
        boldness_z.to_numpy(),
        species_names,
        BOLDNESS_LABELS,
        "Species-level internal pattern boldness metrics",
        BOLDNESS_FIGURE,
    )

    make_heatmap(
        detectability_z.to_numpy(),
        species_names,
        DETECTABILITY_LABELS,
        "Species-level animal-background detectability metrics",
        DETECTABILITY_FIGURE,
    )

    # Sampling-effort figure.
    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    ax.barh(
        species_names,
        df["n_images"],
    )

    ax.set_xlabel(
        "Number of accepted images"
    )
    ax.set_ylabel(
        "Species"
    )
    ax.set_title(
        "Final image sample size by species"
    )

    ax.set_xlim(
        0,
        max(df["n_images"]) + 1,
    )

    ax.tick_params(
        axis="y",
        labelsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        IMAGE_COUNT_FIGURE,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("=" * 72)
    print("DESCRIPTIVE RESULTS COMPLETE")
    print("=" * 72)
    print(
        f"Species: {len(df)}"
    )
    print(
        f"Images represented: "
        f"{int(df['n_images'].sum())}"
    )
    print(
        f"Images per species: "
        f"{int(df['n_images'].min())}-"
        f"{int(df['n_images'].max())}"
    )
    print()
    print("Saved:")
    print(
        BOLDNESS_FIGURE.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        DETECTABILITY_FIGURE.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        IMAGE_COUNT_FIGURE.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )
    print(
        ZSCORE_CSV.relative_to(
            PROJECT_ROOT
        ).as_posix()
    )


if __name__ == "__main__":
    main()
