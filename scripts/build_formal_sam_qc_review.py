from pathlib import Path
import json
import os
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUMMARY_CSV = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "validation"
    / "sam_scaled_ring120_formal_full_summary.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "processed_data"
    / "automated_image_analysis"
    / "qc_review"
)

OUTPUT_HTML = OUTPUT_DIR / "formal_sam_qc_review.html"


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def resolve_project_path(path_value):
    path = Path(clean_text(path_value))
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def make_relative_url(target_path, html_path):
    target_path = Path(target_path).resolve()
    html_dir = html_path.parent.resolve()
    return Path(os.path.relpath(target_path, start=html_dir)).as_posix()


def main():
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(
            f"Cannot find formal SAM summary: {SUMMARY_CSV}"
        )

    summary_df = pd.read_csv(
        SUMMARY_CSV,
        dtype=str,
        keep_default_na=False,
    )

    required_columns = [
        "species",
        "image_slot",
        "image_id",
        "qc_output_path",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in summary_df.columns
    ]

    if missing_columns:
        raise KeyError(
            "Formal SAM summary is missing: "
            + ", ".join(missing_columns)
        )

    summary_df = summary_df.sort_values(
        ["species", "image_slot", "image_id"]
    ).reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    missing_qc = []

    for _, row in summary_df.iterrows():
        qc_path = resolve_project_path(row["qc_output_path"])

        if not qc_path.exists():
            missing_qc.append(clean_text(row["image_id"]))

        records.append(
            {
                "species": clean_text(row["species"]),
                "image_slot": clean_text(row["image_slot"]),
                "image_id": clean_text(row["image_id"]),
                "qc_url": make_relative_url(
                    qc_path,
                    OUTPUT_HTML,
                ),
            }
        )

    records_json = json.dumps(
        records,
        ensure_ascii=False,
    )

    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Formal SAM QC Review</title>
