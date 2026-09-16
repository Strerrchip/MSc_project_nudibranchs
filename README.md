# Colour pattern and chemical defence in dorid nudibranchs

This repository contains the analysis workflow developed for an MSc research project on warning coloration and chemical defence in dorid nudibranchs.

The project used citizen-science photographs from iNaturalist to investigate whether species-level colour-pattern traits are associated with toxicity and unpalatability. It also tested whether comparative visual signals can be recovered from multiple uncalibrated photographs collected under variable natural conditions.

## Project summary

The final dataset contained:

- 295 photographs
- 30 dorid nudibranch species
- Multiple photographs per species
- Species-level toxicity and unpalatability information from published datasets
- Image-level and species-level visual metrics

The main result was a positive relationship between toxicity strength and mean normalised pattern boldness. This agrees with previous controlled-image studies and suggests that uncalibrated citizen-science photographs can retain a useful species-level comparative signal.

The other planned relationships between chemical defence and visual traits were not clearly supported. These results help identify the limitations of the current sample and indicate where larger datasets, calibrated reference photographs and phylogenetic comparative analyses would be useful.

Measurements produced by this workflow are relative visual estimates. They should not be interpreted as calibrated reflectance measurements or predator-specific visual estimates.

## Analysis workflow

The main workflow consisted of the following stages:

1. Compile species, defence and image metadata.
2. Download and review candidate iNaturalist photographs.
3. Segment each nudibranch using MobileSAM.
4. Scale images using animal perimeter.
5. Define the animal mask and a 120-pixel surrounding background ring.
6. Extract image-level colour-pattern and visibility metrics.
7. Review failed or uncertain segmentations and perform manual rescue where necessary.
8. Aggregate measurements to species-level summaries.
9. Examine correlations among visual metrics.
10. Run principal component analysis and calculate mean normalised scores.
11. Test associations between visual traits, toxicity and unpalatability.
12. Validate the influence of background selection and image scaling.

## Repository structure

```text
MSc_project_nudibranchs/
├── scripts/
│   └── Formal Python scripts used for data preparation,
│       image analysis, validation and statistical analysis
├── processed_data/
│   ├── current_core/
│   │   └── Core species and chemical-defence tables
│   ├── automated_image_analysis/
│   │   └── Final image metrics, species summaries,
│   │       validation results and method figures
│   └── analysis/
│       └── Final statistical results and figures
├── requirements.txt
└── README.md
```

Raw photographs, model weights, papers, working notes, manuscript drafts and large intermediate image files are not included in the public repository.

## Software requirements

The analysis was developed using:

- Python 3.14.5
- Windows PowerShell
- Visual Studio Code

The Python package versions used in the final environment are recorded in `requirements.txt`.

To create a local environment on Windows:

