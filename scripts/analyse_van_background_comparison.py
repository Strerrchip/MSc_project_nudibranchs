from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


# ============================================================
# File paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPARISON_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "van_background_comparison"
)

INPUT_FILE = (
    COMPARISON_DIR
    / "van_online_background_comparison_zscores.csv"
)

RESULTS_FILE = (
    COMPARISON_DIR
    / "van_background_correlations.csv"
)

FIGURE_PNG = (
    COMPARISON_DIR
    / "van_background_comparison_2x2.png"
)

FIGURE_PDF = (
    COMPARISON_DIR
    / "van_background_comparison_2x2.pdf"
)

SUMMARY_FILE = (
    COMPARISON_DIR
    / "van_background_comparison_summary.txt"
)


# ============================================================
# Metric pairs
# ============================================================

METRIC_PAIRS = [
    {
        "comparison": "luminance_edge_mean",
        "panel_title": "Mean luminance-edge strength",
        "online_z": "online_luminance_edge_mean_z",
        "van_z": "van_luminance_edge_mean_z",
    },
    {
        "comparison": "luminance_edge_cv",
        "panel_title": "Variation in luminance-edge strength",
        "online_z": "online_luminance_edge_cv_z",
        "van_z": "van_luminance_edge_cv_z",
    },
    {
        "comparison": "chromatic_edge_mean",
        "panel_title": "Mean chromatic-edge strength",
        "online_z": "online_chromatic_edge_mean_z",
        "van_z": "van_chromatic_edge_mean_z",
    },
    {
        "comparison": "chromatic_edge_cv",
        "panel_title": "Variation in chromatic-edge strength",
        "online_z": "online_chromatic_edge_cv_z",
        "van_z": "van_chromatic_edge_cv_z",
    },
]

DISTANCES = [
    "2cm",
    "30cm",
]

DISTANCE_LABELS = {
    "2cm": "2 cm",
    "30cm": "30 cm",
}

DISTANCE_COLOURS = {
    "2cm": "#0072B2",
    "30cm": "#D55E00",
}

DISTANCE_MARKERS = {
    "2cm": "o",
    "30cm": "^",
}

DISTANCE_LINESTYLES = {
    "2cm": "-",
    "30cm": "--",
}


# ============================================================
# Statistical functions
# ============================================================

def benjamini_hochberg(p_values):
    """
    Apply the Benjamini-Hochberg false-discovery-rate
    correction.

    The adjusted p-values are returned in the original order.
    """

    p_values = np.asarray(
        p_values,
        dtype=float,
    )

    number_of_tests = len(
        p_values
    )

    order = np.argsort(
        p_values
    )

    ranked_p_values = (
        p_values[order]
    )

    adjusted_ranked = np.empty(
        number_of_tests,
        dtype=float,
    )

    running_minimum = 1.0

    for index in range(
        number_of_tests - 1,
        -1,
        -1,
    ):

        rank = index + 1

        adjusted_value = (
            ranked_p_values[index]
            * number_of_tests
            / rank
        )

        running_minimum = min(
            running_minimum,
            adjusted_value,
        )

        adjusted_ranked[index] = min(
            running_minimum,
            1.0,
        )

    adjusted_p_values = np.empty(
        number_of_tests,
        dtype=float,
    )

    adjusted_p_values[
        order
    ] = adjusted_ranked

    return adjusted_p_values


def analyse_pair(
    data,
    metric_pair,
    distance,
):
    """
    Calculate Pearson and Spearman correlations for one
    metric pair at one viewing distance.
    """

    online_column = (
        metric_pair["online_z"]
    )

    van_column = (
        metric_pair["van_z"]
    )

    subset = (
        data.loc[
            data["distance"].eq(
                distance
            ),
            [
                "species",
                online_column,
                van_column,
            ],
        ]
        .dropna()
        .copy()
    )

    if len(subset) != 9:
        raise ValueError(
            f"Expected 9 species for "
            f"{metric_pair['comparison']} at {distance}, "
            f"but found {len(subset)}."
        )

    online_values = (
        subset[
            online_column
        ]
        .astype(float)
        .to_numpy()
    )

    van_values = (
        subset[
            van_column
        ]
        .astype(float)
        .to_numpy()
    )

    pearson_result = pearsonr(
        online_values,
        van_values,
    )

    spearman_result = spearmanr(
        online_values,
        van_values,
    )

    slope, intercept = np.polyfit(
        online_values,
        van_values,
        1,
    )

    return {
        "comparison": metric_pair["comparison"],
        "distance": distance,
        "n_species": len(subset),
        "online_metric_z": online_column,
        "van_metric_z": van_column,
        "pearson_r": float(
            pearson_result.statistic
        ),
        "pearson_p": float(
            pearson_result.pvalue
        ),
        "pearson_r_squared": float(
            pearson_result.statistic ** 2
        ),
        "spearman_rho": float(
            spearman_result.statistic
        ),
        "spearman_p": float(
            spearman_result.pvalue
        ),
        "linear_slope": float(
            slope
        ),
        "linear_intercept": float(
            intercept
        ),
    }


