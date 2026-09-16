from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
    / "correlation_results"
)

BOLDNESS_CSV = OUTPUT_DIR / "boldness_metric_correlations.csv"
DETECTABILITY_CSV = OUTPUT_DIR / "detectability_metric_correlations.csv"

BOLDNESS_FIG = OUTPUT_DIR / "boldness_metric_correlations.png"
DETECTABILITY_FIG = OUTPUT_DIR / "detectability_metric_correlations.png"

EXPECTED_SPECIES = 30

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


def make_corr_figure(corr, labels, title, output_path):
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1)

    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)

    ax.set_title(title)

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j,
                i,
                f"{corr.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=8,
            )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Pearson correlation (r)")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def print_strong_pairs(corr, metric_names, threshold=0.70):
    pairs = []

    for i in range(len(metric_names)):
        for j in range(i + 1, len(metric_names)):
            r = corr.iloc[i, j]

            if abs(r) >= threshold:
                pairs.append(
                    (
                        metric_names[i],
                        metric_names[j],
                        float(r),
                    )
                )

    if not pairs:
        print(f"No metric pairs with |r| >= {threshold:.2f}.")
        return

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    for metric_a, metric_b, r in pairs:
        print(
            f"{metric_a}  <->  {metric_b}: "
            f"r = {r:.3f}"
        )


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find species summary: {INPUT_CSV}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)

    if len(df) != EXPECTED_SPECIES:
        raise ValueError(
            f"Expected {EXPECTED_SPECIES} species, "
            f"but found {len(df)}."
        )

    boldness_cols = [
        f"{metric}_mean"
        for metric in BOLDNESS_BASE
    ]

    detectability_cols = [
        f"{metric}_mean"
        for metric in DETECTABILITY_BASE
    ]

    missing = [
        c
        for c in boldness_cols + detectability_cols
        if c not in df.columns
    ]

    if missing:
        raise KeyError(
            "Missing columns: " + ", ".join(missing)
        )

    if df[boldness_cols + detectability_cols].isna().any().any():
        raise ValueError(
            "Missing values found in species-level metric means."
        )

    boldness_corr = df[boldness_cols].corr(method="pearson")
    detectability_corr = df[detectability_cols].corr(method="pearson")

    boldness_corr.index = BOLDNESS_BASE
    boldness_corr.columns = BOLDNESS_BASE

    detectability_corr.index = DETECTABILITY_BASE
    detectability_corr.columns = DETECTABILITY_BASE

    boldness_corr.to_csv(BOLDNESS_CSV)
    detectability_corr.to_csv(DETECTABILITY_CSV)

    make_corr_figure(
        boldness_corr,
        BOLDNESS_LABELS,
        "Correlations among species-level boldness metrics",
        BOLDNESS_FIG,
    )

    make_corr_figure(
        detectability_corr,
        DETECTABILITY_LABELS,
        "Correlations among species-level detectability metrics",
        DETECTABILITY_FIG,
    )

    print("=" * 72)
    print("CORRELATION CHECK COMPLETE")
    print("=" * 72)

    print("\nBoldness: strong correlations (|r| >= 0.70)")
    print_strong_pairs(
        boldness_corr,
        BOLDNESS_BASE,
        threshold=0.70,
    )

    print("\nDetectability: strong correlations (|r| >= 0.70)")
    print_strong_pairs(
        detectability_corr,
        DETECTABILITY_BASE,
        threshold=0.70,
    )

    print("\nSaved:")
    print(BOLDNESS_CSV.relative_to(PROJECT_ROOT).as_posix())
    print(DETECTABILITY_CSV.relative_to(PROJECT_ROOT).as_posix())
    print(BOLDNESS_FIG.relative_to(PROJECT_ROOT).as_posix())
    print(DETECTABILITY_FIG.relative_to(PROJECT_ROOT).as_posix())


if __name__ == "__main__":
    main()
