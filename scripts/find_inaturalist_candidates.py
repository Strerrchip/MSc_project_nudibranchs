from pathlib import Path
from collections import defaultdict
from datetime import date
import html
import re
import time

import pandas as pd
import requests


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "image_inventory.csv"
)

SPECIES_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "current_core"
    / "species_for_image_collection.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "image_candidate_search"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "inaturalist_auto_candidates.csv"
)

OUTPUT_TXT = (
    OUTPUT_DIR
    / "inaturalist_auto_candidate_blocks.txt"
)

OUTPUT_HTML = (
    OUTPUT_DIR
    / "inaturalist_candidate_review.html"
)


# ============================================================
# Settings
# ============================================================

# Aim for approximately 10 usable photographs per species.
TARGET_USABLE_PER_SPECIES = 10

# Find some extra candidates because visual inspection may later
# reject photographs with poor animal/background visibility.
EXTRA_REVIEW_CANDIDATES = 5

# Same photographer + same species:
# maximum two photographs.
MAX_PER_AUTHOR_PER_SPECIES = 2

# The second photograph from the same author must have a
# different observation/capture time.

# Search up to 5 pages per taxon name.
# iNaturalist allows up to 200 observations per page.
MAX_PAGES_PER_SEARCH_NAME = 5
PER_PAGE = 200

# Keep requests slow enough to avoid unnecessary API pressure.
REQUEST_DELAY_SECONDS = 1.05


# ============================================================
# Species already completed
# ============================================================

# These 8 species have already been manually collected.
# The script will not search for more photographs for them.

SKIP_SPECIES = {
    "Aphelodoris varia",
    "Doriprismatica atromarginata",
    "Hypselodoris bennetti",
    "Phyllidia ocellata",
    "Phyllidiella pustulosa",
    "Ardeadoris egretta",
    "Ardeadoris rubroannulata",
    "Ceratosoma brevicaudatum",
}


# ============================================================
# Allowed photograph licences
# ============================================================

# Conservative licence filter.
#
# Allowed:
# CC0
# CC BY
# CC BY-NC
# CC BY-SA
# CC BY-NC-SA
#
# Excluded automatically:
# All Rights Reserved
# missing licence
# CC BY-ND
# CC BY-NC-ND

ALLOWED_PHOTO_LICENSES = {
    "cc0",
    "cc-by",
    "cc-by-nc",
    "cc-by-sa",
    "cc-by-nc-sa",
}


# ============================================================
# Taxonomy search-name overrides
# ============================================================

# A few D03 names contain synonyms in brackets and should not
# be sent literally to the iNaturalist API.

SEARCH_NAME_OVERRIDES = {
    "Dendrodoris krusensternii (=denisoni)": [
        "Dendrodoris krusensternii",
        "Dendrodoris denisoni",
    ],

    "Notodoris (=Aegires) gardineri": [
        "Aegires gardineri",
        "Notodoris gardineri",
    ],
}


# ============================================================
# iNaturalist API setup
# ============================================================

API_URL = (
    "https://api.inaturalist.org/v1/observations"
)

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
            "Avery-Nudibranch-MSc-Image-Collection"
    }
)

LAST_REQUEST_TIME = 0.0


# ============================================================
# Basic utility functions
# ============================================================

def normalise_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalise_yes_no(value):
    return normalise_text(value).lower()


def clean_integer_id(value):
    """
    Convert values such as:

    388381275
    388381275.0

    into:

    '388381275'
    """

    text = normalise_text(value)

    if not text:
        return None

    try:
        return str(int(float(text)))

    except ValueError:
        return None


def normalise_license(value):
    text = normalise_text(value).lower()

    text = text.replace(
        "_",
        "-",
    )

    text = text.replace(
        " ",
        "-",
    )

    return text


def display_license(value):
    value = normalise_license(value)

    if value == "cc0":
        return "CC0"

    return value.upper()


def safe_filename_species(species):
    return re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        species,
    ).strip("_")


def make_image_id(species, slot):
    return (
        f"{safe_filename_species(species)}"
        f"_img{slot:02d}"
    )


def today_string():
    today = date.today()

    return (
        f"{today.year}/"
        f"{today.month}/"
        f"{today.day}"
    )


# ============================================================
# Capture-time handling
# ============================================================

