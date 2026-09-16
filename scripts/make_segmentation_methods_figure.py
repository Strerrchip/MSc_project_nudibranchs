from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


# =========================
# Paths and settings
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUMMARY_FILE = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "sam_scaled_ring120_final_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "methods_figures"
)

# This is an automatic-QC example that was downscaled.
# It can be changed later if the photograph is not visually suitable.
IMAGE_ID = "Aphelodoris_varia_img03"

PNG_FILE = OUTPUT_DIR / "segmentation_methods_2x2.png"
PDF_FILE = OUTPUT_DIR / "segmentation_methods_2x2.pdf"
CAPTION_FILE = OUTPUT_DIR / "segmentation_methods_2x2_caption.txt"
METADATA_FILE = OUTPUT_DIR / "segmentation_methods_2x2_metadata.csv"


# =========================
# Helper functions
# =========================

def resolve_project_path(path_value):
    """Resolve a project-relative or absolute path."""

    path = Path(str(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def load_rgb_image(path):
    """Load an RGB image."""

    return np.array(
        Image.open(path).convert("RGB")
    )


def load_binary_mask(path):
    """Load a saved mask as a Boolean array."""

    mask = np.array(
        Image.open(path).convert("L")
    )

    return mask > 0


def add_colour_overlay(
    rgb_image,
    mask,
    colour,
    alpha=0.55,
):
    """Add a transparent colour to a selected image region."""

    overlay = rgb_image.astype(float).copy()
    colour = np.asarray(colour, dtype=float)

    overlay[mask] = (
        (1 - alpha) * overlay[mask]
        + alpha * colour
    )

    return np.clip(
        overlay,
        0,
        255,
    ).astype(np.uint8)


def add_panel_label(ax, label):
    """Add a panel letter to the upper-left corner."""

    ax.text(
        0.025,
        0.965,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=18,
        fontweight="bold",
        color="black",
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.80,
            "pad": 2,
        },
    )


# =========================
# Load the selected image
# =========================

if not SUMMARY_FILE.exists():
    raise FileNotFoundError(
        f"Cannot find the final summary file:\n{SUMMARY_FILE}"
    )

summary = pd.read_csv(SUMMARY_FILE)

matching_rows = summary.loc[
    summary["image_id"].astype(str) == IMAGE_ID
].copy()

if len(matching_rows) == 0:
    available_examples = (
        summary["image_id"]
        .astype(str)
        .head(10)
        .tolist()
    )

    raise ValueError(
        f"IMAGE_ID '{IMAGE_ID}' was not found.\n"
        f"Examples of available IDs:\n{available_examples}"
    )

if len(matching_rows) > 1:
    raise ValueError(
        f"More than one row was found for {IMAGE_ID}."
    )

row = matching_rows.iloc[0]

scaled_image_path = resolve_project_path(
    row["scaled_image_output_path"]
)

animal_mask_path = resolve_project_path(
    row["mask_output_path"]
)

background_ring_path = resolve_project_path(
    row["background_ring_output_path"]
)

for required_path in [
    scaled_image_path,
    animal_mask_path,
    background_ring_path,
]:
    if not required_path.exists():
        raise FileNotFoundError(
            f"Cannot find required image file:\n{required_path}"
        )

rgb_image = load_rgb_image(
    scaled_image_path
)

animal_mask = load_binary_mask(
    animal_mask_path
)

background_ring = load_binary_mask(
    background_ring_path
)

expected_shape = rgb_image.shape[:2]

if animal_mask.shape != expected_shape:
    raise ValueError(
        "The animal mask dimensions do not match "
        "the scaled image dimensions."
    )

if background_ring.shape != expected_shape:
    raise ValueError(
        "The background-ring dimensions do not match "
        "the scaled image dimensions."
    )


# =========================
# Create overlays
# =========================

animal_overlay = add_colour_overlay(
    rgb_image,
    animal_mask,
    colour=[230, 40, 40],
    alpha=0.58,
)

ring_overlay = add_colour_overlay(
    rgb_image,
    background_ring,
    colour=[40, 190, 80],
    alpha=0.58,
)

combined_overlay = add_colour_overlay(
    rgb_image,
    background_ring,
    colour=[40, 190, 80],
    alpha=0.58,
)

combined_overlay = add_colour_overlay(
    combined_overlay,
    animal_mask,
    colour=[230, 40, 40],
    alpha=0.58,
)


# =========================
# Make the 2 x 2 figure
# =========================

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
    }
)

