"""Create the two-panel 30-species colour-pattern heatmap."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def first_existing(*relative_paths: str) -> Path:
    candidates = [
        PROJECT_ROOT / path
        for path in relative_paths
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = "\n".join(
        f"  - {path}"
        for path in candidates
    )

    raise FileNotFoundError(
        f"Could not find the score table:\n{searched}"
    )


INPUT_CSV = first_existing(
    (
        "processed_data/automated_image_analysis/"
        "composite_scores/"
        "visibility_composite_scores.csv"
    ),
    (
        "processed_data/automated_image_analysis/"
        "composite_scores/"
        "visibility_mean_normalised_scores.csv"
    ),
    "composite_scores/visibility_composite_scores.csv",
    "visibility_mean_normalised_scores.csv",
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "descriptive_results"
)

FIGURE_PNG = (
    OUTPUT_DIR
    / "species_visibility_metrics_heatmap_2panel.png"
)

FIGURE_PDF = (
    OUTPUT_DIR
    / "species_visibility_metrics_heatmap_2panel.pdf"
)

VALUES_CSV = (
    OUTPUT_DIR
    / "species_visibility_metric_zscores.csv"
)

CAPTION_TXT = (
    OUTPUT_DIR
    / "species_visibility_metrics_heatmap_2panel_caption.txt"
)


BOLDNESS_COLUMNS = [
    "animal_gray_sd_z",
    "animal_saturation_sd_z",
    "animal_edge_density_z",
    "animal_luminance_edge_cv_z",
    "animal_chromatic_edge_mean_z",
    "animal_chromatic_edge_cv_z",
]

BOLDNESS_LABELS = [
    "Gray SD",
    "Saturation SD",
    "Edge density",
    "Luminance edge CV",
    "Chromatic edge mean",
    "Chromatic edge CV",
]


DETECTABILITY_COLUMNS = [
    "gray_contrast_abs_z",
    "saturation_contrast_abs_z",
    "lab_colour_distance_z",
    "luminance_edge_cv_difference_z",
    "chromatic_edge_cv_difference_z",
    "gray_sd_difference_z",
    "saturation_sd_difference_z",
    "edge_density_difference_z",
    "chromatic_edge_mean_difference_z",
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


def main() -> None:
    data = pd.read_csv(INPUT_CSV)

    required_columns = [
        "species",
        "n_images",
        *BOLDNESS_COLUMNS,
        *DETECTABILITY_COLUMNS,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing heatmap columns: "
            + ", ".join(missing_columns)
        )

    if len(data) != 30:
        raise ValueError(
            f"Expected 30 species, but found {len(data)}."
        )

    if data["species"].duplicated().any():
        raise ValueError(
            "Duplicate species rows were found."
        )

    if data[required_columns].isna().any().any():
        raise ValueError(
            "Missing values were found "
            "in the heatmap inputs."
        )

    total_images = int(
        data["n_images"].sum()
    )

    if total_images != 295:
        raise ValueError(
            "Expected 295 images, but n_images "
            f"sums to {total_images}."
        )

    # Alphabetical ordering avoids choosing an order
    # based on the expected biological result.
    data = (
        data
        .sort_values("species")
        .reset_index(drop=True)
    )

    species_names = (
        data["species"]
        .astype(str)
        .tolist()
    )

    boldness_matrix = data[
        BOLDNESS_COLUMNS
    ].to_numpy(dtype=float)

    detectability_matrix = data[
        DETECTABILITY_COLUMNS
    ].to_numpy(dtype=float)

    all_values = np.concatenate(
        [
            boldness_matrix.ravel(),
            detectability_matrix.ravel(),
        ]
    )

    colour_limit = float(
        np.max(np.abs(all_values))
    )

    if colour_limit == 0:
        raise ValueError(
            "All z-scores are zero; "
            "a heatmap cannot be drawn."
        )

    colour_norm = TwoSlopeNorm(
        vmin=-colour_limit,
        vcenter=0,
        vmax=colour_limit,
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(16, 12),
        gridspec_kw={
            "width_ratios": [6, 9]
        },
        sharey=True,
    )

    panels = [
        (
            axes[0],
            boldness_matrix,
            BOLDNESS_LABELS,
            "A",
            "Internal pattern boldness",
        ),
        (
            axes[1],
            detectability_matrix,
            DETECTABILITY_LABELS,
            "B",
            "Animal-background detectability",
        ),
    ]

    heatmap_image = None

    for (
        axis,
        matrix,
        metric_labels,
        panel_label,
        panel_title,
    ) in panels:
        heatmap_image = axis.imshow(
            matrix,
            aspect="auto",
            cmap="RdBu_r",
            norm=colour_norm,
            interpolation="nearest",
        )

        axis.set_xticks(
            np.arange(len(metric_labels))
        )

        axis.set_xticklabels(
            metric_labels,
            rotation=45,
            ha="right",
            fontsize=9,
        )

        axis.set_title(
            panel_title,
            fontsize=13,
            pad=10,
        )

        axis.tick_params(
            length=0
        )

        # Do not add grey table or panel grid lines.
        axis.grid(False)
        axis.xaxis.grid(False)
        axis.yaxis.grid(False)

        axis.text(
            0.01,
            0.99,
            panel_label,
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=17,
            fontweight="bold",
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.75,
            },
        )

    axes[0].set_yticks(
        np.arange(len(species_names))
    )

    axes[0].set_yticklabels(
        species_names,
        fontsize=8,
        fontstyle="italic",
    )

    axes[0].set_ylabel(
        "Species"
    )

    colour_axis = fig.add_axes(
        [0.93, 0.27, 0.016, 0.48]
    )

    colour_bar = fig.colorbar(
        heatmap_image,
        cax=colour_axis,
    )

    colour_bar.set_label(
        "Standardised species mean (z-score)"
    )

    fig.suptitle(
        (
            "Colour-pattern variation among "
            "30 nudibranch species"
        ),
        fontsize=17,
        y=0.995,
    )

    fig.subplots_adjust(
        left=0.24,
        right=0.90,
        bottom=0.23,
        top=0.93,
        wspace=0.04,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
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

    output_columns = [
        "species",
        "n_images",
        *BOLDNESS_COLUMNS,
        *DETECTABILITY_COLUMNS,
    ]

    data[output_columns].to_csv(
        VALUES_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    caption = (
        "Species-level variation in colour-pattern metrics "
        "derived from 295 online images of 30 nudibranch "
        "species. (A) Six animal-only metrics used to "
        "describe internal pattern boldness. (B) Nine "
        "contrasts between each animal and its immediate "
        "environment used to describe detectability. Each "
        "cell shows a species mean standardised across the "
        "30 species; red values are above the among-species "
        "mean and blue values are below it. Species are "
        "ordered alphabetically."
    )

    CAPTION_TXT.write_text(
        caption + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("30-SPECIES HEATMAP COMPLETE")
    print("=" * 72)
    print(f"Species: {len(data)}")
    print(f"Images represented: {total_images}")
    print(f"Saved figure: {FIGURE_PNG}")
    print(f"Saved values: {VALUES_CSV}")


if __name__ == "__main__":
    main()