def capture_key(observation):
    """
    Return a value used to decide whether two observations from
    the same photographer count as different capture times.

    Priority:
    1. exact observation time
    2. observation date
    3. unknown

    If only a date is available, two observations by the same
    photographer on the same date are treated as the same
    capture event.
    """

    exact_time = observation.get(
        "time_observed_at"
    )

    if exact_time:
        return f"time:{exact_time}"

    observed_on = observation.get(
        "observed_on"
    )

    if observed_on:
        return f"date:{observed_on}"

    return "unknown_time"


def capture_display(observation):
    exact_time = observation.get(
        "time_observed_at"
    )

    if exact_time:
        return exact_time

    observed_on = observation.get(
        "observed_on"
    )

    if observed_on:
        return observed_on

    return "unknown"


# ============================================================
# Observer information
# ============================================================

def get_author_id(observation):
    user = observation.get("user") or {}

    user_id = user.get("id")

    if user_id is not None:
        return f"id:{user_id}"

    login = normalise_text(
        user.get("login")
    )

    if login:
        return (
            f"login:{login.lower()}"
        )

    return None


def get_author_display(observation):
    user = observation.get("user") or {}

    name = normalise_text(
        user.get("name")
    )

    login = normalise_text(
        user.get("login")
    )

    if name and login:

        if name.lower() == login.lower():
            return login

        return f"{name} ({login})"

    if name:
        return name

    if login:
        return login

    return "unknown"


# ============================================================
# Photograph URL handling
# ============================================================

def replace_photo_size(
    url,
    new_size,
):
    """
    Change an iNaturalist photograph URL to another available
    image size.
    """

    if not url:
        return ""

    sizes = [
        "square",
        "thumb",
        "small",
        "medium",
        "large",
        "original",
    ]

    result = url

    for old_size in sizes:

        result = result.replace(
            f"/{old_size}.",
            f"/{new_size}.",
        )

        result = result.replace(
            f"_{old_size}.",
            f"_{new_size}.",
        )

    return result


# ============================================================
# API request helper
# ============================================================

