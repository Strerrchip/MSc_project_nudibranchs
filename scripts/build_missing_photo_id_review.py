from pathlib import Path
import json

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]

INVENTORY = ROOT / "processed_data" / "image_inventory.csv"

AUDIT = (
    ROOT
    / "processed_data"
    / "image_candidate_search"
    / "missing_source_photo_id_audit.csv"
)

OUT = (
    ROOT
    / "processed_data"
    / "image_candidate_search"
    / "missing_source_photo_id_review.html"
)


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def large_photo_url(url):
    if not url:
        return ""

    return (
        url
        .replace("/square.", "/large.")
        .replace("/small.", "/large.")
        .replace("/medium.", "/large.")
    )


def main():

    inventory = pd.read_csv(
        INVENTORY,
        dtype=str,
    )

    audit = pd.read_csv(
        AUDIT,
        dtype=str,
    )

    multi = audit[
        audit["status"] == "multiple_photos"
    ].copy()

    print("Multi-photo rows:", len(multi))

    if len(multi) == 0:
        print("No multi-photo rows found.")
        return

    obs_ids = (
        multi["observation_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    response = requests.get(
        "https://api.inaturalist.org/v1/observations",
        params={
            "id": ",".join(obs_ids),
            "per_page": 200,
        },
        timeout=30,
    )

    response.raise_for_status()

    results = response.json().get(
        "results",
        [],
    )

    lookup = {
        str(obs["id"]): obs
        for obs in results
    }

    records = []

    for _, audit_row in multi.iterrows():

        obs_id = clean(
            audit_row["observation_id"]
        )

        image_id = clean(
            audit_row["image_id"]
        )

        species = clean(
            audit_row["species"]
        )

        inv_match = inventory[
            inventory["image_id"]
            .fillna("")
            .str.strip()
            .eq(image_id)
        ]

        if len(inv_match) != 1:
            raise ValueError(
                f"Expected one inventory row for {image_id}, "
                f"found {len(inv_match)}"
            )

        inventory_license = clean(
            inv_match.iloc[0]["license"]
        )

        observation_url = clean(
            inv_match.iloc[0]["observation_url"]
        )

        obs = lookup.get(obs_id)

        if obs is None:
            raise ValueError(
                f"Observation {obs_id} not returned by API"
            )

        photos = []

        for photo in obs.get("photos", []):

            photo_id = clean(
                photo.get("id")
            )

            photo_license = clean(
                photo.get("license_code")
            )

            photo_url = large_photo_url(
                clean(
                    photo.get("url")
                )
            )

            attribution = clean(
                photo.get("attribution")
            )

            photos.append(
                {
                    "photo_id": photo_id,
                    "license": photo_license,
                    "url": photo_url,
                    "attribution": attribution,
                }
            )

        records.append(
            {
                "species": species,
                "image_id": image_id,
                "observation_id": obs_id,
                "observation_url": observation_url,
                "inventory_license": inventory_license,
                "photos": photos,
            }
        )

    payload = json.dumps(
        records,
        ensure_ascii=False,
    ).replace(
        "</",
        "<\\/",
    )

    html = r"""
<!doctype html>

<html>

<head>

<meta charset="utf-8">

<title>
Missing source photo ID review
</title>

<style>

body {
    font-family: Arial, sans-serif;
    margin: 25px;
    background: #f4f4f4;
    color: #222;
}

h1 {
    margin-bottom: 8px;
}

.notice {
    background: #fff3cd;
    border: 1px solid #e0c45a;
    border-radius: 8px;
    padding: 14px;
    margin: 18px 0;
    line-height: 1.5;
}

.toolbar {
    position: sticky;
    top: 0;
    z-index: 20;
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 25px;
}

.toolbar button {
    padding: 10px 15px;
    cursor: pointer;
}

.record {
    background: white;
    padding: 20px;
    margin: 28px 0;
    border-radius: 10px;
    box-shadow: 0 2px 7px #0002;
}

.photos {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    margin-top: 15px;
}

.photo-card {
    width: 320px;
    border: 3px solid transparent;
    border-radius: 10px;
    padding: 10px;
    background: #fafafa;
}

.photo-card.selected {
    border-color: #2e8b57;
    background: #edf8f1;
}

.photo-card img {
    width: 100%;
    max-height: 330px;
    object-fit: contain;
    background: #ddd;
}

.photo-card button {
    margin-top: 8px;
    padding: 8px 12px;
    cursor: pointer;
}

.meta {
    font-size: 0.93em;
    line-height: 1.45;
    margin-top: 8px;
}

.selected-text {
    font-weight: bold;
    margin-top: 10px;
}

a {
    color: #1666c5;
}

</style>

</head>


<body>

<h1>
Choose the correct iNaturalist photo
</h1>

<div class="notice">

These observations contain more than one photograph.

<br><br>

For each record, choose the exact photograph that was
originally screened for the dataset.

<br><br>

The existing <b>image_id</b> will not change.
This page only determines the missing
<b>source_photo_id</b>.

</div>


<div class="toolbar">

<span id="summary">
Selected: 0 / 8
</span>

&nbsp;&nbsp;

<button onclick="downloadCSV()">
Download selected photo IDs
</button>

</div>


<div id="content"></div>


<script>

const DATA = __PAYLOAD__;

const STORAGE_KEY =
    "nudibranch_missing_photo_ids_v1";

let selections = {};

try {

    selections =
        JSON.parse(
            localStorage.getItem(
                STORAGE_KEY
            )
        )
        || {};

}
catch (error) {

    selections = {};

}


function saveState() {

    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(
            selections
        )
    );

}


function choosePhoto(
    imageId,
    photoId
) {

    selections[
        imageId
    ] = photoId;

    saveState();

    render();

}


function escapeHTML(value) {

    return String(
        value ?? ""
    )
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

}


function render() {

    const root =
        document.getElementById(
            "content"
        );

    root.innerHTML = "";


    DATA.forEach(record => {

        const section =
            document.createElement(
                "div"
            );

        section.className =
            "record";


        const selected =
            selections[
                record.image_id
            ]
            || "";


        section.innerHTML = `

            <h2>
            ${escapeHTML(
                record.image_id
            )}
            </h2>

            <div>

            <b>Species:</b>
            ${escapeHTML(
                record.species
            )}

            <br>

            <b>Observation:</b>

            <a
            href="${escapeHTML(
                record.observation_url
            )}"
            target="_blank"
            >

            ${escapeHTML(
                record.observation_id
            )}

            </a>

            <br>

            <b>Licence recorded in inventory:</b>
            ${escapeHTML(
                record.inventory_license
            )}

            </div>

            <div class="selected-text">

            Selected Photo ID:
            ${
                selected
                ?
                escapeHTML(
                    selected
                )
                :
                "None"
            }

            </div>

            <div class="photos"></div>

        `;


        const photoArea =
            section.querySelector(
                ".photos"
            );


        record.photos.forEach(photo => {

            const card =
                document.createElement(
                    "div"
                );

            const isSelected =
                selected
                === photo.photo_id;


            card.className =
                "photo-card"
                +
                (
                    isSelected
                    ?
                    " selected"
                    :
                    ""
                );


            card.innerHTML = `

                <a
                href="${escapeHTML(
                    photo.url
                )}"
                target="_blank"
                >

                <img
                loading="lazy"
                src="${escapeHTML(
                    photo.url
                )}"
                >

                </a>

                <div class="meta">

                <b>Photo ID:</b>
                ${escapeHTML(
                    photo.photo_id
                )}

                <br>

                <b>Photo licence:</b>
                ${escapeHTML(
                    photo.license
                )}

                <br>

                ${escapeHTML(
                    photo.attribution
                )}

                </div>

            `;


            const button =
                document.createElement(
                    "button"
                );

            button.textContent =
                isSelected
                ?
                "SELECTED"
                :
                "SELECT THIS PHOTO";


            button.onclick =
                () =>
                    choosePhoto(
                        record.image_id,
                        photo.photo_id
                    );


            card.appendChild(
                button
            );

            photoArea.appendChild(
                card
            );

        });


        root.appendChild(
            section
        );

    });


    const nSelected =
        DATA.filter(
            record =>
                selections[
                    record.image_id
                ]
        ).length;


    document.getElementById(
        "summary"
    ).textContent =
        "Selected: "
        +
        nSelected
        +
        " / "
        +
        DATA.length;

}


function csvEscape(value) {

    const text =
        String(
            value ?? ""
        );

    if (
        /[",\r\n]/.test(
            text
        )
    ) {

        return (
            '"'
            +
            text.replaceAll(
                '"',
                '""'
            )
            +
            '"'
        );

    }

    return text;

}


function downloadCSV() {

    const missing =
        DATA.filter(
            record =>
                !selections[
                    record.image_id
                ]
        );

    if (
        missing.length
        > 0
    ) {

        alert(
            "Please select one photo for all "
            +
            DATA.length
            +
            " records first."
        );

        return;

    }


    const columns = [
        "species",
        "image_id",
        "observation_id",
        "source_photo_id"
    ];


    const lines = [
        columns.join(",")
    ];


    DATA.forEach(record => {

        const row = {
            species:
                record.species,

            image_id:
                record.image_id,

            observation_id:
                record.observation_id,

            source_photo_id:
                selections[
                    record.image_id
                ]
        };


        lines.push(
            columns
            .map(
                column =>
                    csvEscape(
                        row[column]
                    )
            )
            .join(",")
        );

    });


    const blob =
        new Blob(
            [
                "\uFEFF"
                +
                lines.join(
                    "\r\n"
                )
            ],
            {
                type:
                    "text/csv;charset=utf-8"
            }
        );


    const url =
        URL.createObjectURL(
            blob
        );


    const link =
        document.createElement(
            "a"
        );

    link.href = url;

    link.download =
        "selected_missing_source_photo_ids.csv";

    document.body.appendChild(
        link
    );

    link.click();

    link.remove();

    URL.revokeObjectURL(
        url
    );

}


render();

</script>


</body>

</html>
"""

    html = html.replace(
        "__PAYLOAD__",
        payload,
    )

    OUT.write_text(
        html,
        encoding="utf-8",
    )

    print()
    print("PHOTO REVIEW PAGE CREATED")
    print("Records:", len(records))
    print(
        "Saved to:",
        OUT.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()