# ============================================================
# Figure functions
# ============================================================

def add_regression_line(
    axis,
    x_values,
    y_values,
    colour,
    linestyle,
):
    """
    Add a least-squares regression line to one panel.
    """

    slope, intercept = np.polyfit(
        x_values,
        y_values,
        1,
    )

    x_line = np.linspace(
        x_values.min(),
        x_values.max(),
        100,
    )

    y_line = (
        intercept
        + slope * x_line
    )

    axis.plot(
        x_line,
        y_line,
        color=colour,
        linestyle=linestyle,
        linewidth=1.4,
        alpha=0.85,
        zorder=2,
    )


def make_comparison_figure(
    data,
    results,
):
    """
    Create the final 2 x 2 external-comparison figure.
    """

    figure, axes = plt.subplots(
        2,
        2,
        figsize=(11, 9),
        sharex=True,
        sharey=True,
    )

    panel_letters = [
        "A",
        "B",
        "C",
        "D",
    ]

    for (
        axis,
        metric_pair,
        panel_letter,
    ) in zip(
        axes.flat,
        METRIC_PAIRS,
        panel_letters,
    ):

        annotation_lines = []

        for distance in DISTANCES:

            online_column = (
                metric_pair["online_z"]
            )

            van_column = (
                metric_pair["van_z"]
            )

            subset = (
                data.loc[
                    data["distance"].eq(
                        distance
                    ),
                    [
                        "species",
                        online_column,
                        van_column,
                    ],
                ]
                .sort_values("species")
                .copy()
            )

            x_values = (
                subset[
                    online_column
                ]
                .astype(float)
                .to_numpy()
            )

            y_values = (
                subset[
                    van_column
                ]
                .astype(float)
                .to_numpy()
            )

            axis.scatter(
                x_values,
                y_values,
                s=55,
                color=DISTANCE_COLOURS[
                    distance
                ],
                marker=DISTANCE_MARKERS[
                    distance
                ],
                edgecolor="white",
                linewidth=0.7,
                alpha=0.9,
                label=DISTANCE_LABELS[
                    distance
                ],
                zorder=3,
            )

            add_regression_line(
                axis,
                x_values,
                y_values,
                DISTANCE_COLOURS[
                    distance
                ],
                DISTANCE_LINESTYLES[
                    distance
                ],
            )

            result_row = (
                results.loc[
                    results[
                        "comparison"
                    ].eq(
                        metric_pair[
                            "comparison"
                        ]
                    )
                    & results[
                        "distance"
                    ].eq(
                        distance
                    )
                ]
                .iloc[0]
            )

            annotation_lines.append(
                (
                    f"{DISTANCE_LABELS[distance]}: "
                    f"ρ = "
                    f"{result_row['spearman_rho']:.2f}, "
                    f"q = "
                    f"{result_row['spearman_q_bh_8_tests']:.3f}"
                )
            )

        axis.axhline(
            0,
            color="0.75",
            linewidth=0.8,
            zorder=1,
        )

        axis.axvline(
            0,
            color="0.75",
            linewidth=0.8,
            zorder=1,
        )

        axis.grid(
            color="0.90",
            linewidth=0.7,
            zorder=0,
        )

        axis.set_title(
            metric_pair[
                "panel_title"
            ],
            fontsize=11,
        )

        axis.text(
            0.02,
            0.98,
            panel_letter,
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=14,
            fontweight="bold",
        )

        axis.text(
            0.98,
            0.02,
            "\n".join(
                annotation_lines
            ),
            transform=axis.transAxes,
            ha="right",
            va="bottom",
            fontsize=8.5,
            bbox={
                "facecolor": "white",
                "edgecolor": "0.85",
                "alpha": 0.9,
                "pad": 3,
            },
        )

    for axis in axes[:, 0]:
        axis.set_ylabel(
            "van den Berg background metric (z-score)"
        )

    for axis in axes[1, :]:
        axis.set_xlabel(
            "Online-image background metric (z-score)"
        )

    legend_handles, legend_labels = (
        axes[0, 0]
        .get_legend_handles_labels()
    )

    figure.legend(
        legend_handles,
        legend_labels,
        title="Simulated viewing distance",
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            0.935,
        ),
        ncol=2,
        frameon=False,
    )

    figure.suptitle(
        (
            "External comparison of online-image and "
            "calibrated background metrics"
        ),
        fontsize=14,
        y=0.99,
    )

    figure.tight_layout(
        rect=(
            0,
            0,
            1,
            0.87,
        )
    )

    figure.savefig(
        FIGURE_PNG,
        dpi=300,
        bbox_inches="tight",
    )

    figure.savefig(
        FIGURE_PDF,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )


# ============================================================
# Summary file
# ============================================================