def api_get(
    url,
    params=None,
):
    global LAST_REQUEST_TIME

    elapsed = (
        time.time()
        - LAST_REQUEST_TIME
    )

    if elapsed < REQUEST_DELAY_SECONDS:

        time.sleep(
            REQUEST_DELAY_SECONDS
            - elapsed
        )

    for attempt in range(5):

        try:

            response = SESSION.get(
                url,
                params=params,
                timeout=45,
            )

            LAST_REQUEST_TIME = (
                time.time()
            )

            if response.status_code == 429:

                wait_seconds = (
                    5 * (attempt + 1)
                )

                print(
                    "API rate limited. "
                    f"Waiting {wait_seconds} "
                    "seconds..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            response.raise_for_status()

            return response.json()

        except requests.RequestException as exc:

            if attempt == 4:
                raise

            wait_seconds = (
                3 * (attempt + 1)
            )

            print(
                f"API request failed: {exc}"
            )

            print(
                "Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        "API request failed after repeated attempts."
    )


# ============================================================
# Retrieve existing observations
# ============================================================

def fetch_existing_observations(
    observation_ids,
):
    """
    Retrieve metadata for observations already stored as usable
    in image_inventory.csv.

    Important:
    iNaturalist's /observations/{ids} endpoint cannot accept a
    very large comma-separated list.

    Therefore IDs are requested in batches of 25.
    """

    observation_ids = sorted(
        set(observation_ids)
    )

    result = {}

    # Fixed after the previous 422 error.
    batch_size = 25

    for start in range(
        0,
        len(observation_ids),
        batch_size,
    ):

        batch = observation_ids[
            start:start + batch_size
        ]

        if not batch:
            continue

        joined_ids = ",".join(
            batch
        )

        url = (
            f"{API_URL}/"
            f"{joined_ids}"
        )

        end_number = (
            start
            + len(batch)
        )

        print(
            "Checking existing observations "
            f"{start + 1}-{end_number}..."
        )

        data = api_get(
            url
        )

        for observation in data.get(
            "results",
            [],
        ):

            observation_id = str(
                observation.get("id")
            )

            result[
                observation_id
            ] = observation

    return result


# ============================================================
# Load project tables
# ============================================================

def load_project_data():

    if not INVENTORY_CSV.exists():

        raise FileNotFoundError(
            "Cannot find inventory:\n"
            f"{INVENTORY_CSV}"
        )

    if not SPECIES_CSV.exists():

        raise FileNotFoundError(
            "Cannot find D03 species table:\n"
            f"{SPECIES_CSV}"
        )

    inventory = pd.read_csv(
        INVENTORY_CSV,
        dtype=str,
    )

    species_table = pd.read_csv(
        SPECIES_CSV,
        dtype=str,
    )

    required_inventory_columns = {
        "species",
        "image_slot",
        "observation_id",
        "usable",
    }

    missing_columns = (
        required_inventory_columns
        - set(inventory.columns)
    )

    if missing_columns:

        raise ValueError(
            "image_inventory.csv is missing columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    if (
        "species"
        not in species_table.columns
    ):

        raise ValueError(
            "species_for_image_collection.csv "
            "does not contain a species column."
        )

    return (
        inventory,
        species_table,
    )


# ============================================================
# Existing photographer history
# ============================================================

def build_existing_history(
    inventory,
):

    all_existing_observation_ids = set()

    usable_observation_to_species = {}

    for _, row in inventory.iterrows():

        observation_id = clean_integer_id(
            row.get(
                "observation_id"
            )
        )

        if observation_id:

            all_existing_observation_ids.add(
                observation_id
            )

        if (
            observation_id
            and normalise_yes_no(
                row.get("usable")
            )
            == "yes"
        ):

            species = normalise_text(
                row.get("species")
            )

            usable_observation_to_species[
                observation_id
            ] = species

    print()

    print(
        "Existing observations in inventory:",
        len(
            all_existing_observation_ids
        ),
    )

    print(
        "Existing usable observations:",
        len(
            usable_observation_to_species
        ),
    )

    existing_metadata = (
        fetch_existing_observations(
            usable_observation_to_species.keys()
        )
    )

    # history:
    #
    # species
    #   -> photographer
    #       -> set of capture times

    history = defaultdict(
        lambda: defaultdict(set)
    )

    for (
        observation_id,
        species,
    ) in usable_observation_to_species.items():

        observation = (
            existing_metadata.get(
                observation_id
            )
        )

        if observation is None:
            continue

        author_id = get_author_id(
            observation
        )

        if author_id is None:
            continue

        capture = capture_key(
            observation
        )

        history[
            species
        ][
            author_id
        ].add(
            capture
        )

    return (
        all_existing_observation_ids,
        history,
    )


# ============================================================
# Existing usable counts
# ============================================================

def existing_usable_count(
    inventory,
    species,
):

    species_rows = inventory[
        inventory[
            "species"
        ]
        .fillna("")
        .str.strip()
        == species
    ]

    if species_rows.empty:
        return 0

    usable_count = (
        species_rows[
            "usable"
        ]
        .fillna("")
        .str.strip()
        .str.lower()
        .eq("yes")
        .sum()
    )

    return int(
        usable_count
    )


# ============================================================
# Determine next image slot
# ============================================================

def next_image_slot(
    inventory,
    species,
):

    species_rows = inventory[
        inventory[
            "species"
        ]
        .fillna("")
        .str.strip()
        == species
    ]

    if species_rows.empty:
        return 1

    numeric_slots = pd.to_numeric(
        species_rows[
            "image_slot"
        ],
        errors="coerce",
    ).dropna()

    if numeric_slots.empty:
        return 1

    return (
        int(
            numeric_slots.max()
        )
        + 1
    )


# ============================================================
# Select an openly licensed photograph
# ============================================================

def choose_open_photo(
    observation,
):

    photos = (
        observation.get("photos")
        or []
    )

    for photo in photos:

        licence = normalise_license(
            photo.get(
                "license_code"
            )
        )

        # No licence, ARR or ND:
        # automatically excluded.
        if (
            licence
            not in ALLOWED_PHOTO_LICENSES
        ):
            continue

        photo_url = normalise_text(
            photo.get("url")
        )

        if not photo_url:
            continue

        return photo

    return None


# ============================================================
# Search names for each species
# ============================================================

def get_search_names(
    species,
):

    if (
        species
        in SEARCH_NAME_OVERRIDES
    ):

        return (
            SEARCH_NAME_OVERRIDES[
                species
            ]
        )

    return [species]


# ============================================================
# Search one species
# ============================================================

def search_species_candidates(
    species,
    number_needed,
    next_slot,
    existing_observation_ids,
    history,
):

    candidate_goal = (
        number_needed
        + EXTRA_REVIEW_CANDIDATES
    )

    candidates = []

    selected_observation_ids = set()

    search_names = get_search_names(
        species
    )

    print()
    print("=" * 70)

    print(
        "Species:",
        species,
    )

    print(
        "Usable images still needed:",
        number_needed,
    )

    print(
        "Candidate images requested:",
        candidate_goal,
    )

    print(
        "Search names:",
        ", ".join(
            search_names
        ),
    )

    for search_name in search_names:

        if (
            len(candidates)
            >= candidate_goal
        ):
            break

        for page in range(
            1,
            MAX_PAGES_PER_SEARCH_NAME + 1,
        ):

            if (
                len(candidates)
                >= candidate_goal
            ):
                break

            params = {
                "taxon_name":
                    search_name,

                "quality_grade":
                    "research",

                "photos":
                    "true",

                "per_page":
                    PER_PAGE,

                "page":
                    page,

                "order_by":
                    "observed_on",

                "order":
                    "desc",
            }

            print(
                f"Searching {search_name}, "
                f"page {page}..."
            )

            data = api_get(
                API_URL,
                params=params,
            )

            observations = (
                data.get(
                    "results",
                    [],
                )
            )

            if not observations:
                break

            for observation in observations:

                if (
                    len(candidates)
                    >= candidate_goal
                ):
                    break

                observation_id = str(
                    observation.get(
                        "id"
                    )
                )

                # Do not return anything already
                # present in image_inventory.csv.
                if (
                    observation_id
                    in existing_observation_ids
                ):
                    continue

                # Do not duplicate an observation
                # within the current search run.
                if (
                    observation_id
                    in selected_observation_ids
                ):
                    continue

                author_id = get_author_id(
                    observation
                )

                # Skip observations where an author
                # cannot be identified because the
                # author-frequency rule could not be
                # enforced reliably.
                if author_id is None:
                    continue

                current_capture = capture_key(
                    observation
                )

                author_capture_times = (
                    history[
                        species
                    ][
                        author_id
                    ]
                )

                # Rule:
                # Same author + same species:
                # maximum two photographs.
                if (
                    len(
                        author_capture_times
                    )
                    >=
                    MAX_PER_AUTHOR_PER_SPECIES
                ):
                    continue

                # Rule:
                # The second image from the same
                # photographer must have a different
                # capture time/date.
                if (
                    current_capture
                    in author_capture_times
                ):
                    continue

                # Select the first photo from this
                # observation that has an allowed
                # photo licence.
                photo = choose_open_photo(
                    observation
                )

                if photo is None:
                    continue

                licence = normalise_license(
                    photo.get(
                        "license_code"
                    )
                )

                photo_id = clean_integer_id(
                    photo.get("id")
                )

                photo_url = normalise_text(
                    photo.get("url")
                )

                medium_url = (
                    replace_photo_size(
                        photo_url,
                        "medium",
                    )
                )

                large_url = (
                    replace_photo_size(
                        photo_url,
                        "large",
                    )
                )

                slot = (
                    next_slot
                    + len(candidates)
                )

                image_id = make_image_id(
                    species,
                    slot,
                )

                author_display = (
                    get_author_display(
                        observation
                    )
                )

                observation_url = (
                    "https://www.inaturalist.org/"
                    f"observations/{observation_id}"
                )

                record = {
                    "species":
                        species,

                    "image_slot":
                        slot,

                    "image_id":
                        image_id,

                    "analysis_stage":
                        "candidate",

                    "source":
                        "iNaturalist",

                    "observation_id":
                        observation_id,

                    "observation_url":
                        observation_url,

                    "license":
                        display_license(
                            licence
                        ),

                    "photographer_or_observer":
                        author_display,

                    "date_accessed":
                        today_string(),

                    "capture_time":
                        capture_display(
                            observation
                        ),

                    "source_photo_id":
                        photo_id or "",

                    "photo_url_medium":
                        medium_url,

                    "photo_url_large":
                        large_url,
                }

                candidates.append(
                    record
                )

                selected_observation_ids.add(
                    observation_id
                )

                # Reserve this photographer/time
                # immediately so later candidates
                # cannot violate the maximum-two rule.
                history[
                    species
                ][
                    author_id
                ].add(
                    current_capture
                )

            total_results = data.get(
                "total_results",
                0,
            )

            if (
                page * PER_PAGE
                >= total_results
            ):
                break

    print(
        "Candidates found:",
        len(candidates),
    )

    return candidates


# ============================================================
# Create copyable record
# ============================================================

def make_usable_block(
    record,
):

    return (
        f"species: {record['species']}\n"
        f"image_slot: {record['image_slot']}\n"
        f"image_id: {record['image_id']}\n"
        f"analysis_stage: candidate\n"
        f"source: iNaturalist\n"
        f"observation_id: "
        f"{record['observation_id']}\n"
        f"observation_url: "
        f"{record['observation_url']}\n"
        f"license: {record['license']}\n"
        f"photographer_or_observer: "
        f"{record['photographer_or_observer']}\n"
        f"date_accessed: "
        f"{record['date_accessed']}\n"
        f"usable: yes\n"
        f"exclusion_reason:\n"
        f"animal_clear: yes\n"
        f"background_clear: yes\n"
        f"notes: Research grade; whole animal "
        f"clear and fully visible; colour pattern "
        f"visible; natural background clear"
    )


# ============================================================
# Save plain-text blocks
# ============================================================

def save_text_blocks(
    records,
):

    lines = []

    for (
        index,
        record,
    ) in enumerate(
        records,
        start=1,
    ):

        lines.append(
            "=" * 80
        )

        lines.append(
            f"CANDIDATE {index}"
        )

        lines.append(
            "Capture time: "
            f"{record['capture_time']}"
        )

        lines.append(
            "Photo preview: "
            f"{record['photo_url_large']}"
        )

        lines.append("")

        lines.append(
            make_usable_block(
                record
            )
        )

        lines.append("")

    OUTPUT_TXT.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )


# ============================================================
# Save browser review page
# ============================================================

def save_review_html(
    records,
):

    grouped = defaultdict(list)

    for record in records:

        grouped[
            record["species"]
        ].append(
            record
        )

    html_parts = []

    html_parts.append(
        """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<title>
iNaturalist candidate review
</title>

<style>

body {
    font-family: Arial, sans-serif;
    margin: 24px;
    background: #f5f5f5;
    color: #222;
}

h1 {
    margin-bottom: 8px;
}

.warning {
    background: #fff3cd;
    border: 1px solid #e6c75a;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 24px;
}

.species-title {
    margin-top: 40px;
    padding-bottom: 8px;
    border-bottom: 2px solid #444;
}

.card {
    background: white;
    border-radius: 12px;
    padding: 18px;
    margin: 18px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

.photo {
    max-width: 700px;
    max-height: 600px;
    display: block;
    margin-bottom: 14px;
}

.meta {
    line-height: 1.6;
}

pre {
    white-space: pre-wrap;
    background: #f2f2f2;
    padding: 14px;
    border-radius: 8px;
    overflow-x: auto;
}

button {
    padding: 9px 14px;
    margin-right: 8px;
    cursor: pointer;
    font-size: 14px;
}

a {
    color: #1666c5;
}

</style>


<script>

function copyBlock(id) {

    const element =
        document.getElementById(id);

    const text =
        element.innerText;

    if (
        navigator.clipboard
        && window.isSecureContext
    ) {

        navigator.clipboard
            .writeText(text)
            .then(() => {
                alert("Copied");
            });

        return;
    }

    const textarea =
        document.createElement(
            "textarea"
        );

    textarea.value = text;

    document.body.appendChild(
        textarea
    );

    textarea.select();

    document.execCommand(
        "copy"
    );

    document.body.removeChild(
        textarea
    );

    alert("Copied");
}

</script>

</head>

<body>
"""
    )

    html_parts.append(
        "<h1>"
        "iNaturalist candidate review"
        "</h1>"
    )

    html_parts.append(
        f"<p>Total candidates: "
        f"{len(records)}</p>"
    )

    html_parts.append(
        """
<div class="warning">

<b>Important:</b><br>

The script has already filtered:
<br>
- photograph licences
<br>
- existing observations
<br>
- same-author maximum
<br>
- same-author repeated capture times
<br>
- Research Grade status
<br><br>

It has NOT automatically decided whether the nudibranch
and natural background are visually suitable.

Check the photograph before clicking
<b>Copy usable record</b>.

</div>
"""
    )

    block_number = 0

    for (
        species,
        species_records,
    ) in grouped.items():

        html_parts.append(
            '<h2 class="species-title">'
            f'{html.escape(species)} '
            f'({len(species_records)} candidates)'
            '</h2>'
        )

        for record in species_records:

            block_number += 1

            block_id = (
                f"copy_block_"
                f"{block_number}"
            )

            block_text = html.escape(
                make_usable_block(
                    record
                )
            )

            observation_url = html.escape(
                record[
                    "observation_url"
                ]
            )

            medium_url = html.escape(
                record[
                    "photo_url_medium"
                ]
            )

            large_url = html.escape(
                record[
                    "photo_url_large"
                ]
            )

            author = html.escape(
                record[
                    "photographer_or_observer"
                ]
            )

            licence = html.escape(
                record[
                    "license"
                ]
            )

            capture = html.escape(
                record[
                    "capture_time"
                ]
            )

            image_id = html.escape(
                record[
                    "image_id"
                ]
            )

            source_photo_id = html.escape(
                str(
                    record[
                        "source_photo_id"
                    ]
                )
            )

            html_parts.append(
                f"""
<div class="card">

<h3>
{image_id}
</h3>

<a
href="{large_url}"
target="_blank"
>

<img
class="photo"
src="{medium_url}"
loading="lazy"
alt="{image_id}"
>

</a>


<div class="meta">

<b>Author:</b>
{author}
<br>

<b>Capture time:</b>
{capture}
<br>

<b>Licence:</b>
{licence}
<br>

<b>Photo ID:</b>
{source_photo_id}
<br>

<b>Observation:</b>

<a
href="{observation_url}"
target="_blank"
>
{observation_url}
</a>

</div>


<p>

<b>Visual check:</b>

Is the whole nudibranch clear and sufficiently visible?

Is the colour pattern visible?

Is there enough natural background around the animal
for the immediate-background ring?

</p>


<button
onclick="copyBlock('{block_id}')"
>
Copy usable record
</button>


<pre id="{block_id}">{block_text}</pre>

</div>
"""
            )

    html_parts.append(
        """
</body>
</html>
"""
    )

    OUTPUT_HTML.write_text(
        "\n".join(
            html_parts
        ),
        encoding="utf-8",
    )


