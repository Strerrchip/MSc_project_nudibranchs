"""Make a 4 x 3 photo collage for species with large panel-C residuals."""

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def first_existing(*relative_paths):
    possible_paths = [
        PROJECT_ROOT / path
        for path in relative_paths
    ]

    for path in possible_paths:
        if path.exists():
            return path

    searched = "\n".join(
        f"  - {path}"
        for path in possible_paths
    )

    raise FileNotFoundError(
        f"Could not find any of these files:\n{searched}"
    )


RESIDUAL_CSV = first_existing(
    (
        "processed_data/analysis/"
        "toxicity_boldness_residuals/"
        "toxicity_boldness_collage_species.csv"
    )
)

METRICS_CSV = first_existing(
    (
        "processed_data/automated_image_analysis/"
        "visibility_metrics/"
        "sam_scaled_ring120_visibility_metrics_final.csv"
    ),
    (
        "visibility_metrics/"
        "sam_scaled_ring120_visibility_metrics_final.csv"
    ),
)

VALIDATION_CSV = first_existing(
    (
        "processed_data/automated_image_analysis/"
        "validation/"
        "sam_scaled_ring120_final_summary.csv"
    ),
    (
        "validation/"
        "sam_scaled_ring120_final_summary.csv"
    ),
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "analysis"
    / "toxicity_boldness_residuals"
)

FIGURE_PNG = (
    OUTPUT_DIR
    / "toxicity_boldness_residual_collage.png"
)

FIGURE_PDF = (
    OUTPUT_DIR
    / "toxicity_boldness_residual_collage.pdf"
)

SELECTION_CSV = (
    OUTPUT_DIR
    / "toxicity_boldness_collage_image_selection.csv"
)

CAPTION_TXT = (
    OUTPUT_DIR
    / "toxicity_boldness_residual_collage_caption.txt"
)


BOLDNESS_METRICS = [
    "animal_gray_sd",
    "animal_saturation_sd",
    "animal_edge_density",
    "animal_luminance_edge_cv",
    "animal_chromatic_edge_mean",
    "animal_chromatic_edge_cv",
]

DISPLAY_POSITIONS = [
    "Lower image-level boldness",
    "Median image-level boldness",
    "Higher image-level boldness",
]

METADATA_COLUMNS = [
    "observation_id",
    "observation_url",
    "license",
    "photographer_or_observer",
    "date_accessed",
]


def choose_three_images(group):
    group = group.sort_values(
        [
            "image_level_boldness_score",
            "image_id",
        ]
    ).copy()

    if len(group) < 3:
        raise ValueError(
            "Fewer than three images for "
            f"{group['species'].iloc[0]}."
        )

    low_index = group.index[0]
    high_index = group.index[-1]

    remaining = group.drop(
        index=[
            low_index,
            high_index,
        ]
    )

    median_value = group[
        "image_level_boldness_score"
    ].median()

    median_index = (
        remaining[
            "image_level_boldness_score"
        ]
        - median_value
    ).abs().idxmin()

    chosen = group.loc[
        [
            low_index,
            median_index,
            high_index,
        ]
    ].copy()

    chosen[
        "display_position"
    ] = DISPLAY_POSITIONS

    chosen[
        "selection_order"
    ] = [
        1,
        2,
        3,
    ]

    return chosen


