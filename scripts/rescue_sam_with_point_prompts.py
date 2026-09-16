from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from ultralytics import SAM
import matplotlib.pyplot as plt
from matplotlib.widgets import Button


# =========================
# Basic settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "mobile_sam.pt"

INVENTORY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "image_inventory.csv"
)

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "manual_rescue"
)

MASK_OUTPUT_DIR = OUTPUT_ROOT / "masks_original_resolution"
QC_OUTPUT_DIR = OUTPUT_ROOT / "qc"
SELECTION_CSV = OUTPUT_ROOT / "manual_rescue_selections.csv"

PREVIEW_RING_WIDTH_PX = 120

RESCUE_IDS = ['Goniobranchus_splendidus_img08', 'Phyllidia_varicosa_img02', 'Phyllidiopsis_shireenae_img02', 'Ceratosoma_brevicaudatum_img01', 'Ceratosoma_trilobatum_img07', 'Ceratosoma_trilobatum_img09', 'Chromodoris_elisabethina_img02', 'Chromodoris_elisabethina_img04', 'Chromodoris_elisabethina_img06', 'Chromodoris_elisabethina_img08', 'Chromodoris_kuiteri_img04', 'Chromodoris_kuiteri_img06', 'Chromodoris_kuiteri_img08', 'Chromodoris_kuiteri_img09', 'Dendrodoris_krusensternii_denisoni_img01', 'Dendrodoris_krusensternii_denisoni_img02', 'Dendrodoris_krusensternii_denisoni_img03', 'Dendrodoris_nigra_img01', 'Dendrodoris_nigra_img02', 'Dendrodoris_nigra_img04', 'Dendrodoris_nigra_img05', 'Dendrodoris_nigra_img06', 'Dendrodoris_nigra_img07', 'Dendrodoris_nigra_img08', 'Dendrodoris_nigra_img09', 'Dendrodoris_nigra_img10', 'Dendrodoris_tuberculosa_img01', 'Goniobranchus_collingwoodi_img01', 'Goniobranchus_collingwoodi_img02', 'Goniobranchus_collingwoodi_img06', 'Goniobranchus_daphne_img10', 'Goniobranchus_splendidus_img03', 'Goniobranchus_splendidus_img09', 'Goniobranchus_splendidus_img10', 'Goniobranchus_tasmaniensis_img05', 'Goniobranchus_tinctorius_img01', 'Goniobranchus_tinctorius_img02', 'Goniobranchus_tinctorius_img03', 'Goniobranchus_tinctorius_img05', 'Halgerda_aurantiomaculata_img09', 'Halgerda_aurantiomaculata_img10', 'Hypselodoris_obscura_img03', 'Hypselodoris_obscura_img06', 'Hypselodoris_obscura_img07', 'Hypselodoris_obscura_img08', 'Hypselodoris_tryoni_img09', 'Hypselodoris_tryoni_img10', 'Mexichromis_festiva_img09', 'Notodoris_Aegires_gardineri_img01', 'Notodoris_Aegires_gardineri_img03', 'Notodoris_Aegires_gardineri_img04', 'Notodoris_Aegires_gardineri_img05', 'Notodoris_Aegires_gardineri_img07', 'Notodoris_Aegires_gardineri_img09', 'Phyllidia_coelestis_img10', 'Phyllidia_elegans_img01', 'Phyllidia_elegans_img07', 'Phyllidia_ocellata_img06', 'Phyllidia_varicosa_img04', 'Phyllidia_varicosa_img08', 'Phyllidia_varicosa_img09', 'Phyllidiella_pustulosa_img01', 'Phyllidiella_pustulosa_img08', 'Phyllidiella_pustulosa_img09', 'Phyllidiopsis_shireenae_img01', 'Phyllidiopsis_shireenae_img06', 'Sebadoris_fragilis_img05', 'Sebadoris_fragilis_img06', 'Sebadoris_fragilis_img09']


