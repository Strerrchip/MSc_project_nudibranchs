from pathlib import Path
import io
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


INPUT_PATH = Path(
    "processed_data/analysis_preparation/"
    "image_download_queue_current5_api_audit.csv"
)

OUTPUT_DIR = Path(
    "processed_data/automated_image_analysis/"
    "qc_figures/download_selection"
)

API_TEMPLATE = (
    "https://api.inaturalist.org/v1/observations/{observation_id}"
)

PREVIEW_SIZE = (500, 500)
REQUEST_DELAY_SECONDS = 0.3
TIMEOUT_SECONDS = 30


def fetch_json(url: str) -> dict:
    """Read JSON from a public URL."""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "MSc-nudibranch-photo-review/1.0 "
                "(academic research)"
            )
        },
    )

    try:
        with urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            return json.load(response)

    except HTTPError as exc:
        raise RuntimeError(
            f"HTTP {exc.code} while reading:\n{url}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Network error while reading:\n{url}\n"
            f"{exc.reason}"
        ) from exc


def fetch_image(url: str) -> Image.Image:
    """Download one preview image."""

    request = Request(
        url,
        headers={
            "User-Agent": (
                "MSc-nudibranch-photo-review/1.0 "
                "(academic research)"
            )
        },
    )

    try:
        with urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            image_bytes = response.read()

    except HTTPError as exc:
        raise RuntimeError(
            f"HTTP {exc.code} while downloading:\n{url}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Network error while downloading:\n{url}\n"
            f"{exc.reason}"
        ) from exc

    return Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")


def make_large_url(photo_url: str) -> str:
    """Use the iNaturalist large preview version."""

    replacements = [
        "/square.",
        "/thumb.",
        "/small.",
        "/medium.",
    ]

    result = photo_url

    for old in replacements:
        result = result.replace(old, "/large.")

    return result


def fit_image(
    image: Image.Image,
    target_size: tuple[int, int],
) -> Image.Image:
    """Fit an image inside a fixed white panel."""

    image_copy = image.copy()
    image_copy.thumbnail(target_size)

    panel = Image.new(
        "RGB",
        target_size,
        "white",
    )

    x = (target_size[0] - image_copy.width) // 2
    y = (target_size[1] - image_copy.height) // 2

    panel.paste(
        image_copy,
        (x, y),
    )

    return panel


def create_contact_sheet(
    image_id: str,
    observation_id: str,
    photos: list[dict],
) -> Path:
    """Create one labelled contact sheet."""

    font = ImageFont.load_default()

    columns = 2
    rows = math.ceil(len(photos) / columns)

    label_height = 70
    panel_width = PREVIEW_SIZE[0]
    panel_height = PREVIEW_SIZE[1] + label_height

    title_height = 70

    canvas = Image.new(
        "RGB",
        (
            columns * panel_width,
            title_height + rows * panel_height,
        ),
        "white",
    )

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (15, 15),
        (
            f"{image_id}\n"
            f"Observation {observation_id}"
        ),
        fill="black",
        font=font,
    )

    for index, photo in enumerate(photos):
        row = index // columns
        column = index % columns

        x = column * panel_width
        y = title_height + row * panel_height

        preview = fit_image(
            photo["image"],
            PREVIEW_SIZE,
        )

        canvas.paste(
            preview,
            (x, y),
        )

        label = (
            f"Photo {index + 1}\n"
            f"photo_id: {photo['photo_id']}\n"
            f"licence: {photo['license_code'] or 'none'}"
        )

        draw.text(
            (
                x + 10,
                y + PREVIEW_SIZE[1] + 5,
            ),
            label,
            fill="black",
            font=font,
        )

    output_path = OUTPUT_DIR / (
        f"{image_id}_photo_selection.jpg"
    )

    canvas.save(
        output_path,
        quality=92,
    )

    return output_path


def main() -> None:
    """Create review sheets for observations with multiple photos."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_PATH.resolve()}"
        )

    audit = pd.read_csv(
        INPUT_PATH,
        dtype=str,
        keep_default_na=False,
    )

    multiple = audit[
        audit["photo_selection_status"]
        == "multiple_photos_review_required"
    ].copy()

    if multiple.empty:
        print(
            "No observations with multiple photos were found."
        )
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Observations requiring review: {len(multiple)}"
    )

    for position, (_, row) in enumerate(
        multiple.iterrows(),
        start=1,
    ):
        image_id = row["image_id"]
        observation_id = row["observation_id"]

        print(
            f"[{position}/{len(multiple)}] "
            f"{image_id}"
        )

        api_url = API_TEMPLATE.format(
            observation_id=observation_id
        )

        response = fetch_json(api_url)
        results = response.get("results", [])

        if len(results) != 1:
            raise RuntimeError(
                f"Unexpected API result for {observation_id}"
            )

        observation_photos = results[0].get(
            "observation_photos",
            [],
        )

        photos = []

        for item in observation_photos:
            photo = item.get("photo", {})

            photo_url = make_large_url(
                photo.get("url", "")
            )

            if not photo_url:
                continue

            photos.append(
                {
                    "photo_id": str(
                        photo.get("id", "")
                    ),
                    "license_code": (
                        photo.get("license_code", "")
                        or ""
                    ),
                    "image": fetch_image(photo_url),
                }
            )

            time.sleep(REQUEST_DELAY_SECONDS)

        if len(photos) < 2:
            raise RuntimeError(
                f"Expected multiple photos for {image_id}, "
                f"but downloaded {len(photos)}."
            )

        output_path = create_contact_sheet(
            image_id=image_id,
            observation_id=observation_id,
            photos=photos,
        )

        print(f"  Saved: {output_path}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print("\nMulti-photo review sheets completed.")
    print(f"Output folder:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()