fig, axes = plt.subplots(
    2,
    2,
    figsize=(10, 8),
)

panels = [
    (
        rgb_image,
        "Scaled image",
        "A",
    ),
    (
        animal_overlay,
        "Animal mask",
        "B",
    ),
    (
        ring_overlay,
        "120-pixel background ring",
        "C",
    ),
    (
        combined_overlay,
        "Animal and background regions",
        "D",
    ),
]

for ax, (panel_image, title, label) in zip(
    axes.flat,
    panels,
):
    ax.imshow(panel_image)
    ax.set_title(title, pad=8)
    ax.axis("off")
    add_panel_label(ax, label)

legend_handles = [
    Patch(
        facecolor=(230 / 255, 40 / 255, 40 / 255),
        label="Animal region",
    ),
    Patch(
        facecolor=(40 / 255, 190 / 255, 80 / 255),
        label="Background ring",
    ),
]

axes[1, 1].legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.02),
    ncol=2,
    frameon=True,
    fontsize=10,
)

fig.suptitle(
    "Image segmentation and background sampling",
    fontsize=17,
    y=0.985,
)

fig.subplots_adjust(
    left=0.02,
    right=0.98,
    bottom=0.03,
    top=0.93,
    wspace=0.06,
    hspace=0.15,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

fig.savefig(
    PNG_FILE,
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
)

fig.savefig(
    PDF_FILE,
    bbox_inches="tight",
    facecolor="white",
)

plt.close(fig)


# =========================
# Save figure information
# =========================

metadata_columns = [
    "species",
    "image_id",
    "mask_source",
    "animal_perimeter_before_scaling",
    "target_animal_perimeter",
    "scale_factor",
    "animal_perimeter_after_scaling",
    "ring_width_px",
    "animal_area_pixels",
    "background_ring_area_pixels",
]

row[metadata_columns].to_frame().T.to_csv(
    METADATA_FILE,
    index=False,
)

species = str(row["species"])
mask_source = str(row["mask_source"])
perimeter_before = float(
    row["animal_perimeter_before_scaling"]
)
target_perimeter = float(
    row["target_animal_perimeter"]
)
scale_factor = float(
    row["scale_factor"]
)
perimeter_after = float(
    row["animal_perimeter_after_scaling"]
)
ring_width = int(
    row["ring_width_px"]
)

caption = (
    "Example of the image segmentation and background-sampling "
    "workflow. (A) Scaled online image; (B) final animal mask "
    "shown in red; (C) the surrounding 120-pixel background ring "
    "shown in green; and (D) the two analysis regions combined. "
    f"The example shows {species} ({IMAGE_ID}), with the mask "
    f"obtained from {mask_source}. The animal perimeter before "
    f"scaling was {perimeter_before:.2f} pixels, compared with the "
    f"median target perimeter of {target_perimeter:.2f} pixels. "
    f"The applied scale factor was {scale_factor:.3f}, giving a "
    f"final perimeter of {perimeter_after:.2f} pixels. Scale factors "
    "were capped at 1, so images below the target size were not "
    f"enlarged. Background pixels were sampled within {ring_width} "
    "pixels of the animal mask."
)

CAPTION_FILE.write_text(
    caption,
    encoding="utf-8",
)

print("Completed segmentation methods figure.")
print(f"Selected image: {IMAGE_ID}")
print(f"Species: {species}")
print(f"Mask source: {mask_source}")
print(f"PNG: {PNG_FILE}")
print(f"PDF: {PDF_FILE}")
print(f"Caption: {CAPTION_FILE}")
print(f"Metadata: {METADATA_FILE}")