<style>
body { margin:0; font-family:Arial,Helvetica,sans-serif; background:#111; color:#eee; }
header { position:sticky; top:0; z-index:10; background:#181818; border-bottom:1px solid #333; padding:12px 16px; }
.top { display:flex; flex-wrap:wrap; gap:12px; justify-content:space-between; align-items:center; }
.title { font-size:20px; font-weight:700; }
.controls { margin-top:10px; display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
button, select { font:inherit; padding:8px 12px; border-radius:7px; border:1px solid #555; background:#262626; color:#eee; cursor:pointer; }
main { max-width:1500px; margin:0 auto; padding:18px; }
.card { background:#1a1a1a; border:2px solid #333; border-radius:10px; overflow:hidden; }
.card.keep { border-color:#22c55e; }
.card.reject { border-color:#ef4444; }
.meta { display:flex; flex-wrap:wrap; gap:12px; padding:12px 14px; border-bottom:1px solid #333; align-items:baseline; }
.species { font-size:18px; font-weight:700; }
.imageid { font-family:Consolas,monospace; font-size:13px; opacity:.85; }
.figure { display:flex; justify-content:center; align-items:center; min-height:360px; background:#0d0d0d; padding:10px; }
img { display:block; max-width:100%; max-height:72vh; object-fit:contain; }
.decisions { display:flex; gap:10px; padding:12px; border-top:1px solid #333; }
.decisions button { flex:1; font-size:17px; font-weight:700; padding:12px; }
.keepbtn { border-color:#22c55e; }
.rejectbtn { border-color:#ef4444; }
.activekeep { background:#166534; }
.activereject { background:#7f1d1d; }
.nav { margin-top:14px; display:flex; justify-content:space-between; gap:10px; }
.small { font-size:12px; opacity:.75; }
.empty { padding:40px; text-align:center; }
</style>
</head>
<body>
<header>
  <div class="top">
    <div class="title">Formal SAM QC Review</div>
    <div id="stats"></div>
  </div>
  <div class="controls">
    <label>Species: <select id="speciesFilter"></select></label>
    <label>Show:
      <select id="statusFilter">
        <option value="all">All</option>
        <option value="unreviewed">Unreviewed</option>
        <option value="keep">KEEP</option>
        <option value="reject">REJECT</option>
      </select>
    </label>
    <button id="exportBtn">Export CSV</button>
    <button id="clearBtn">Clear all decisions</button>
    <span class="small">K = KEEP, R = REJECT, ← / → = previous / next</span>
  </div>
</header>
<main><div id="reviewArea"></div></main>

<script>
const records = __RECORDS__;
const STORAGE_KEY = "formal_sam_qc_review_v1";
let decisions = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
let visibleIndices = [];
let currentVisiblePosition = 0;

const reviewArea = document.getElementById("reviewArea");
const stats = document.getElementById("stats");
const speciesFilter = document.getElementById("speciesFilter");
const statusFilter = document.getElementById("statusFilter");

function saveDecisions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
}

function getDecision(imageId) {
  return decisions[imageId] || "";
}

function updateStats() {
  let keep = 0;
  let reject = 0;
  for (const record of records) {
    const d = getDecision(record.image_id);
    if (d === "KEEP") keep++;
    if (d === "REJECT") reject++;
  }
  const reviewed = keep + reject;
  stats.textContent =
    `Total: ${records.length} | KEEP: ${keep} | REJECT: ${reject} | Unreviewed: ${records.length - reviewed}`;
}

function buildSpeciesFilter() {
  speciesFilter.innerHTML = "";
  const all = document.createElement("option");
  all.value = "all";
  all.textContent = "All species";
  speciesFilter.appendChild(all);

  const species = [...new Set(records.map(r => r.species))].sort();
  for (const name of species) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    speciesFilter.appendChild(option);
  }
}

function matches(record) {
  const speciesOk =
    speciesFilter.value === "all" ||
    record.species === speciesFilter.value;

  const d = getDecision(record.image_id);
  let statusOk = true;

  if (statusFilter.value === "unreviewed") statusOk = d === "";
  if (statusFilter.value === "keep") statusOk = d === "KEEP";
  if (statusFilter.value === "reject") statusOk = d === "REJECT";

  return speciesOk && statusOk;
}

function rebuild() {
  visibleIndices = [];
  for (let i = 0; i < records.length; i++) {
    if (matches(records[i])) visibleIndices.push(i);
  }
  currentVisiblePosition = 0;
  render();
}

function setDecision(value) {
  if (visibleIndices.length === 0) return;

  const record = records[visibleIndices[currentVisiblePosition]];
  decisions[record.image_id] = value;
  saveDecisions();
  updateStats();

  if (statusFilter.value === "unreviewed") {
    rebuild();
    return;
  }

  if (currentVisiblePosition < visibleIndices.length - 1) {
    currentVisiblePosition++;
  }
  render();
}

function render() {
  reviewArea.innerHTML = "";

  if (visibleIndices.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No images match the current filters.";
    reviewArea.appendChild(empty);
    return;
  }

  const record = records[visibleIndices[currentVisiblePosition]];
  const d = getDecision(record.image_id);

  const card = document.createElement("div");
  card.className = "card";
  if (d === "KEEP") card.classList.add("keep");
  if (d === "REJECT") card.classList.add("reject");

  const meta = document.createElement("div");
  meta.className = "meta";

  const species = document.createElement("div");
  species.className = "species";
  species.textContent = record.species;

  const imageId = document.createElement("div");
  imageId.className = "imageid";
  imageId.textContent =
    `${record.image_id} (${currentVisiblePosition + 1} / ${visibleIndices.length})`;

  meta.appendChild(species);
  meta.appendChild(imageId);

  const figure = document.createElement("div");
  figure.className = "figure";

  const img = document.createElement("img");
  img.src = record.qc_url;
  img.alt = record.image_id;
  figure.appendChild(img);

  const decisionsRow = document.createElement("div");
  decisionsRow.className = "decisions";

  const keepBtn = document.createElement("button");
  keepBtn.className = "keepbtn";
  keepBtn.textContent = "KEEP";
  if (d === "KEEP") keepBtn.classList.add("activekeep");
  keepBtn.onclick = () => setDecision("KEEP");

  const rejectBtn = document.createElement("button");
  rejectBtn.className = "rejectbtn";
  rejectBtn.textContent = "REJECT";
  if (d === "REJECT") rejectBtn.classList.add("activereject");
  rejectBtn.onclick = () => setDecision("REJECT");

  decisionsRow.appendChild(keepBtn);
  decisionsRow.appendChild(rejectBtn);

  const nav = document.createElement("div");
  nav.className = "nav";

  const prev = document.createElement("button");
  prev.textContent = "← Previous";
  prev.disabled = currentVisiblePosition === 0;
  prev.onclick = () => {
    if (currentVisiblePosition > 0) {
      currentVisiblePosition--;
      render();
    }
  };

  const next = document.createElement("button");
  next.textContent = "Next →";
  next.disabled = currentVisiblePosition === visibleIndices.length - 1;
  next.onclick = () => {
    if (currentVisiblePosition < visibleIndices.length - 1) {
      currentVisiblePosition++;
      render();
    }
  };

  nav.appendChild(prev);
  nav.appendChild(next);

  card.appendChild(meta);
  card.appendChild(figure);
  card.appendChild(decisionsRow);

  reviewArea.appendChild(card);
  reviewArea.appendChild(nav);
}

function exportCsv() {
  const rows = [
    ["species", "image_slot", "image_id", "segmentation_qc"]
  ];

  for (const record of records) {
    rows.push([
      record.species,
      record.image_slot,
      record.image_id,
      getDecision(record.image_id)
    ]);
  }

  const csv = rows
    .map(row =>
      row.map(value =>
        '"' + String(value).replaceAll('"', '""') + '"'
      ).join(",")
    )
    .join("\n");

  const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "formal_sam_qc_decisions.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

speciesFilter.onchange = rebuild;
statusFilter.onchange = rebuild;
document.getElementById("exportBtn").onclick = exportCsv;

document.getElementById("clearBtn").onclick = () => {
  if (!confirm("Clear all KEEP / REJECT decisions?")) return;
  decisions = {};
  saveDecisions();
  updateStats();
  rebuild();
};

document.addEventListener("keydown", event => {
  if (event.key === "k" || event.key === "K") setDecision("KEEP");
  if (event.key === "r" || event.key === "R") setDecision("REJECT");

  if (event.key === "ArrowRight" && currentVisiblePosition < visibleIndices.length - 1) {
    currentVisiblePosition++;
    render();
  }

  if (event.key === "ArrowLeft" && currentVisiblePosition > 0) {
    currentVisiblePosition--;
    render();
  }
});

buildSpeciesFilter();
updateStats();
rebuild();
</script>
</body>
</html>
"""

    html = html.replace("__RECORDS__", records_json)

    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print("=" * 72)
    print("FORMAL SAM QC REVIEW PAGE CREATED")
    print("=" * 72)
    print(f"QC rows: {len(records)}")
    print(f"Species: {summary_df['species'].nunique()}")
    print(f"Missing QC figures: {len(missing_qc)}")
    print()
    print("Saved to:")
    print(OUTPUT_HTML.relative_to(PROJECT_ROOT).as_posix())
    print()
    print("Open the HTML file in a browser.")
    print("Use KEEP / REJECT or keyboard shortcuts K / R.")
    print("When finished, click Export CSV.")


if __name__ == "__main__":
    main()
