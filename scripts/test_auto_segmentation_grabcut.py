from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from skimage import measure, morphology


PROJECT_DIR = Path(__file__).resolve().parents[1]

test_images = [
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img03.jpg",
]

base_output_dir = PROJECT_DIR / "processed_data/automated_image_analysis"
mask_dir = base_output_dir / "masks"
ring_dir = base_output_dir / "background_rings"
qc_dir = base_output_dir / "qc_figures"

mask_dir.mkdir(parents=True, exist_ok=True)
ring_dir.mkdir(parents=True, exist_ok=True)
qc_dir.mkdir(parents=True, exist_ok=True)

# Current baseline background ring width.
RING_WIDTH = 80

# Large images are resized during GrabCut to make the script faster.
MAX_PROCESS_WIDTH = 1200

# This refinement is useful for the current pale/white pilot species.
# It removes some dark or highly saturated background pixels from the animal mask.
USE_PALE_ANIMAL_REFINEMENT = True


def resize_for_processing(image_rgb, max_width):
    h, w = image_rgb.shape[:2]

    if w <= max_width:
        return image_rgb, 1.0

    scale = max_width / w
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(
        image_rgb,
        (new_w, new_h),
        interpolation=cv2.INTER_AREA
    )

    return resized, scale


def resize_mask_to_original(mask, original_shape):
    original_h, original_w = original_shape[:2]

    resized_mask = cv2.resize(
        mask.astype(np.uint8),
        (original_w, original_h),
        interpolation=cv2.INTER_NEAREST
    )

    return resized_mask.astype(bool)


def keep_likely_main_object(binary_mask):
    """
    Keep the most likely main animal object from a binary mask.
    """
    binary_mask = binary_mask.astype(bool)

    min_size = max(100, int(binary_mask.size * 0.002))
    binary_mask = morphology.remove_small_objects(binary_mask, min_size=min_size)

    binary_mask = morphology.remove_small_holes(
        binary_mask,
        area_threshold=max(100, int(binary_mask.size * 0.001))
    )

    binary_mask = morphology.binary_closing(binary_mask, morphology.disk(7))
    binary_mask = morphology.binary_opening(binary_mask, morphology.disk(4))

    labels = measure.label(binary_mask)

    if labels.max() == 0:
        return binary_mask

    h, w = binary_mask.shape
    image_area = h * w

    best_label = None
    best_score = -999999

    for region in measure.regionprops(labels):
        area_fraction = region.area / image_area

        if area_fraction < 0.002 or area_fraction > 0.70:
            continue

        cy, cx = region.centroid

        centre_distance = np.sqrt(
            ((cx - w / 2) / (w / 2)) ** 2
            + ((cy - h / 2) / (h / 2)) ** 2
        )

        minr, minc, maxr, maxc = region.bbox
        touches_border = minr == 0 or minc == 0 or maxr == h or maxc == w

        score = region.area
        score -= centre_distance * image_area * 0.25

        if touches_border:
            score -= image_area * 0.30

        if score > best_score:
            best_score = score
            best_label = region.label

    if best_label is None:
        regions = measure.regionprops(labels)
        largest_region = max(regions, key=lambda r: r.area)
        best_label = largest_region.label

    final_mask = labels == best_label

    final_mask = morphology.remove_small_holes(
        final_mask,
        area_threshold=max(100, int(final_mask.size * 0.002))
    )

    final_mask = morphology.binary_closing(final_mask, morphology.disk(5))

    return final_mask


def refine_pale_animal_mask(image_rgb, animal_mask):
    """
    Experimental refinement for pale/white nudibranchs.

    This step keeps pixels that are bright enough or not extremely saturated.
    It helps remove some red algae or dark background from the animal mask.
    """
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    brightness = hsv[:, :, 2]

    if animal_mask.sum() == 0:
        return animal_mask

    animal_brightness = brightness[animal_mask]
    animal_saturation = saturation[animal_mask]

    brightness_cutoff = np.percentile(animal_brightness, 25)
    saturation_cutoff = np.percentile(animal_saturation, 85)

    refined_mask = animal_mask & (
        (brightness >= brightness_cutoff) | (saturation <= saturation_cutoff)
    )

    refined_mask = morphology.remove_small_objects(
        refined_mask,
        min_size=max(100, int(refined_mask.size * 0.001))
    )

    refined_mask = morphology.remove_small_holes(
        refined_mask,
        area_threshold=max(100, int(refined_mask.size * 0.002))
    )

    refined_mask = morphology.binary_closing(refined_mask, morphology.disk(6))
    refined_mask = morphology.binary_opening(refined_mask, morphology.disk(3))

    refined_mask = keep_likely_main_object(refined_mask)

    return refined_mask