def write_summary(
    data,
    results,
):
    """
    Save a short analysis summary for later Results writing.
    """

    strongest_index = (
        results[
            "spearman_rho"
        ]
        .abs()
        .idxmax()
    )

    strongest = results.loc[
        strongest_index
    ]

    significant_after_bh = results[
        results[
            "spearman_q_bh_8_tests"
        ] < 0.05
    ]

    summary_lines = [
        "Van background external comparison",
        "==================================",
        "",
        (
            "Overlapping species: "
            f"{data['species'].nunique()}"
        ),
        "Viewing distances: 2 cm and 30 cm",
        "Metric pairs: 4",
        "Total comparisons: 8",
        "",
        "Statistical approach:",
        (
            "Pearson and Spearman correlations were calculated "
            "using species-level z-scores."
        ),
        (
            "Benjamini-Hochberg correction was applied across "
            "the eight comparisons separately for Pearson and "
            "Spearman tests."
        ),
        "",
        "Important interpretation:",
        (
            "The paired metrics are conceptually related but not "
            "mathematically identical."
        ),
        (
            "The online-image metrics use uncalibrated photographs "
            "and CIELAB edge approximations."
        ),
        (
            "The van den Berg metrics use calibrated photographs, "
            "triggerfish vision and QCPA."
        ),
        "",
        "Largest absolute Spearman association:",
        (
            f"{strongest['comparison']} at "
            f"{DISTANCE_LABELS[strongest['distance']]}: "
            f"rho = {strongest['spearman_rho']:.3f}, "
            f"raw p = {strongest['spearman_p']:.4f}, "
            f"BH q = "
            f"{strongest['spearman_q_bh_8_tests']:.4f}"
        ),
        "",
        (
            "Spearman comparisons with BH q < 0.05: "
            f"{len(significant_after_bh)}"
        ),
    ]

    SUMMARY_FILE.write_text(
        "\n".join(
            summary_lines
        )
        + "\n",
        encoding="utf-8",
    )


# ============================================================
# Main workflow
# ============================================================

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find standardised comparison file: "
            f"{INPUT_FILE}"
        )

    data = pd.read_csv(
        INPUT_FILE
    )

    print("=" * 76)
    print("VAN BACKGROUND COMPARISON")
    print("=" * 76)

    print(
        f"\nRows: {len(data)}"
    )

    print(
        f"Species: "
        f"{data['species'].nunique()}"
    )

    print(
        "Distance counts:"
    )

    print(
        data[
            "distance"
        ]
        .value_counts()
        .to_string()
    )

    if len(data) != 18:
        raise ValueError(
            f"Expected 18 rows, but found {len(data)}."
        )

    if data["species"].nunique() != 9:
        raise ValueError(
            "Expected 9 unique species."
        )

    if data.isna().any().any():
        raise ValueError(
            "Missing values found in the input table."
        )

    required_columns = [
        "species",
        "distance",
    ]

    for metric_pair in METRIC_PAIRS:
        required_columns.extend(
            [
                metric_pair["online_z"],
                metric_pair["van_z"],
            ]
        )

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Run the eight comparisons
    # --------------------------------------------------------

    result_rows = []

    for metric_pair in METRIC_PAIRS:
        for distance in DISTANCES:

            result_rows.append(
                analyse_pair(
                    data,
                    metric_pair,
                    distance,
                )
            )

    results = pd.DataFrame(
        result_rows
    )

    # --------------------------------------------------------
    # Multiple-testing correction
    # --------------------------------------------------------

    results[
        "pearson_q_bh_8_tests"
    ] = benjamini_hochberg(
        results[
            "pearson_p"
        ]
        .to_numpy()
    )

    results[
        "spearman_q_bh_8_tests"
    ] = benjamini_hochberg(
        results[
            "spearman_p"
        ]
        .to_numpy()
    )

    # --------------------------------------------------------
    # Save results and figure
    # --------------------------------------------------------

    results.to_csv(
        RESULTS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    make_comparison_figure(
        data,
        results,
    )

    write_summary(
        data,
        results,
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print("\n" + "=" * 76)
    print("CORRELATION RESULTS")
    print("=" * 76)

    display_columns = [
        "comparison",
        "distance",
        "n_species",
        "pearson_r",
        "pearson_p",
        "pearson_q_bh_8_tests",
        "spearman_rho",
        "spearman_p",
        "spearman_q_bh_8_tests",
    ]

    print(
        results[
            display_columns
        ].to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.4f}"
            ),
        )
    )

    print("\n" + "=" * 76)
    print("FILES SAVED")
    print("=" * 76)

    print("\nCorrelation table:")
    print(RESULTS_FILE)

    print("\n2 x 2 PNG figure:")
    print(FIGURE_PNG)

    print("\n2 x 2 PDF figure:")
    print(FIGURE_PDF)

    print("\nSummary:")
    print(SUMMARY_FILE)


if __name__ == "__main__":
    main()