from __future__ import annotations

import argparse
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

INVENTORY_CSV = ROOT / "processed_data" / "image_inventory.csv"

OUTPUT_ROOT = ROOT / "raw_data" / "formal_images"

API_URL = "https://api.inaturalist.org/v1/observations"

BATCH_SIZE = 25

USER_AGENT = "MSc-nudibranch-image-analysis/1.0 academic research"


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalise_id(value):
    value = clean(value)

    if value.endswith(".0"):
        value = value[:-2]

    return value


def safe_name(value):
    return re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        clean(value),
    ).strip("_")


def original_photo_url(url):
    url = clean(url)

    if not url:
        return ""

    return re.sub(
        r"/(?:square|small|medium|large)\.",
        "/original.",
        url,
    )


def save_inventory(df):
    temp = INVENTORY_CSV.with_suffix(".tmp.csv")

    df.to_csv(
        temp,
        index=False,
        encoding="utf-8-sig",
    )

    temp.replace(INVENTORY_CSV)


def get_pending(inventory):
    downloaded = (
        inventory["image_downloaded"]
        .fillna("")
        .str.strip()
        .str.lower()
    )

    usable = (
        inventory["usable"]
        .fillna("")
        .str.strip()
        .str.lower()
    )

    return inventory[
        (downloaded != "yes")
        & (usable == "yes")
    ].copy()


def fetch_photo_urls(pending):
    observation_ids = (
        pending["observation_id"]
        .apply(normalise_id)
        .drop_duplicates()
        .tolist()
    )

    print()
    print("Resolving iNaturalist photo URLs...")
    print("Observations:", len(observation_ids))

    session = requests.Session()

    session.headers.update(
        {"User-Agent": USER_AGENT}
    )

    lookup = {}

    total_batches = (
        len(observation_ids)
        + BATCH_SIZE
        - 1
    ) // BATCH_SIZE

    for start in range(
        0,
        len(observation_ids),
        BATCH_SIZE,
    ):

        batch = observation_ids[
            start:start + BATCH_SIZE
        ]

        batch_number = (
            start // BATCH_SIZE
        ) + 1

        print(
            f"API batch "
            f"{batch_number}/{total_batches}"
        )

        response = session.get(
            API_URL,
            params={
                "id": ",".join(batch),
                "per_page": 200,
            },
            timeout=60,
        )

        response.raise_for_status()

        results = response.json().get(
            "results",
            [],
        )

        for observation in results:

            observation_id = normalise_id(
                observation.get("id", "")
            )

            for photo in observation.get(
                "photos",
                [],
            ):

                photo_id = normalise_id(
                    photo.get("id", "")
                )

                url = original_photo_url(
                    photo.get("url", "")
                )

                if (
                    observation_id
                    and photo_id
                    and url
                ):
                    lookup[
                        (
                            observation_id,
                            photo_id,
                        )
                    ] = url

        time.sleep(0.3)

    return lookup


def build_plan(inventory):
    pending = get_pending(inventory)

    print()
    print("Inventory rows:", len(inventory))
    print(
        "Already downloaded:",
        (
            inventory["image_downloaded"]
            .fillna("")
            .str.lower()
            .eq("yes")
            .sum()
        ),
    )
    print(
        "Pending usable images:",
        len(pending),
    )

    missing_obs = (
        pending["observation_id"]
        .fillna("")
        .str.strip()
        .eq("")
    )

    missing_photo = (
        pending["source_photo_id"]
        .fillna("")
        .str.strip()
        .eq("")
    )

    if missing_obs.any():
        raise ValueError(
            "Some pending rows are missing observation_id."
        )

    if missing_photo.any():
        raise ValueError(
            "Some pending rows are missing source_photo_id."
        )

    lookup = fetch_photo_urls(
        pending
    )

    rows = []

    for inventory_index, row in pending.iterrows():

        species = clean(
            row["species"]
        )

        image_id = clean(
            row["image_id"]
        )

        observation_id = normalise_id(
            row["observation_id"]
        )

        photo_id = normalise_id(
            row["source_photo_id"]
        )

        url = lookup.get(
            (
                observation_id,
                photo_id,
            ),
            "",
        )

        folder = safe_name(
            species
        )

        filename = (
            safe_name(image_id)
            + ".jpg"
        )

        relative_path = (
            Path("raw_data")
            / "formal_images"
            / folder
            / filename
        )

        output_path = (
            ROOT
            / relative_path
        )

        if not url:
            action = "ERROR_PHOTO_NOT_FOUND"

        elif output_path.exists():
            action = "ERROR_FILE_ALREADY_EXISTS"

        else:
            action = "DOWNLOAD"

        rows.append(
            {
                "inventory_index":
                    inventory_index,
                "species":
                    species,
                "image_id":
                    image_id,
                "observation_id":
                    observation_id,
                "source_photo_id":
                    photo_id,
                "photo_url":
                    url,
                "planned_path":
                    relative_path.as_posix(),
                "action":
                    action,
            }
        )

    return pd.DataFrame(rows)