def resolve_path(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    path = Path(
        text.replace("\\", "/")
    )

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def find_image(row):
    possible_images = [
        (
            "original_image_path",
            "original image",
        ),
        (
            "scaled_image_output_path",
            "scaled image fallback",
        ),
    ]

    paths_checked = []

    for column, source_type in possible_images:
        path = resolve_path(
            row.get(column, "")
        )

        if path is None:
            continue

        paths_checked.append(
            str(path)
        )

        if path.exists():
            return path, source_type

    checked_text = "\n".join(
        f"  - {path}"
        for path in paths_checked
    )

    raise FileNotFoundError(
        "No image found for "
        f"{row['species']} / {row['image_id']}.\n"
        f"Checked:\n{checked_text}"
    )


def project_relative_text(path):
    try:
        return (
            path.resolve()
            .relative_to(
                PROJECT_ROOT.resolve()
            )
            .as_posix()
        )

    except ValueError:
        return path.as_posix()


def place_image_on_canvas(
    path,
    canvas_size=(900, 650),
):
    with Image.open(path) as opened_image:
        image = (
            ImageOps
            .exif_transpose(opened_image)
            .convert("RGB")
        )

        image.thumbnail(
            canvas_size,
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new(
            "RGB",
            canvas_size,
            color=(245, 245, 245),
        )

        x_position = (
            canvas_size[0] - image.width
        ) // 2

        y_position = (
            canvas_size[1] - image.height
        ) // 2

        canvas.paste(
            image,
            (
                x_position,
                y_position,
            ),
        )

    return canvas


def value_is_true(value):
    if isinstance(
        value,
        (
            bool,
            np.bool_,
        ),
    ):
        return bool(value)

    return (
        str(value)
        .strip()
        .lower()
        in {
            "true",
            "1",
            "yes",
        }
    )


def main():
    residual_species = pd.read_csv(
        RESIDUAL_CSV
    ).sort_values(
        "residual_rank"
    )

    required_residual_columns = [
        "species",
        "residual_rank",
        "toxicity_strength_0_1",
        "mean_normalised_boldness",
        "internally_studentised_residual",
        (
            "formal_outlier_"
            "abs_studentised_residual_gt_2"
        ),
    ]

    missing_columns = [
        column
        for column in required_residual_columns
        if column not in residual_species.columns
    ]

    if missing_columns:
        raise KeyError(
            "Residual CSV is missing: "
            + ", ".join(missing_columns)
        )

    if len(residual_species) != 4:
        raise ValueError(
            "Expected four residual species, "
            f"but found {len(residual_species)}."
        )

    image_metrics = pd.read_csv(
        METRICS_CSV
    )

    required_metric_columns = [
        "species",
        "image_id",
        *BOLDNESS_METRICS,
    ]

    missing_columns = [
        column
        for column in required_metric_columns
        if column not in image_metrics.columns
    ]

    if missing_columns:
        raise KeyError(
            "Metrics CSV is missing: "
            + ", ".join(missing_columns)
        )

    if len(image_metrics) != 295:
        raise ValueError(
            "Expected 295 image rows, "
            f"but found {len(image_metrics)}."
        )

    if image_metrics[
        [
            "species",
            "image_id",
        ]
    ].duplicated().any():
        raise ValueError(
            "Duplicate species/image_id rows "
            "in metrics CSV."
        )

    if image_metrics[
        required_metric_columns
    ].isna().any().any():
        raise ValueError(
            "Missing image-level metric values."
        )

    metric_values = image_metrics[
        BOLDNESS_METRICS
    ].apply(
        pd.to_numeric,
        errors="raise",
    )

    metric_standard_deviations = (
        metric_values.std(
            axis=0,
            ddof=1,
        )
    )

    if (
        metric_standard_deviations <= 0
    ).any():
        raise ValueError(
            "At least one boldness metric "
            "has zero variance."
        )

    metric_zscores = (
        metric_values
        - metric_values.mean(axis=0)
    ) / metric_standard_deviations

    image_scores = image_metrics[
        [
            "species",
            "image_id",
        ]
    ].copy()

    image_scores[
        "image_level_boldness_score"
    ] = metric_zscores.mean(
        axis=1
    )

    validation = pd.read_csv(
        VALIDATION_CSV
    )

    required_path_columns = [
        "species",
        "image_id",
        "original_image_path",
        "scaled_image_output_path",
    ]

    missing_columns = [
        column
        for column in required_path_columns
        if column not in validation.columns
    ]

    if missing_columns:
        raise KeyError(
            "Validation CSV is missing: "
            + ", ".join(missing_columns)
        )

    optional_columns = [
        column
        for column in [
            "mask_source",
            "image_slot",
        ]
        if column in validation.columns
    ]

    image_data = image_scores.merge(
        validation[
            [
                *required_path_columns,
                *optional_columns,
            ]
        ],
        on=[
            "species",
            "image_id",
        ],
        how="left",
        validate="one_to_one",
    )

    if image_data[
        "original_image_path"
    ].isna().any():
        raise ValueError(
            "Some metric rows have no "
            "validation image path."
        )

    selected_groups = []

    for residual_row in residual_species.itertuples(
        index=False
    ):
        species_images = image_data.loc[
            image_data["species"]
            == residual_row.species
        ]

        if species_images.empty:
            raise ValueError(
                "No images found for "
                f"{residual_row.species}."
            )

        chosen_images = choose_three_images(
            species_images
        )

        for column in required_residual_columns[1:]:
            chosen_images[column] = getattr(
                residual_row,
                column,
            )

        selected_groups.append(
            chosen_images
        )

    selection = pd.concat(
        selected_groups,
        ignore_index=True,
    )

    selection = (
        selection
        .sort_values(
            [
                "residual_rank",
                "selection_order",
            ]
        )
        .reset_index(drop=True)
    )

    # Add source metadata when the inventory exists.
    inventory_path = (
        PROJECT_ROOT
        / "processed_data"
        / "image_inventory.csv"
    )

    if inventory_path.exists():
        inventory = pd.read_csv(
            inventory_path,
            dtype=str,
            keep_default_na=False,
        )

        available_metadata = [
            column
            for column in METADATA_COLUMNS
            if column in inventory.columns
        ]

        if inventory[
            [
                "species",
                "image_id",
            ]
        ].duplicated().any():
            raise ValueError(
                "Duplicate species/image_id rows "
                "in image inventory."
            )

        selection = selection.merge(
            inventory[
                [
                    "species",
                    "image_id",
                    *available_metadata,
                ]
            ],
            on=[
                "species",
                "image_id",
            ],
            how="left",
            validate="one_to_one",
        )

    for column in METADATA_COLUMNS:
        if column not in selection.columns:
            selection[column] = ""

        selection[column] = (
            selection[column]
            .fillna("")
        )

    selection[
        "image_path_used"
    ] = ""

    selection[
        "image_source_used"
    ] = ""

    figure, axes = plt.subplots(
        4,
        3,
        figsize=(15, 12),
    )

    panel_letters = [
        "A",
        "B",
        "C",
        "D",
    ]

    grouped_selection = selection.groupby(
        "residual_rank",
        sort=True,
    )

    for row_number, (
        residual_rank,
        species_group,
    ) in enumerate(grouped_selection):
        species_group = (
            species_group
            .sort_values("selection_order")
        )

        first_row = species_group.iloc[0]

        species_label = textwrap.fill(
            str(first_row["species"]),
            width=27,
        )

        residual_value = float(
            first_row[
                "internally_studentised_residual"
            ]
        )

        formal_outlier = value_is_true(
            first_row[
                "formal_outlier_"
                "abs_studentised_residual_gt_2"
            ]
        )

        if formal_outlier:
            residual_status = "formal outlier"
        else:
            residual_status = "large residual"

        for (
            column_number,
            (
                selection_index,
                image_row,
            ),
        ) in enumerate(
            species_group.iterrows()
        ):
            image_path, source_type = find_image(
                image_row
            )

            selection.loc[
                selection_index,
                "image_path_used",
            ] = project_relative_text(
                image_path
            )

            selection.loc[
                selection_index,
                "image_source_used",
            ] = source_type

            display_image = place_image_on_canvas(
                image_path
            )

            current_axis = axes[
                row_number,
                column_number,
            ]

            current_axis.imshow(
                display_image
            )

            current_axis.axis(
                "off"
            )

            current_axis.text(
                0.5,
                -0.035,
                str(image_row["image_id"]),
                transform=current_axis.transAxes,
                ha="center",
                va="top",
                fontsize=8,
            )

            if row_number == 0:
                current_axis.set_title(
                    DISPLAY_POSITIONS[
                        column_number
                    ],
                    fontsize=11,
                    pad=9,
                )

        axes[
            row_number,
            0,
        ].text(
            -0.06,
            0.5,
            (
                f"{panel_letters[row_number]}  "
                f"{species_label}\n"
                f"studentised residual = "
                f"{residual_value:+.2f}\n"
                f"({residual_status})"
            ),
            transform=axes[
                row_number,
                0,
            ].transAxes,
            ha="right",
            va="center",
            fontsize=10,
        )

    figure.suptitle(
        (
            "Images from species with the largest "
            "toxicity-boldness residuals"
        ),
        fontsize=17,
        y=0.985,
    )

    figure.subplots_adjust(
        left=0.29,
        right=0.99,
        top=0.92,
        bottom=0.05,
        wspace=0.025,
        hspace=0.24,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
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

    attribution_missing = selection[
        [
            "observation_url",
            "license",
            "photographer_or_observer",
        ]
    ].apply(
        lambda column: (
            column
            .astype(str)
            .str.strip()
            .eq("")
        )
    ).any(axis=1)

    selection[
        "attribution_complete"
    ] = ~attribution_missing

    selection.to_csv(
        SELECTION_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    caption = (
        "Examples from the four species with the largest "
        "absolute internally studentised residuals in the "
        "toxicity-boldness relationship. Rows show species "
        "in descending residual rank. Columns show images "
        "with lower, median and higher image-level boldness "
        "within each species, selected reproducibly from the "
        "six animal-only metrics. The scatter-plot analysis "
        "used species means; these images illustrate within-"
        "species photographic variation. Dendrodoris nigra "
        "was the only formal residual outlier under the "
        "absolute residual threshold of 2. Photo attribution "
        "and licence information are listed in the associated "
        "image-selection table."
    )

    CAPTION_TXT.write_text(
        caption + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print(
        "TOXICITY-BOLDNESS RESIDUAL COLLAGE COMPLETE"
    )
    print("=" * 72)
    print(
        "Selected species: "
        f"{selection['species'].nunique()}"
    )
    print(
        f"Selected images: {len(selection)}"
    )
    print(
        "Rows with complete attribution: "
        f"{int(selection['attribution_complete'].sum())}/12"
    )

    if attribution_missing.any():
        print(
            "WARNING: Complete observation URL, "
            "photographer and licence information "
            "before submitting the figure."
        )

    print(
        f"Saved figure: {FIGURE_PNG}"
    )
    print(
        f"Saved image selection: {SELECTION_CSV}"
    )


if __name__ == "__main__":
    main()