# =========================
# Helper functions
# =========================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def resolve_project_path(path_value):
    path = Path(clean_text(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def make_project_relative_path(path):
    path = Path(path)

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_rgb_image(image_path):
    return np.array(
        Image.open(image_path).convert("RGB")
    )


def keep_largest_component(mask):
    mask_uint8 = mask.astype(np.uint8)

    num_labels, labels, stats, _ = (
        cv2.connectedComponentsWithStats(
            mask_uint8,
            connectivity=8,
        )
    )

    if num_labels <= 1:
        return mask

    largest_label = 1 + np.argmax(
        stats[1:, cv2.CC_STAT_AREA]
    )

    return labels == largest_label


def calculate_mask_perimeter(mask):
    mask_uint8 = (
        mask.astype(np.uint8)
        * 255
    )

    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if len(contours) == 0:
        return np.nan

    return float(
        sum(
            cv2.arcLength(
                contour,
                closed=True,
            )
            for contour in contours
        )
    )


def make_background_ring(mask, ring_width_px):
    mask_uint8 = mask.astype(np.uint8)

    outside_animal = 1 - mask_uint8

    distance_from_animal = cv2.distanceTransform(
        outside_animal,
        distanceType=cv2.DIST_L2,
        maskSize=5,
    )

    return (
        (distance_from_animal > 0)
        & (
            distance_from_animal
            <= ring_width_px
        )
    )


def save_mask(mask, output_path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Image.fromarray(
        mask.astype(np.uint8) * 255
    ).save(output_path)


def atomic_save_csv(df, output_path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    df.to_csv(
        temp_path,
        index=False,
    )

    temp_path.replace(output_path)


def get_prompted_mask(
    model,
    image_path,
    image_shape,
    points,
):
    prompt_points = [
        [
            [float(points[0][0]), float(points[0][1])],
            [float(points[1][0]), float(points[1][1])],
        ]
    ]

    results = model.predict(
        str(image_path),
        points=prompt_points,
        labels=[[1, 1]],
        verbose=False,
    )

    if (
        len(results) == 0
        or results[0].masks is None
        or results[0].masks.data.shape[0] == 0
    ):
        return None

    masks_tensor = results[0].masks.data

    # Prompted SAM should normally return one object mask.
    # If more than one is returned, keep the largest mask.
    candidate_masks = []

    image_height, image_width = (
        image_shape[:2]
    )

    for i in range(
        masks_tensor.shape[0]
    ):
        mask = (
            masks_tensor[i]
            .cpu()
            .numpy()
        )

        mask = (
            mask > 0.5
        ).astype(np.uint8)

        if mask.shape != (
            image_height,
            image_width,
        ):
            mask = cv2.resize(
                mask,
                (
                    image_width,
                    image_height,
                ),
                interpolation=cv2.INTER_NEAREST,
            )

        mask = keep_largest_component(
            mask.astype(bool)
        )

        candidate_masks.append(mask)

    if not candidate_masks:
        return None

    return max(
        candidate_masks,
        key=lambda m: int(np.sum(m)),
    )


def collect_two_positive_points(
    rgb_image,
    image_id,
    attempt_number,
):
    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    ax.imshow(rgb_image)
    ax.axis("off")

    ax.set_title(
        (
            f"{image_id}\n"
            f"Attempt {attempt_number}: "
            "click TWO points inside the nudibranch\n"
            "(for example one near the head and one near the tail)"
        )
    )

    plt.tight_layout()

    points = plt.ginput(
        2,
        timeout=-1,
        show_clicks=True,
    )

    plt.close(fig)

    if len(points) != 2:
        return None

    return points


def review_prompted_mask(
    rgb_image,
    mask,
    image_id,
):
    ring = make_background_ring(
        mask,
        PREVIEW_RING_WIDTH_PX,
    )

    red_overlay = rgb_image.copy()
    red_overlay[mask] = [255, 0, 0]

    green_overlay = rgb_image.copy()
    green_overlay[ring] = [0, 255, 0]

    combined = rgb_image.copy()
    combined[ring] = [0, 255, 0]
    combined[mask] = [255, 0, 0]

    fig, axes = plt.subplots(
        1,
        4,
        figsize=(16, 5),
    )

    axes[0].imshow(rgb_image)
    axes[0].set_title("Original")

    axes[1].imshow(red_overlay)
    axes[1].set_title("Prompted animal mask")

    axes[2].imshow(green_overlay)
    axes[2].set_title(
        "120 px ring preview"
    )

    axes[3].imshow(combined)
    axes[3].set_title("Mask + ring preview")

    for ax in axes:
        ax.axis("off")

    fig.suptitle(
        (
            f"{image_id}\n"
            "Accept only if the animal mask is clearly correct. "
            "The ring shown here is only a preview."
        )
    )

    plt.subplots_adjust(
        bottom=0.20,
        top=0.84,
        wspace=0.05,
    )

    decision = {"value": None}

    accept_ax = plt.axes(
        [0.20, 0.05, 0.16, 0.07]
    )
    retry_ax = plt.axes(
        [0.42, 0.05, 0.16, 0.07]
    )
    reject_ax = plt.axes(
        [0.64, 0.05, 0.16, 0.07]
    )

    accept_button = Button(
        accept_ax,
        "ACCEPT",
    )
    retry_button = Button(
        retry_ax,
        "RETRY POINTS",
    )
    reject_button = Button(
        reject_ax,
        "REJECT IMAGE",
    )

    def accept(_event):
        decision["value"] = "accepted"
        plt.close(fig)

    def retry(_event):
        decision["value"] = "retry"
        plt.close(fig)

    def reject(_event):
        decision["value"] = "rejected"
        plt.close(fig)

    accept_button.on_clicked(accept)
    retry_button.on_clicked(retry)
    reject_button.on_clicked(reject)

    plt.show()

    return decision["value"]


def save_qc_figure(
    rgb_image,
    mask,
    image_id,
    output_path,
):
    ring = make_background_ring(
        mask,
        PREVIEW_RING_WIDTH_PX,
    )

    combined = rgb_image.copy()
    combined[ring] = [0, 255, 0]
    combined[mask] = [255, 0, 0]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(12, 4),
    )

    axes[0].imshow(rgb_image)
    axes[0].set_title("Original")

    red_overlay = rgb_image.copy()
    red_overlay[mask] = [255, 0, 0]

    axes[1].imshow(red_overlay)
    axes[1].set_title("Accepted rescue mask")

    axes[2].imshow(combined)
    axes[2].set_title(
        "Mask + 120 px ring preview"
    )

    for ax in axes:
        ax.axis("off")

    fig.suptitle(image_id)
    plt.tight_layout()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        output_path,
        dpi=160,
    )

    plt.close(fig)


def load_existing_selections():
    if not SELECTION_CSV.exists():
        return pd.DataFrame(
            columns=[
                "species",
                "image_id",
                "status",
                "attempts",
                "point1_x",
                "point1_y",
                "point2_x",
                "point2_y",
                "animal_perimeter_original_px",
                "mask_path",
                "qc_path",
            ]
        )

    return pd.read_csv(
        SELECTION_CSV,
        dtype={
            "species": str,
            "image_id": str,
            "status": str,
        },
    )


# =========================
# Main workflow
# =========================

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find SAM model: {MODEL_PATH}"
        )

    if not INVENTORY_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find inventory: {INVENTORY_CSV}"
        )

    inventory = pd.read_csv(
        INVENTORY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    required_columns = [
        "species",
        "image_id",
        "original_image_path",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in inventory.columns
    ]

    if missing_columns:
        raise KeyError(
            "image_inventory.csv is missing: "
            + ", ".join(missing_columns)
        )

    inventory_by_id = (
        inventory
        .drop_duplicates(
            subset=["image_id"],
            keep="first",
        )
        .set_index("image_id")
    )

    missing_ids = [
        image_id
        for image_id in RESCUE_IDS
        if image_id
        not in inventory_by_id.index
    ]

    if missing_ids:
        print("These rescue IDs were not found:")
        for image_id in missing_ids:
            print(f"  {image_id}")

        raise KeyError(
            "Some rescue image IDs are missing "
            "from image_inventory.csv."
        )

    selections_df = (
        load_existing_selections()
    )

    already_done = set(
        selections_df[
            selections_df["status"].isin(
                ["accepted", "rejected"]
            )
        ]["image_id"].astype(str)
    )

    pending_ids = [
        image_id
        for image_id in RESCUE_IDS
        if image_id not in already_done
    ]

    print("=" * 72)
    print("MANUAL SAM RESCUE")
    print("=" * 72)
    print(
        f"Total rescue images: {len(RESCUE_IDS)}"
    )
    print(
        f"Already completed: {len(already_done)}"
    )
    print(
        f"Still pending: {len(pending_ids)}"
    )
    print()
    print(
        "For each image, click TWO points inside the animal."
    )
    print(
        "Then ACCEPT, RETRY POINTS, or REJECT IMAGE."
    )
    print(
        "Every accepted/rejected decision is saved immediately."
    )
    print()

    if not pending_ids:
        print("No rescue images left to review.")
        return

    print("Loading MobileSAM model...")
    model = SAM(str(MODEL_PATH))

    for position, image_id in enumerate(
        pending_ids,
        start=1,
    ):
        row = inventory_by_id.loc[
            image_id
        ]

        species = clean_text(
            row["species"]
        )

        image_path = resolve_project_path(
            row["original_image_path"]
        )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Cannot find image for {image_id}: "
                f"{image_path}"
            )

        rgb_image = load_rgb_image(
            image_path
        )

        print()
        print("-" * 72)
        print(
            f"[{position}/{len(pending_ids)}] "
            f"{image_id}"
        )
        print("-" * 72)

        attempt_number = 0

        while True:
            attempt_number += 1

            points = (
                collect_two_positive_points(
                    rgb_image,
                    image_id,
                    attempt_number,
                )
            )

            if points is None:
                print(
                    "Point selection was cancelled. "
                    "Try again."
                )
                continue

            print(
                "Running prompted MobileSAM..."
            )

            mask = get_prompted_mask(
                model,
                image_path,
                rgb_image.shape,
                points,
            )

            if mask is None:
                print(
                    "No prompted mask returned. "
                    "Try different points."
                )
                continue

            decision = review_prompted_mask(
                rgb_image,
                mask,
                image_id,
            )

            if decision == "retry":
                continue

            if decision is None:
                print(
                    "Review window was closed without "
                    "a decision. Try again."
                )
                continue

            if decision == "accepted":
                species_folder = (
                    species
                    .replace(" ", "_")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("=", "")
                )

                mask_path = (
                    MASK_OUTPUT_DIR
                    / species_folder
                    / (
                        f"{image_id}_"
                        "manual_rescue_mask.png"
                    )
                )

                qc_path = (
                    QC_OUTPUT_DIR
                    / species_folder
                    / (
                        f"{image_id}_"
                        "manual_rescue_qc.png"
                    )
                )

                save_mask(
                    mask,
                    mask_path,
                )

                save_qc_figure(
                    rgb_image,
                    mask,
                    image_id,
                    qc_path,
                )

                perimeter = (
                    calculate_mask_perimeter(
                        mask
                    )
                )

                new_row = {
                    "species": species,
                    "image_id": image_id,
                    "status": "accepted",
                    "attempts": attempt_number,
                    "point1_x": points[0][0],
                    "point1_y": points[0][1],
                    "point2_x": points[1][0],
                    "point2_y": points[1][1],
                    "animal_perimeter_original_px": perimeter,
                    "mask_path": (
                        make_project_relative_path(
                            mask_path
                        )
                    ),
                    "qc_path": (
                        make_project_relative_path(
                            qc_path
                        )
                    ),
                }

            else:
                new_row = {
                    "species": species,
                    "image_id": image_id,
                    "status": "rejected",
                    "attempts": attempt_number,
                    "point1_x": points[0][0],
                    "point1_y": points[0][1],
                    "point2_x": points[1][0],
                    "point2_y": points[1][1],
                    "animal_perimeter_original_px": np.nan,
                    "mask_path": "",
                    "qc_path": "",
                }

            selections_df = selections_df[
                selections_df["image_id"]
                .astype(str)
                .ne(image_id)
            ].copy()

            selections_df = pd.concat(
                [
                    selections_df,
                    pd.DataFrame(
                        [new_row]
                    ),
                ],
                ignore_index=True,
            )

            atomic_save_csv(
                selections_df,
                SELECTION_CSV,
            )

            print(
                f"Saved decision: "
                f"{new_row['status']}"
            )

            break

    print()
    print("=" * 72)
    print("MANUAL RESCUE COMPLETE")
    print("=" * 72)

    final_df = pd.read_csv(
        SELECTION_CSV,
        dtype=str,
        keep_default_na=False,
    )

    print(
        final_df["status"]
        .value_counts()
        .to_string()
    )

    print()
    print("Selections saved to:")
    print(
        make_project_relative_path(
            SELECTION_CSV
        )
    )


if __name__ == "__main__":
    main()
