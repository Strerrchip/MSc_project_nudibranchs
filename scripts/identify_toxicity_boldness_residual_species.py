"""Identify species with the largest residuals in toxicity versus boldness."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "mean_normalised_scores_vs_defence"
    / "mean_normalised_scores_vs_defence_table.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "toxicity_boldness_residuals"
)

ALL_RESIDUALS_CSV = (
    OUTPUT_DIR
    / "toxicity_boldness_all_species_residuals.csv"
)

COLLAGE_SELECTION_CSV = (
    OUTPUT_DIR
    / "toxicity_boldness_collage_species.csv"
)

SUMMARY_TXT = (
    OUTPUT_DIR
    / "toxicity_boldness_residual_summary.txt"
)

N_COLLAGE_SPECIES = 4


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            "Run plot_mean_normalised_scores_vs_defence.py "
            "first. The required table was not found:\n"
            f"{INPUT_CSV}"
        )

    data = pd.read_csv(INPUT_CSV)

    required_columns = [
        "species",
        "n_images",
        "toxicity_strength_0_1",
        "mean_normalised_boldness",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise KeyError(
            "Missing residual-analysis columns: "
            + ", ".join(missing_columns)
        )

    if data["species"].duplicated().any():
        raise ValueError(
            "Duplicate species rows were found."
        )

    analysis = (
        data[required_columns]
        .dropna()
        .copy()
        .reset_index(drop=True)
    )

    if len(analysis) != 27:
        raise ValueError(
            "Expected 27 species with resolved "
            f"toxicity, but found {len(analysis)}."
        )

    x = analysis[
        "toxicity_strength_0_1"
    ].to_numpy(dtype=float)

    y = analysis[
        "mean_normalised_boldness"
    ].to_numpy(dtype=float)

    # Design matrix for an OLS model with an intercept.
    design_matrix = np.column_stack(
        [
            np.ones(len(x)),
            x,
        ]
    )

    coefficients = np.linalg.lstsq(
        design_matrix,
        y,
        rcond=None,
    )[0]

    intercept = float(
        coefficients[0]
    )

    slope = float(
        coefficients[1]
    )

    predicted = (
        design_matrix
        @ coefficients
    )

    residual = (
        y - predicted
    )

    number_observations = len(y)
    number_parameters = design_matrix.shape[1]

    residual_degrees_freedom = (
        number_observations
        - number_parameters
    )

    residual_mse = float(
        np.sum(residual ** 2)
        / residual_degrees_freedom
    )

    hat_matrix = (
        design_matrix
        @ np.linalg.inv(
            design_matrix.T
            @ design_matrix
        )
        @ design_matrix.T
    )

    leverage = np.diag(
        hat_matrix
    )

    internally_studentised_residual = (
        residual
        / np.sqrt(
            residual_mse
            * (1.0 - leverage)
        )
    )

    cooks_distance = (
        (
            residual ** 2
            / (
                number_parameters
                * residual_mse
            )
        )
        * (
            leverage
            / (1.0 - leverage) ** 2
        )
    )

    analysis[
        "predicted_mean_normalised_boldness"
    ] = predicted

    analysis[
        "residual"
    ] = residual

    analysis[
        "absolute_residual"
    ] = np.abs(residual)

    analysis[
        "leverage"
    ] = leverage

    analysis[
        "internally_studentised_residual"
    ] = internally_studentised_residual

    analysis[
        "absolute_studentised_residual"
    ] = np.abs(
        internally_studentised_residual
    )

    analysis[
        "cooks_distance"
    ] = cooks_distance

    analysis[
        "formal_outlier_abs_studentised_residual_gt_2"
    ] = (
        analysis[
            "absolute_studentised_residual"
        ] > 2.0
    )

    analysis = (
        analysis
        .sort_values(
            [
                "absolute_studentised_residual",
                "cooks_distance",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    analysis[
        "residual_rank"
    ] = np.arange(
        1,
        len(analysis) + 1,
    )

    analysis[
        "selected_for_collage"
    ] = (
        analysis["residual_rank"]
        <= N_COLLAGE_SPECIES
    )

    selection = analysis.loc[
        analysis["selected_for_collage"]
    ].copy()

    selection[
        "selection_reason"
    ] = np.where(
        selection[
            "formal_outlier_abs_studentised_residual_gt_2"
        ],
        (
            "Formal residual outlier: absolute internally "
            "studentised residual > 2"
        ),
        (
            "Among the four largest absolute internally "
            "studentised residuals"
        ),
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    analysis.to_csv(
        ALL_RESIDUALS_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    selection.to_csv(
        COLLAGE_SELECTION_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    formal_outliers = analysis.loc[
        analysis[
            "formal_outlier_abs_studentised_residual_gt_2"
        ],
        [
            "species",
            "internally_studentised_residual",
        ],
    ]

    summary_lines = [
        "Toxicity-boldness residual audit",
        "=================================",
        "",
        (
            "Species included in panel C: "
            f"{number_observations}"
        ),
        (
            "OLS equation: boldness = "
            f"{intercept:.6f} + "
            f"{slope:.6f} * toxicity"
        ),
        (
            "Formal residual rule: absolute internally "
            "studentised residual > 2."
        ),
        (
            "Number of formal residual outliers: "
            f"{len(formal_outliers)}"
        ),
        "",
        "Formal residual outliers:",
    ]

    if formal_outliers.empty:
        summary_lines.append(
            "- none"
        )

    else:
        for row in formal_outliers.itertuples(
            index=False
        ):
            summary_lines.append(
                f"- {row.species}: "
                "studentised residual = "
                f"{row.internally_studentised_residual:.3f}"
            )

    summary_lines.extend(
        [
            "",
            (
                "Four species selected "
                "for the image collage:"
            ),
        ]
    )

    for row in selection.itertuples(
        index=False
    ):
        summary_lines.append(
            f"- rank {row.residual_rank}: "
            f"{row.species}; "
            f"toxicity = "
            f"{row.toxicity_strength_0_1:.3f}; "
            f"boldness = "
            f"{row.mean_normalised_boldness:.3f}; "
            f"studentised residual = "
            f"{row.internally_studentised_residual:.3f}; "
            f"Cook's distance = "
            f"{row.cooks_distance:.3f}"
        )

    SUMMARY_TXT.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print(
        "TOXICITY-BOLDNESS RESIDUAL AUDIT COMPLETE"
    )
    print("=" * 72)

    print(
        "\n".join(summary_lines[3:])
    )

    print(
        f"\nSaved all residuals: "
        f"{ALL_RESIDUALS_CSV}"
    )

    print(
        f"Saved collage selection: "
        f"{COLLAGE_SELECTION_CSV}"
    )


if __name__ == "__main__":
    main()