```powershell
git clone https://github.com/Strerrchip/MSc_project_nudibranchs.git
cd MSc_project_nudibranchs

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## MobileSAM model

Image segmentation uses the MobileSAM model through the Ultralytics package.

Download the `mobile_sam.pt` model weights and place the file in the project root before running the segmentation scripts.

Official documentation:

https://docs.ultralytics.com/models/mobile-sam/

The model weights are not stored in this repository.

## Main scripts

The table below gives the principal analysis sequence. Some review and rescue stages require manual inspection, so the workflow is not intended to run as one completely unattended pipeline.

| Stage | Main scripts |
|---|---|
| Master data preparation | `build_master_table.py` |
| Defence data preparation | `prepare_d03_defence_data.py` |
| iNaturalist image inventory | `download_inaturalist_full_inventory.py` |
| Initial segmentation | `run_sam_scaled_ring120_formal.py` |
| Segmentation review | `build_formal_sam_qc_review.py` |
| Manual segmentation rescue | `rescue_sam_with_point_prompts.py` |
| Final scaled dataset | `build_final_scaled_ring120_dataset.py` |
| Image-level metric extraction | `extract_sam_scaled_ring120_metrics_final.py` |
| Visibility metric preparation | `prepare_visibility_metrics_final.py` |
| Image and species summaries | `summarise_visibility_metrics_final.py` |
| Metric correlation checks | `check_visibility_correlations.py` |
| Descriptive figures | `make_descriptive_visibility_figures.py` |
| Species heatmap | `make_species_visibility_heatmap.py` |
| Principal component analysis | `run_visibility_pca.py` |
| Normalised visibility scores | `build_normalised_visibility_scores.py` |
| Visual-defence analysis table | `build_visual_defence_analysis_table.py` |
| Continuous defence analysis | `analyse_continuous_defence_vs_pca.py` |
| Defence scatterplots | `plot_mean_normalised_scores_vs_defence.py` |
| Residual-species analysis | `identify_toxicity_boldness_residual_species.py` |
| Residual image collage | `make_toxicity_boldness_residual_collage.py` |
| Background comparison | `compare_van_background_metrics.py` |
| Standardised background comparison | `standardise_van_background_comparison.py` |
| Background validation analysis | `analyse_van_background_comparison.py` |
| Scaling validation | `summarise_final_scaling.py` |
| Manuscript scaling summary | `summarise_scaling_for_manuscript.py` |
| Segmentation methods figure | `make_segmentation_methods_figure.py` |

Additional scripts in `scripts/` support candidate-image searching, image review and the identification of missing photo IDs.

## Running the analysis

Scripts should be run from the project root. For example:

```powershell
python scripts/build_master_table.py
```

Many scripts depend on outputs produced during an earlier stage. File locations are defined using project-relative paths within the scripts.

The original analysis also used local raw images and working files that cannot be redistributed through this repository. The repository therefore contains the final analysis code and shareable derived results, but it is not a standalone copy of all third-party source material.

## Image data and attribution

Photographs were sourced from iNaturalist observations under the licence associated with each individual observation.

The repository does not redistribute the original full-resolution photographs. Image provenance, observation links, photographer information and licence information are recorded in the project image inventory and supplementary attribution table.

Copyright in each photograph remains with its original photographer. Anyone wishing to reuse a photograph should consult the corresponding iNaturalist observation and comply with its stated licence.

## Reproducibility and limitations

Several features of the dataset should be considered when interpreting or reproducing the analysis:

- Citizen-science photographs vary in camera settings, lighting, viewing angle, background and post-processing.
- The images do not contain consistent colour or scale standards.
- Visual measurements are comparative and relative rather than calibrated reflectance values.
- Automated segmentation was followed by quality control and manual rescue where required.
- Available toxicity and unpalatability data limited the number of species in some comparisons.
- Toxicity and unpalatability are related but biologically distinct aspects of chemical defence.
- Species were treated as statistically independent in the present analysis.
- A larger dataset with suitable phylogenetic coverage would allow phylogenetic generalised least-squares models to account for shared ancestry.

A useful future approach would compare the large citizen-science dataset with a smaller collection of calibrated reference photographs. This would help determine which visual metrics remain stable across calibrated and uncalibrated images.

## Key references

Prieto-Baños, S. and Layton, K. K. S. (2025). Tracing the evolution of key traits in dorid nudibranchs. *PLOS ONE*, 20(4), e0317704. https://doi.org/10.1371/journal.pone.0317704

van den Berg, C. P., Troscianko, J., Endler, J. A., Marshall, N. J. and Cheney, K. L. (2020). Quantitative Colour Pattern Analysis (QCPA): A comprehensive framework for the analysis of colour patterns in nature. *Methods in Ecology and Evolution*, 11(2), 316–332. https://doi.org/10.1111/2041-210X.13328

van den Berg, C. P., Endler, J. A. and Cheney, K. L. (2023). Signal detectability and boldness are not the same: The function of defensive coloration in nudibranchs is distance-dependent. *Proceedings of the Royal Society B: Biological Sciences*, 290(2003), 20231160. https://doi.org/10.1098/rspb.2023.1160

van den Berg, C. P., Santon, M., Endler, J. A. and Cheney, K. L. (2024). Highly defended nudibranchs ‘escape’ to visually distinct background habitats. *Behavioral Ecology*, 35(5), arae053. https://doi.org/10.1093/beheco/arae053

van den Berg, C. P., Santon, M., Endler, J. A., Drummond, L., Dawson, B. R., Santiago, C., Weber, N. and Cheney, K. L. (2024). Chemical defences indicate bold colour patterns with reduced variability in aposematic nudibranchs. *Proceedings of the Royal Society B: Biological Sciences*, 291(2027), 20240953. https://doi.org/10.1098/rspb.2024.0953

Zhang, C., Han, D., Qiao, Y., Kim, J. U., Bae, S.-H., Lee, S. and Hong, C. S. (2023). Faster Segment Anything: Towards lightweight SAM for mobile applications. *arXiv*. https://doi.org/10.48550/arXiv.2306.14289

## Author

Avery L. Chen  
MSc Computational Methods in Ecology and Evolution  
Imperial College London  
2026

## Repository status

This repository is an archived record of the final MSc project workflow. It is organised for transparency and reproducibility rather than maintained as a general-purpose software package.