def print_plan(plan):
    print()
    print("=" * 72)
    print("FULL INVENTORY DOWNLOAD PLAN")
    print("=" * 72)

    print()
    print("Rows in plan:", len(plan))

    print()
    print("Action summary:")
    print(
        plan["action"]
        .value_counts()
        .to_string()
    )

    problems = plan[
        plan["action"] != "DOWNLOAD"
    ]

    print()
    print(
        "Problems detected:",
        len(problems),
    )

    if len(problems) > 0:
        print(
            problems[
                [
                    "species",
                    "image_id",
                    "observation_id",
                    "source_photo_id",
                    "action",
                ]
            ].to_string(
                index=False
            )
        )

    print()
    print("First 10 planned downloads:")

    print(
        plan[
            [
                "species",
                "image_id",
                "source_photo_id",
                "planned_path",
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )


def execute(plan, inventory):
    problems = plan[
        plan["action"] != "DOWNLOAD"
    ]

    if len(problems) > 0:
        raise RuntimeError(
            "Download stopped because "
            "the dry-run contains errors."
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = (
        INVENTORY_CSV.parent
        / (
            "image_inventory_before_full_download_"
            f"{timestamp}.csv"
        )
    )

    shutil.copy2(
        INVENTORY_CSV,
        backup,
    )

    print()
    print("Backup created:")
    print(backup)
    print()

    session = requests.Session()

    session.headers.update(
        {"User-Agent": USER_AGENT}
    )

    successful = 0
    failed = 0

    total = len(plan)

    for number, (_, row) in enumerate(
        plan.iterrows(),
        start=1,
    ):

        inventory_index = int(
            row["inventory_index"]
        )

        relative_path = Path(
            row["planned_path"]
        )

        output_path = (
            ROOT
            / relative_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"[{number}/{total}] "
            f"{row['image_id']}"
        )

        try:

            response = session.get(
                row["photo_url"],
                timeout=90,
            )

            response.raise_for_status()

            output_path.write_bytes(
                response.content
            )

            with Image.open(
                output_path
            ) as image:

                width, height = image.size

                image.verify()

            inventory.at[
                inventory_index,
                "original_image_path",
            ] = relative_path.as_posix()

            inventory.at[
                inventory_index,
                "original_width",
            ] = str(width)

            inventory.at[
                inventory_index,
                "original_height",
            ] = str(height)

            inventory.at[
                inventory_index,
                "image_downloaded",
            ] = "yes"

            save_inventory(
                inventory
            )

            successful += 1

            print(
                f"  saved "
                f"({width} x {height})"
            )

        except Exception as exc:

            failed += 1

            print(
                f"  FAILED: {exc}"
            )

            if output_path.exists():
                output_path.unlink()

        time.sleep(0.15)

    print()
    print("=" * 72)
    print("DOWNLOAD COMPLETE")
    print("=" * 72)

    print("Successful:", successful)
    print("Failed:", failed)
    print("Backup:", backup)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute",
        action="store_true",
    )

    args = parser.parse_args()

    inventory = pd.read_csv(
        INVENTORY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    plan = build_plan(
        inventory
    )

    print_plan(
        plan
    )

    if not args.execute:

        print()
        print("DRY RUN ONLY.")
        print(
            "No images were downloaded."
        )
        print(
            "image_inventory.csv was not changed."
        )

        return

    execute(
        plan,
        inventory,
    )


if __name__ == "__main__":
    main()