def create_background_ring(animal_mask, ring_width):
    """
    Create a surrounding background ring.

    background_ring = dilated_animal_mask - animal_mask
    """
    dilated_mask = morphology.binary_dilation(
        animal_mask,
        morphology.disk(ring_width)
    )

    background_ring = dilated_mask & (~animal_mask)

    return background_ring


def make_overlay(image_rgb, mask, colour):
    """
    Add a transparent colour overlay to show a mask.
    """
    overlay = image_rgb.copy().astype(float)
    colour = np.array(colour)

    overlay[mask] = overlay[mask] * 0.35 + colour * 0.65

    return np.clip(overlay, 0, 255).astype(np.uint8)


def process_image(image_path):
    species = image_path.parent.name
    image_id = image_path.stem

    print(f"Processing: {species} / {image_id}")
    print(f"  background ring width: {RING_WIDTH} pixels")
    print(f"  pale animal refinement: {USE_PALE_ANIMAL_REFINEMENT}")

    original_rgb = np.array(Image.open(image_path).convert("RGB"))
    process_rgb, scale = resize_for_processing(original_rgb, MAX_PROCESS_WIDTH)

    print(f"  processing scale: {scale:.3f}")

    process_bgr = cv2.cvtColor(process_rgb, cv2.COLOR_RGB2BGR)

    h, w = process_rgb.shape[:2]

    margin_x = int(w * 0.08)
    margin_y = int(h * 0.08)
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

    grabcut_mask = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    cv2.grabCut(
        process_bgr,
        grabcut_mask,
        rect,
        bgd_model,
        fgd_model,
        5,
        cv2.GC_INIT_WITH_RECT
    )

    raw_animal_mask_small = np.where(
        (grabcut_mask == cv2.GC_FGD) | (grabcut_mask == cv2.GC_PR_FGD),
        True,
        False
    )

    animal_mask_small = keep_likely_main_object(raw_animal_mask_small)
    animal_mask = resize_mask_to_original(animal_mask_small, original_rgb.shape)

    if USE_PALE_ANIMAL_REFINEMENT:
        animal_mask = refine_pale_animal_mask(original_rgb, animal_mask)

    background_ring = create_background_ring(animal_mask, ring_width=RING_WIDTH)

    species_mask_dir = mask_dir / species
    species_ring_dir = ring_dir / species
    species_qc_dir = qc_dir / species

    species_mask_dir.mkdir(parents=True, exist_ok=True)
    species_ring_dir.mkdir(parents=True, exist_ok=True)
    species_qc_dir.mkdir(parents=True, exist_ok=True)

    mask_output_path = species_mask_dir / f"{image_id}_animal_mask_grabcut_clean.png"
    ring_output_path = species_ring_dir / f"{image_id}_background_ring{RING_WIDTH}_clean.png"

    Image.fromarray((animal_mask.astype(np.uint8) * 255)).save(mask_output_path)
    Image.fromarray((background_ring.astype(np.uint8) * 255)).save(ring_output_path)

    animal_overlay = make_overlay(original_rgb, animal_mask, colour=(255, 0, 0))
    ring_overlay = make_overlay(original_rgb, background_ring, colour=(0, 120, 255))

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    axes[0].imshow(original_rgb)
    axes[0].set_title("Original")
    axes[0].axis("off")

    axes[1].imshow(animal_overlay)
    axes[1].set_title("Animal mask clean")
    axes[1].axis("off")

    axes[2].imshow(ring_overlay)
    axes[2].set_title(f"Background ring {RING_WIDTH}px")
    axes[2].axis("off")

    plt.tight_layout()

    qc_output_path = species_qc_dir / f"{image_id}_grabcut_clean_ring{RING_WIDTH}_qc.png"
    plt.savefig(qc_output_path, dpi=200)
    plt.close()

    print(f"  saved mask: {mask_output_path}")
    print(f"  saved ring: {ring_output_path}")
    print(f"  saved QC:   {qc_output_path}")


def main():
    print("Running automatic segmentation pilot using cleaned GrabCut...\n")

    for image_path in test_images:
        if image_path.exists():
            process_image(image_path)
        else:
            print(f"MISSING: {image_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()