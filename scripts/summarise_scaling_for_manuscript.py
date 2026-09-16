"""Summarise final image scaling for the manuscript."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_input_file() -> Path:
    possible_files = [
        (
            PROJECT_ROOT
            / "processed_data"
            / "automated_image_analysis"
            / "validation"
            / "sam_scaled_ring120_final_summary.csv"
        ),
        (
            PROJECT_ROOT
            / "validation"
            / "sam_scaled_ring120_final_summary.csv"
        ),
    ]

    for path in possible_files:
        if path.exists():
            return path

    searched = "\n".join(str(path) for path in possible_files)

    raise FileNotFoundError(
        "Could not find the final scaling summary CSV.\n"
        "The script searched:\n"
        f"{searched}"
    )


INPUT_CSV = find_input_file()

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "scaling_manuscript_summary"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "scaling_manuscript_statistics.csv"
)

SUMMARY_TXT = (
    OUTPUT_DIR
    / "scaling_manuscript_summary.txt"
)

BELOW_TARGET_CSV = (
    OUTPUT_DIR
    / "images_below_scaling_target.csv"
)


def main() -> None:
    data = pd.read_csv(INPUT_CSV)

    required_columns = [
        "species",
        "image_id",
        "animal_perimeter_before_scaling",
        "target_animal_perimeter",
        "scale_factor",
        "animal_perimeter_after_scaling",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise KeyError(
            "The input CSV is missing these columns: "
            + ", ".join(missing_columns)
        )

    numeric_columns = [
        "animal_perimeter_before_scaling",
        "target_animal_perimeter",
        "scale_factor",
        "animal_perimeter_after_scaling",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="raise",
        )

    targets = data[
        "target_animal_perimeter"
    ].unique()

    if len(targets) != 1:
        raise ValueError(
            "Expected one common scaling target, "
            f"but found {len(targets)}."
        )

    target = float(targets[0])
    tolerance = 1e-9

    below_target = data.loc[
        data["animal_perimeter_before_scaling"]
        < target - tolerance
    ].copy()

    equal_to_target = data.loc[
        np.isclose(
            data["animal_perimeter_before_scaling"],
            target,
            rtol=0,
            atol=tolerance,
        )
    ].copy()

    above_target = data.loc[
        data["animal_perimeter_before_scaling"]
        > target + tolerance
    ].copy()

    if (
        data["scale_factor"]
        > 1.0 + tolerance
    ).any():
        raise ValueError(
            "Upscaling was detected. "
            "At least one scale factor was greater than 1."
        )

    if not np.allclose(
        below_target["scale_factor"],
        1.0,
    ):
        raise ValueError(
            "At least one below-target image "
            "was unexpectedly rescaled."
        )

    if (
        above_target["scale_factor"]
        >= 1.0
    ).any():
        raise ValueError(
            "At least one above-target image "
            "was not downscaled."
        )

    below_target[
        "perimeter_as_percent_of_target"
    ] = (
        100
        * below_target[
            "animal_perimeter_before_scaling"
        ]
        / target
    )

    minimum_perimeter = below_target[
        "animal_perimeter_before_scaling"
    ].min()

    maximum_perimeter = below_target[
        "animal_perimeter_before_scaling"
    ].max()

    minimum_percentage = below_target[
        "perimeter_as_percent_of_target"
    ].min()

    maximum_percentage = below_target[
        "perimeter_as_percent_of_target"
    ].max()

    unchanged_images = (
        len(below_target)
        + len(equal_to_target)
    )

    summary_rows = [
        {
            "statistic": "final_images",
            "value": len(data),
            "unit": "images",
        },
        {
            "statistic": "species",
            "value": data["species"].nunique(),
            "unit": "species",
        },
        {
            "statistic": "target_perimeter_exact",
            "value": target,
            "unit": "pixels",
        },
        {
            "statistic": "target_perimeter_reported",
            "value": round(target),
            "unit": "pixels",
        },
        {
            "statistic": "images_above_target_downscaled",
            "value": len(above_target),
            "unit": "images",
        },
        {
            "statistic": "images_at_or_below_target_unchanged",
            "value": unchanged_images,
            "unit": "images",
        },
        {
            "statistic": "images_strictly_below_target",
            "value": len(below_target),
            "unit": "images",
        },
        {
            "statistic": "below_target_minimum_perimeter",
            "value": minimum_perimeter,
            "unit": "pixels",
        },
        {
            "statistic": "below_target_maximum_perimeter",
            "value": maximum_perimeter,
            "unit": "pixels",
        },
        {
            "statistic": "below_target_minimum_percent",
            "value": minimum_percentage,
            "unit": "percent of target",
        },
        {
            "statistic": "below_target_maximum_percent",
            "value": maximum_percentage,
            "unit": "percent of target",
        },
        {
            "statistic": "maximum_scale_factor",
            "value": data["scale_factor"].max(),
            "unit": "ratio",
        },
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(
        summary_rows
    ).to_csv(
        SUMMARY_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    below_target[
        [
            "species",
            "image_id",
            "animal_perimeter_before_scaling",
            "target_animal_perimeter",
            "scale_factor",
            "perimeter_as_percent_of_target",
        ]
    ].sort_values(
        "animal_perimeter_before_scaling"
    ).to_csv(
        BELOW_TARGET_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    summary_text = (
        "Final scaling summary for the manuscript\n"
        "==========================================\n\n"
        f"The rounded median scaling target was "
        f"{round(target):,} pixels.\n"
        f"Of {len(data)} retained images, "
        f"{len(above_target)} animals above the target "
        f"were downscaled and {unchanged_images} images "
        f"at or below the target were retained at their "
        f"original resolution.\n"
        f"The {len(below_target)} strictly below-target "
        f"animal perimeters ranged from "
        f"{minimum_perimeter:,.0f} to "
        f"{maximum_perimeter:,.0f} pixels "
        f"({minimum_percentage:.1f}-"
        f"{maximum_percentage:.1f}% of the target).\n"
        "No image was enlarged "
        f"(maximum scale factor = "
        f"{data['scale_factor'].max():.3f}).\n"
    )

    SUMMARY_TXT.write_text(
        summary_text,
        encoding="utf-8",
    )

    print("=" * 72)
    print("SCALING MANUSCRIPT SUMMARY COMPLETE")
    print("=" * 72)
    print(summary_text)
    print(f"Saved statistics: {SUMMARY_CSV}")
    print(f"Saved below-target table: {BELOW_TARGET_CSV}")


if __name__ == "__main__":
    main()