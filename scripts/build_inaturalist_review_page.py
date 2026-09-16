from pathlib import Path
import json
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

CANDIDATES = (
    ROOT
    / "processed_data"
    / "image_candidate_search"
    / "inaturalist_auto_candidates.csv"
)

INVENTORY = (
    ROOT
    / "processed_data"
    / "image_inventory.csv"
)

OUT = (
    ROOT
    / "processed_data"
    / "image_candidate_search"
    / "inaturalist_candidate_review.html"
)

TARGET = 10


def txt(x):
    return "" if pd.isna(x) else str(x).strip()


def safe_species(s):
    return re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        s,
    ).strip("_")


def usable_count(inv, species):
    rows = inv[
        inv["species"]
        .fillna("")
        .str.strip()
        == species
    ]

    if rows.empty:
        return 0

    return int(
        rows["usable"]
        .fillna("")
        .str.strip()
        .str.lower()
        .eq("yes")
        .sum()
    )


def next_slot(inv, species):
    rows = inv[
        inv["species"]
        .fillna("")
        .str.strip()
        == species
    ]

    if rows.empty:
        return 1

    numeric = pd.to_numeric(
        rows["image_slot"],
        errors="coerce",
    ).dropna()

    if numeric.empty:
        return 1

    return int(numeric.max()) + 1