# ============================================================
# Main workflow
# ============================================================

def main():

    print(
        "Loading project data..."
    )

    (
        inventory,
        species_table,
    ) = load_project_data()

    (
        existing_observation_ids,
        author_history,
    ) = build_existing_history(
        inventory
    )

    target_species = (
        species_table[
            "species"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    target_species = [
        species

        for species
        in target_species

        if species
        and species
        not in SKIP_SPECIES
    ]

    print()

    print(
        "Completed species skipped:",
        len(SKIP_SPECIES),
    )

    print(
        "Species remaining to search:",
        len(target_species),
    )

    print()

    print(
        "Remaining species:"
    )

    for species in target_species:
        print(
            "-",
            species,
        )

    all_candidates = []

    for species in target_species:

        usable_now = (
            existing_usable_count(
                inventory,
                species,
            )
        )

        number_needed = max(
            0,
            TARGET_USABLE_PER_SPECIES
            - usable_now,
        )

        print()

        print(
            f"{species}: "
            f"{usable_now} usable "
            "already in inventory"
        )

        if number_needed == 0:

            print(
                "Target already reached. "
                "Skipping."
            )

            continue

        next_slot = (
            next_image_slot(
                inventory,
                species,
            )
        )

        candidates = (
            search_species_candidates(

                species=species,

                number_needed=(
                    number_needed
                ),

                next_slot=(
                    next_slot
                ),

                existing_observation_ids=(
                    existing_observation_ids
                ),

                history=(
                    author_history
                ),
            )
        )

        all_candidates.extend(
            candidates
        )

        # Prevent candidates selected for one search
        # from being selected again later during the
        # same execution.
        for record in candidates:

            existing_observation_ids.add(
                record[
                    "observation_id"
                ]
            )

    candidate_df = pd.DataFrame(
        all_candidates
    )

    candidate_df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    save_text_blocks(
        all_candidates
    )

    save_review_html(
        all_candidates
    )

    print()
    print("=" * 70)
    print("SEARCH COMPLETE")
    print()

    print(
        "Completed species skipped:",
        len(SKIP_SPECIES),
    )

    print(
        "Species searched:",
        len(target_species),
    )

    print(
        "Total candidates:",
        len(all_candidates),
    )

    print()

    print(
        "Candidate CSV:"
    )

    print(
        OUTPUT_CSV.relative_to(
            PROJECT_ROOT
        )
    )

    print()

    print(
        "Copyable text blocks:"
    )

    print(
        OUTPUT_TXT.relative_to(
            PROJECT_ROOT
        )
    )

    print()

    print(
        "Visual review page:"
    )

    print(
        OUTPUT_HTML.relative_to(
            PROJECT_ROOT
        )
    )

    print()

    print(
        "Open the HTML file in your browser "
        "and review the photographs."
    )


if __name__ == "__main__":
    main()