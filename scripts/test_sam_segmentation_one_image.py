from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from ultralytics import SAM
from skimage import measure, morphology


PROJECT_DIR = Path(__file__).resolve().parents[1]

image_path = (
    PROJECT_DIR
    / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img01.jpg"
)

base_output_dir = PROJECT_DIR / "processed_data/automated_image_analysis"
mask_dir = base_output_dir / "masks" / "sam_test"
qc_dir = base_output_dir / "qc_figures" / "sam_test"

mask_dir.mkdir(parents=True, exist_ok=True)
qc_dir.mkdir(parents=True, exist_ok=True)

RING_WIDTH = 80


def resize_mask_to_image(mask, image_shape):
    image_h, image_w = image_shape[:2]

    if mask.shape == (image_h, image_w):
        return mask.astype(bool)

    resized = cv2.resize(
        mask.astype(np.uint8),
        (image_w, image_h),
        interpolation=cv2.INTER_NEAREST
    )

    return resized.astype(bool)


def keep_largest_connected_part(mask):
    mask = mask.astype(bool)

    mask = morphology.remove_small_objects(
        mask,
        min_size=max(100, int(mask.size * 0.001))
    )

    labels = measure.label(mask)

    if labels.max() == 0:
        return mask

    regions = measure.regionprops(labels)
    largest_region = max(regions, key=lambda r: r.area)

    clean_mask = labels == largest_region.label

    clean_mask = morphology.remove_small_holes(
        clean_mask,
        area_threshold=max(100, int(mask.size * 0.001))
    )

    clean_mask = morphology.binary_closing(clean_mask, morphology.disk(4))

    return clean_mask


def score_mask(mask, image_rgb):
    """
    Score a SAM candidate mask.

    This version is designed for the current pale / white pilot nudibranchs.
    It prefers masks that are bright, not too saturated, central, and not too large.
    """
    mask = mask.astype(bool)
    h, w = mask.shape
    image_area = h * w

    area = mask.sum()
    area_fraction = area / image_area

    if area_fraction < 0.01 or area_fraction > 0.45:
        return -999999

    labels = measure.label(mask)

    if labels.max() == 0:
        return -999999

    regions = measure.regionprops(labels)
    largest_region = max(regions, key=lambda r: r.area)

    cy, cx = largest_region.centroid

    centre_distance = np.sqrt(
        ((cx - w / 2) / (w / 2)) ** 2
        + ((cy - h / 2) / (h / 2)) ** 2
    )

    minr, minc, maxr, maxc = largest_region.bbox
    touches_border = minr == 0 or minc == 0 or maxr == h or maxc == w

    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    brightness = hsv[:, :, 2]

    mean_brightness = float(np.mean(brightness[mask]))
    mean_saturation = float(np.mean(saturation[mask]))

    # Pale nudibranchs should usually be bright and relatively low in saturation.
    pale_score = mean_brightness - 0.6 * mean_saturation

    # Avoid masks that are too large, because they are often background.
    size_penalty = abs(area_fraction - 0.20) * 300

    score = 0
    score += pale_score * 1000
    score -= centre_distance * 500
    score -= size_penalty

    if touches_border:
        score -= 500

    return score


def create_background_ring(animal_mask, ring_width):
    dilated_mask = morphology.binary_dilation(
        animal_mask,
        morphology.disk(ring_width)
    )

    background_ring = dilated_mask & (~animal_mask)

    return background_ring


def make_overlay(image_rgb, mask, colour):
    overlay = image_rgb.copy().astype(float)
    colour = np.array(colour)

    overlay[mask] = overlay[mask] * 0.35 + colour * 0.65

    return np.clip(overlay, 0, 255).astype(np.uint8)


def main():
    print("Running SAM segmentation test with pale-animal scoring...\n")
    print(f"Image: {image_path}")

    image_rgb = np.array(Image.open(image_path).convert("RGB"))

    model = SAM("mobile_sam.pt")
    results = model(str(image_path), verbose=False)

    if len(results) == 0 or results[0].masks is None:
        raise RuntimeError("SAM did not return any masks for this image.")

    raw_masks = results[0].masks.data.cpu().numpy()

    print(f"Number of candidate masks: {len(raw_masks)}")

    candidate_masks = []

    for mask in raw_masks:
        mask = resize_mask_to_image(mask, image_rgb.shape)
        mask = keep_largest_connected_part(mask)
        candidate_masks.append(mask)

    scores = [score_mask(mask, image_rgb) for mask in candidate_masks]

    best_index = int(np.argmax(scores))
    animal_mask = candidate_masks[best_index]

    print(f"Selected candidate index: {best_index}")
    print(f"Selected candidate score: {scores[best_index]:.3f}")

    background_ring = create_background_ring(animal_mask, ring_width=RING_WIDTH)

    image_id = image_path.stem

    mask_output_path = mask_dir / f"{image_id}_sam_pale_score_animal_mask.png"
    ring_output_path = mask_dir / f"{image_id}_sam_pale_score_background_ring{RING_WIDTH}.png"

    Image.fromarray((animal_mask.astype(np.uint8) * 255)).save(mask_output_path)
    Image.fromarray((background_ring.astype(np.uint8) * 255)).save(ring_output_path)

    animal_overlay = make_overlay(image_rgb, animal_mask, colour=(255, 0, 0))
    ring_overlay = make_overlay(image_rgb, background_ring, colour=(0, 120, 255))

    top_indices = np.argsort(scores)[::-1][:6]

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.ravel()

    axes[0].imshow(image_rgb)
    axes[0].set_title("Original")
    axes[0].axis("off")

    axes[1].imshow(animal_overlay)
    axes[1].set_title(f"Selected mask {best_index}")
    axes[1].axis("off")

    axes[2].imshow(ring_overlay)
    axes[2].set_title(f"Background ring {RING_WIDTH}px")
    axes[2].axis("off")

    axes[3].imshow(image_rgb)
    axes[3].set_title("Original again")
    axes[3].axis("off")

    for plot_i, mask_i in enumerate(top_indices[:4], start=4):
        candidate_overlay = make_overlay(
            image_rgb,
            candidate_masks[mask_i],
            colour=(255, 0, 0)
        )

        axes[plot_i].imshow(candidate_overlay)
        axes[plot_i].set_title(f"Candidate {mask_i}, score={scores[mask_i]:.0f}")
        axes[plot_i].axis("off")

    plt.tight_layout()

    qc_output_path = qc_dir / f"{image_id}_sam_pale_score_qc.png"
    plt.savefig(qc_output_path, dpi=200)
    plt.close()

    print("\nSaved SAM mask to:")
    print(mask_output_path)

    print("\nSaved SAM QC figure to:")
    print(qc_output_path)

    print("\nDone.")


if __name__ == "__main__":
    main()