def main():

    candidates = pd.read_csv(
        CANDIDATES,
        dtype=str,
    )

    inventory = pd.read_csv(
        INVENTORY,
        dtype=str,
    )

    required = {
        "species",
        "observation_id",
        "observation_url",
        "license",
        "photographer_or_observer",
        "date_accessed",
        "capture_time",
        "source_photo_id",
        "photo_url_medium",
        "photo_url_large",
    }

    missing = (
        required
        - set(candidates.columns)
    )

    if missing:
        raise ValueError(
            "Missing candidate columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    candidates = candidates.copy()

    # Candidate numbering is temporary.
    candidates["candidate_number"] = (
        candidates
        .groupby(
            "species",
            sort=False,
        )
        .cumcount()
        + 1
    )

    species_order = list(
        dict.fromkeys(
            candidates[
                "species"
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )
    )

    records = []

    for species in species_order:

        current_usable = usable_count(
            inventory,
            species,
        )

        selection_limit = max(
            0,
            TARGET - current_usable,
        )

        base_slot = next_slot(
            inventory,
            species,
        )

        species_rows = candidates[
            candidates["species"]
            == species
        ]

        for _, row in species_rows.iterrows():

            records.append(
                {
                    "species":
                        species,

                    "safe_species":
                        safe_species(
                            species
                        ),

                    "candidate_number":
                        int(
                            row[
                                "candidate_number"
                            ]
                        ),

                    "selection_limit":
                        selection_limit,

                    "base_image_slot":
                        base_slot,

                    "observation_id":
                        txt(
                            row[
                                "observation_id"
                            ]
                        ),

                    "observation_url":
                        txt(
                            row[
                                "observation_url"
                            ]
                        ),

                    "license":
                        txt(
                            row["license"]
                        ),

                    "photographer_or_observer":
                        txt(
                            row[
                                "photographer_or_observer"
                            ]
                        ),

                    "date_accessed":
                        txt(
                            row[
                                "date_accessed"
                            ]
                        ),

                    "capture_time":
                        txt(
                            row[
                                "capture_time"
                            ]
                        ),

                    "source_photo_id":
                        txt(
                            row[
                                "source_photo_id"
                            ]
                        ),

                    "photo_url_medium":
                        txt(
                            row[
                                "photo_url_medium"
                            ]
                        ),

                    "photo_url_large":
                        txt(
                            row[
                                "photo_url_large"
                            ]
                        ),
                }
            )

    payload = json.dumps(
        {
            "records": records,
            "species_order":
                species_order,
        },
        ensure_ascii=False,
    ).replace(
        "</",
        "<\\/",
    )

    page = r'''<!doctype html>

<html>

<head>

<meta charset="utf-8">

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

.notice,
.toolbar {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 9px;
    padding: 14px;
    margin-bottom: 18px;
}

.notice {
    background: #fff3cd;
    border-color: #e6c75a;
    line-height: 1.5;
}

.toolbar {
    position: sticky;
    top: 0;
    z-index: 20;
}

.toolbar button,
.card button {
    padding: 9px 14px;
    margin: 5px 8px 5px 0;
    cursor: pointer;
}

.section {
    margin-top: 42px;
}

.section h2 {
    border-bottom: 2px solid #444;
    padding-bottom: 8px;
}

.count {
    font-weight: bold;
    margin-bottom: 10px;
}

.card {
    background: #fff;
    border: 3px solid transparent;
    border-radius: 12px;
    padding: 18px;
    margin: 18px 0;
    box-shadow: 0 2px 8px #0002;
}

.card.keep {
    border-color: #2e8b57;
}

.card.reject {
    border-color: #b94a48;
    opacity: 0.65;
}

.card.hidden {
    display: none;
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

.status {
    font-weight: bold;
    margin-top: 8px;
}

.small {
    color: #555;
    font-size: 0.92em;
}

a {
    color: #1666c5;
}

</style>

</head>


<body>


<h1>
iNaturalist candidate review
</h1>


<div class="notice">

<b>
Candidate numbers are temporary.
</b>

<br>

Final <code>imgXX</code> numbers are created
only when KEEP images are exported.

<br><br>

For example, if Candidate 03 is rejected
but Candidate 11 is kept,
Candidate 11 will automatically move forward
in the final numbering.

There will be no gap caused by Candidate 03.

</div>


<div class="toolbar">

<div id="summary"></div>

<button onclick="downloadCSV()">
Download selected inventory CSV
</button>

<button onclick="downloadTXT()">
Download selected TXT
</button>

<button onclick="copyTXT()">
Copy selected records
</button>

<button onclick="toggleRejected()">
Hide / show rejected
</button>

<button onclick="clearAll()">
Clear all selections
</button>

</div>


<div id="content"></div>


<script>


const DATA = __PAYLOAD__;


const KEY =
    "nudibranch_inaturalist_review_v3";


const COLS = [

    "species",

    "image_slot",

    "image_id",

    "analysis_stage",

    "source",

    "observation_id",

    "observation_url",

    "license",

    "photographer_or_observer",

    "date_accessed",

    "source_metadata_status",

    "original_image_path",

    "original_width",

    "original_height",

    "image_downloaded",

    "usable",

    "exclusion_reason",

    "animal_clear",

    "background_clear",

    "segmentation_status",

    "segmentation_qc",

    "metrics_status",

    "notes",

    "source_photo_id"

];


let state = {};

let hideRejected = false;


try {

    state =
        JSON.parse(
            localStorage.getItem(
                KEY
            )
        )
        || {};

}
catch(error) {

    state = {};

}


function bySpecies(species) {

    return DATA.records.filter(
        record =>
            record.species
            === species
    );

}


function limitFor(species) {

    const records =
        bySpecies(
            species
        );

    if (!records.length) {

        return 0;

    }

    return Number(
        records[0]
            .selection_limit
    );

}


function keepCount(species) {

    return bySpecies(
        species
    ).filter(

        record =>
            state[
                record.observation_id
            ]
            === "keep"

    ).length;

}


function saveState() {

    localStorage.setItem(
        KEY,
        JSON.stringify(
            state
        )
    );

}


function setStatus(
    observationId,
    species,
    status
) {

    const current =
        state[
            observationId
        ]
        || "";

    if (
        status === "keep"
        &&
        current !== "keep"
        &&
        keepCount(
            species
        )
        >=
        limitFor(
            species
        )
    ) {

        alert(
            "This species already has "
            +
            limitFor(
                species
            )
            +
            " selected images."
        );

        return;

    }


    if (
        current
        === status
    ) {

        delete state[
            observationId
        ];

    }
    else {

        state[
            observationId
        ]
        =
        status;

    }


    saveState();

    render();

}


function clearAll() {

    if (
        !confirm(
            "Clear all KEEP / REJECT selections?"
        )
    ) {

        return;

    }

    state = {};

    saveState();

    render();

}


function toggleRejected() {

    hideRejected =
        !hideRejected;

    render();

}


function escapeHTML(value) {

    return String(
        value ?? ""
    )
    .replaceAll(
        "&",
        "&amp;"
    )
    .replaceAll(
        "<",
        "&lt;"
    )
    .replaceAll(
        ">",
        "&gt;"
    )
    .replaceAll(
        '"',
        "&quot;"
    )
    .replaceAll(
        "'",
        "&#039;"
    );

}


function selectedRecords() {

    const output = [];


    DATA.species_order.forEach(

        species => {

            const selected =

                bySpecies(
                    species
                )

                .filter(

                    record =>
                        state[
                            record.observation_id
                        ]
                        === "keep"

                )

                .sort(

                    (a, b) =>
                        a.candidate_number
                        -
                        b.candidate_number

                );


            if (
                !selected.length
            ) {

                return;

            }


            const baseSlot =

                Number(
                    selected[0]
                        .base_image_slot
                );


            selected.forEach(

                (record, index) => {

                    const slot =
                        baseSlot
                        +
                        index;


                    const imageId =

                        record.safe_species
                        +
                        "_img"
                        +
                        String(
                            slot
                        )
                        .padStart(
                            2,
                            "0"
                        );


                    output.push(
                        {

                            species:
                                record.species,

                            image_slot:
                                slot,

                            image_id:
                                imageId,

                            analysis_stage:
                                "candidate",

                            source:
                                "iNaturalist",

                            observation_id:
                                record.observation_id,

                            observation_url:
                                record.observation_url,

                            license:
                                record.license,

                            photographer_or_observer:
                                record.photographer_or_observer,

                            date_accessed:
                                record.date_accessed,

                            source_metadata_status:
                                "matched",

                            original_image_path:
                                "",

                            original_width:
                                "",

                            original_height:
                                "",

                            image_downloaded:
                                "no",

                            usable:
                                "yes",

                            exclusion_reason:
                                "",

                            animal_clear:
                                "yes",

                            background_clear:
                                "yes",

                            segmentation_status:
                                "not_started",

                            segmentation_qc:
                                "not_reviewed",

                            metrics_status:
                                "not_started",

                            notes:
                                "Research grade; "
                                +
                                "whole animal clear and fully visible; "
                                +
                                "colour pattern visible; "
                                +
                                "natural background clear",

                            source_photo_id:
                                record.source_photo_id

                        }
                    );

                }

            );

        }

    );


    return output;

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


function saveFile(
    text,
    name,
    type
) {

    const blob =

        new Blob(
            [text],
            {
                type:
                    type
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


    link.href =
        url;

    link.download =
        name;


    document.body
        .appendChild(
            link
        );


    link.click();

    link.remove();


    URL.revokeObjectURL(
        url
    );

}


function downloadCSV() {

    const rows =
        selectedRecords();


    if (
        !rows.length
    ) {

        alert(
            "No photographs are marked KEEP."
        );

        return;

    }


    const lines = [

        COLS.join(
            ","
        )

    ];


    rows.forEach(

        record => {

            lines.push(

                COLS.map(

                    column =>
                        csvEscape(
                            record[
                                column
                            ]
                        )

                )
                .join(
                    ","
                )

            );

        }

    );


    saveFile(

        "\uFEFF"
        +
        lines.join(
            "\r\n"
        ),

        "selected_inaturalist_records.csv",

        "text/csv;charset=utf-8"

    );

}


function blocks() {

    return selectedRecords()

        .map(

            record => [

                "species: "
                +
                record.species,

                "image_slot: "
                +
                record.image_slot,

                "image_id: "
                +
                record.image_id,

                "analysis_stage: candidate",

                "source: iNaturalist",

                "observation_id: "
                +
                record.observation_id,

                "observation_url: "
                +
                record.observation_url,

                "license: "
                +
                record.license,

                "photographer_or_observer: "
                +
                record.photographer_or_observer,

                "date_accessed: "
                +
                record.date_accessed,

                "usable: yes",

                "exclusion_reason:",

                "animal_clear: yes",

                "background_clear: yes",

                "notes: "
                +
                record.notes

            ]
            .join(
                "\n"
            )

        )

        .join(

            "\n\n"
            +
            "=".repeat(
                80
            )
            +
            "\n\n"

        );

}


function downloadTXT() {

    const text =
        blocks();


    if (
        !text
    ) {

        alert(
            "No photographs are marked KEEP."
        );

        return;

    }


    saveFile(

        text,

        "selected_inaturalist_records.txt",

        "text/plain;charset=utf-8"

    );

}


function copyTXT() {

    const text =
        blocks();


    if (
        !text
    ) {

        alert(
            "No photographs are marked KEEP."
        );

        return;

    }


    navigator.clipboard

        .writeText(
            text
        )

        .then(

            () =>
                alert(
                    "Selected records copied."
                )

        )

        .catch(

            () =>
                alert(
                    "Clipboard failed. "
                    +
                    "Use Download selected TXT."
                )

        );

}


function makeCard(record) {

    const status =

        state[
            record.observation_id
        ]
        || "";


    const card =

        document.createElement(
            "div"
        );


    card.className =

        "card"
        +
        (
            status
            ?
            " " + status
            :
            ""
        )
        +
        (
            hideRejected
            &&
            status === "reject"
            ?
            " hidden"
            :
            ""
        );


    card.innerHTML = `

        <h3>
        Candidate ${String(
            record.candidate_number
        ).padStart(2, "0")}
        </h3>

        <a
        href="${escapeHTML(
            record.photo_url_large
        )}"
        target="_blank"
        >

        <img
        class="photo"
        loading="lazy"
        src="${escapeHTML(
            record.photo_url_medium
        )}"
        >

        </a>

        <div class="meta">

        <b>Author:</b>
        ${escapeHTML(
            record.photographer_or_observer
        )}
        <br>

        <b>Capture time:</b>
        ${escapeHTML(
            record.capture_time
        )}
        <br>

        <b>Licence:</b>
        ${escapeHTML(
            record.license
        )}
        <br>

        <b>Photo ID:</b>
        ${escapeHTML(
            record.source_photo_id
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
            record.observation_url
        )}

        </a>

        </div>

        <p>

        <b>Visual check:</b>

        whole animal clear?
        colour pattern visible?
        enough natural background for the
        immediate-background ring?

        </p>

        <div class="buttons"></div>

        <div class="status">

        Status:
        ${
            status
            ?
            status.toUpperCase()
            :
            "not reviewed"
        }

        </div>

    `;


    const buttons =

        card.querySelector(
            ".buttons"
        );


    const keep =

        document.createElement(
            "button"
        );


    keep.textContent =
        "KEEP";


    keep.onclick =

        () =>
            setStatus(
                record.observation_id,
                record.species,
                "keep"
            );


    const reject =

        document.createElement(
            "button"
        );


    reject.textContent =
        "REJECT";


    reject.onclick =

        () =>
            setStatus(
                record.observation_id,
                record.species,
                "reject"
            );


    buttons.appendChild(
        keep
    );

    buttons.appendChild(
        reject
    );


    return card;

}


function render() {

    const root =

        document.getElementById(
            "content"
        );


    root.innerHTML =
        "";


    DATA.species_order.forEach(

        species => {

            const records =
                bySpecies(
                    species
                );


            const section =

                document.createElement(
                    "section"
                );


            section.className =
                "section";


            const heading =

                document.createElement(
                    "h2"
                );


            heading.textContent =

                species
                +
                " ("
                +
                records.length
                +
                " candidates)";


            section.appendChild(
                heading
            );


            const count =

                document.createElement(
                    "div"
                );


            count.className =
                "count";


            count.textContent =

                "Selected: "
                +
                keepCount(
                    species
                )
                +
                " / "
                +
                limitFor(
                    species
                );


            section.appendChild(
                count
            );


            const note =

                document.createElement(
                    "div"
                );


            note.className =
                "small";


            note.textContent =

                "Final imgXX numbers are assigned "
                +
                "only after export.";


            section.appendChild(
                note
            );


            records.forEach(

                record => {

                    section.appendChild(
                        makeCard(
                            record
                        )
                    );

                }

            );


            root.appendChild(
                section
            );

        }

    );


    const keep =

        DATA.records.filter(

            record =>
                state[
                    record.observation_id
                ]
                === "keep"

        ).length;


    const reject =

        DATA.records.filter(

            record =>
                state[
                    record.observation_id
                ]
                === "reject"

        ).length;


    document.getElementById(
        "summary"
    ).textContent =

        "KEEP: "
        +
        keep
        +
        " | REJECT: "
        +
        reject
        +
        " | Not reviewed: "
        +
        (
            DATA.records.length
            -
            keep
            -
            reject
        );

}


render();


</script>


</body>

</html>
'''.replace(
        "__PAYLOAD__",
        payload,
    )


    OUT.write_text(
        page,
        encoding="utf-8",
    )


    print(
        "REVIEW PAGE UPDATED"
    )

    print(
        "Candidate rows:",
        len(records),
    )

    print(
        "Species:",
        len(species_order),
    )

    print(
        "Saved to:",
        OUT.relative_to(
            ROOT
        ),
    )


if __name__ == "__main__":
    main()