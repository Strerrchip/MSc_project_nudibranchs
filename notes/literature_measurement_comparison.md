# Measurement notes from previous studies

## D04 – Chemical defences indicate bold colour patterns with reduced variability in aposematic nudibranchs

Paper: van den Berg et al. (2024)

This paper used QCPA to measure the internal colour patterns of nudibranchs. The animal was separated from the background before the measurements were taken.

The paper first produced 157 colour-pattern measurements. It then removed strongly correlated measurements and kept 15 measurements for the factor analysis.

The measurements ending in `hrz` were calculated in the horizontal direction. The measurements ending in `vrt` were calculated in the vertical direction. The animals were rotated into a similar head-up position before analysis.

An important difference is that the D04 measurements mainly describe patterns within the animal. They do not measure the contrast between the animal and its surrounding habitat. My workflow currently includes both animal-only measurements and animal-background measurements.

| Analysis | Metric in D04 | Full name | What does it measure? | Similar metric in my workflow | How similar are they? | Possible use in my project | Notes |
|----------|---------------|-----------|-----------------------|-------------------------------|-----------------------|----------------------------|-------|
| CAA | CAA.Asp | Pattern aspect ratio | Whether colour patches are mainly horizontal, vertical or not strongly directional | Not implemented | No current equivalent | Not a priority at the moment | Online images show animals in different positions and body shapes. This measurement would need all animals to be aligned in the same direction. |
| CAA | CAA.PT | Average patch size | The average size of colour patches within the animal | Not implemented | No current equivalent | Consider later | This could describe whether an animal has many small markings or a few large colour patches. It would require the animal image to be divided into separate colour patches. |
| CAA | CAA.Qc.Vrt | Relative Shannon colour diversity | How evenly different colours cover the animal, while controlling for the number of colours | Not implemented | No current equivalent | Consider later | This may be useful for comparing animals with one dominant colour against animals with several evenly represented colours. It requires colour clustering. |
| CAA | CAA.Qt | Relative Shannon transition diversity | How evenly and regularly different colours change from one patch to another | Not implemented | No current equivalent | Consider later | This describes pattern arrangement rather than the amount of colour contrast. It requires colour clustering and may also be affected by animal orientation. |
| VCA | VCA.ML.Hrz | Weighted mean pattern luminance | The average luminance of colour patches, weighted by the area of each patch | `animal_brightness_mean` | Similar general idea, but not the same calculation | Keep the current simpler measurement | My measurement uses all animal pixels directly. D04 first divided the animal into colour patches and used a predator visual model. |
| VCA | VCA.CVL.Hrz | Coefficient of variation of pattern luminance | Luminance variation relative to the mean luminance of the animal pattern | Can be calculated from `animal_brightness_mean` and `animal_brightness_sd` | A simple RGB-image version is possible | Add a simple version | I can calculate `animal_brightness_cv` as brightness standard deviation divided by brightness mean. |
| VCA | VCA.MDmax.Vrt | Weighted mean Dmax chromatic contrast | How far the animal's colour patches are from an achromatic grey point | Closest: `animal_saturation_mean` | Only a rough equivalent | Keep the current simpler measurement | D04 used a triggerfish visual model. My saturation measurement is based on HSV values from ordinary online images. |
| VCA | VCA.MSL.Vrt | Weighted mean RNL luminance pattern contrast | The average luminance difference between different colour patches within the animal | Closest: `animal_brightness_sd` | Related, but not equivalent | Consider later | My current measurement describes overall pixel variation. D04 measured pairwise differences between clustered colour patches. |
| VCA | VCA.CVSL.Hrz | Coefficient of variation of RNL luminance pattern contrast | How variable the luminance differences are between different colour patches | Not implemented | No exact equivalent | Consider later | This would need colour-patch clustering followed by pairwise brightness comparisons. |
| VCA | VCA.CVS.Hrz | Coefficient of variation of RNL chromatic pattern contrast | How variable the colour differences are between colour patches within the animal | Closest: `animal_saturation_sd` | Only a rough equivalent | Add a simple colour-variation measure | A simple `animal_saturation_cv` could be calculated, but it would not reproduce the predator-specific RNL measurement. |
| BSA | BSA.BMSL.Vrt | Weighted mean RNL luminance boundary strength | The average luminance difference across the boundaries between colour patches | Closest: `animal_edge_density` | They measure different parts of the pattern | Add a simple edge-strength measurement | `animal_edge_density` counts how many edges are present. It does not measure how strong the brightness change is across those edges. |
| BSA | BSA.BCVDmax.Vrt | Coefficient of variation of Dmax boundary strength | How variable the chromatic contrast is across different colour-patch boundaries | Not implemented | No current equivalent | Consider later | A simple version could measure variation in Lab colour difference across detected edges, but this may be sensitive to image quality. |
| LEIA | Col.kurtosis.hrz | Kurtosis of chromatic edge contrast | The shape of the distribution of colour-edge strengths within the animal | Not implemented | No current equivalent | Not a priority for the first analysis | This is harder to explain biologically and may be strongly affected by the quality and compression of online images. |
| LEIA | Lum.kurtosis.hrz | Kurtosis of luminance edge contrast | The shape of the distribution of brightness-edge strengths within the animal | Not implemented | No current equivalent | Not a priority for the first analysis | This may distinguish patterns with mostly similar edges from patterns containing a small number of very strong edges. |
| LEIA | Lum.mean.vrt | Mean luminance edge intensity | The average strength of local brightness edges within the animal | Closest: `animal_edge_density` | Related, but not equivalent | Add a simple version | A useful addition would be `animal_mean_edge_strength`, calculated from brightness-gradient strength inside the animal mask. |

## Main points from D04

D04 used calibrated photographs and modelled the images using the visual system of a triggerfish. It also controlled for viewing distance and predator visual acuity.

My project uses online citizen-science images. These images were taken with different cameras, lighting conditions and settings. This means that I cannot reproduce the predator-specific QCPA measurements exactly.

The D04 measurements mainly describe the colour and pattern within the animal. My project also measures animal-background contrast, which is not the main focus of the D04 measurements.

The main measurement groups in my project are therefore:

### Animal-background measurements already in the workflow

- `gray_contrast`
- `brightness_contrast`
- `saturation_contrast`
- `lab_colour_distance`

These measurements describe how different the animal is from the surrounding 120 px background ring.

### Animal-only measurements already in the workflow

- `animal_brightness_mean`
- `animal_saturation_mean`
- `animal_brightness_sd`
- `animal_saturation_sd`
- `animal_gray_sd`
- `animal_edge_density`

These measurements describe the colour and pattern variation within the animal mask.

### Simple measurements that could be added

- `animal_brightness_cv`
- `animal_saturation_cv`
- `animal_mean_edge_strength`
- `animal_edge_strength_sd`

Brightness and saturation coefficients of variation would describe variation relative to the mean value. Mean edge strength would measure how strong the internal pattern boundaries are, rather than only counting the number of edges.

### Measurements to consider later

- average colour-patch size
- colour-patch evenness
- colour-transition regularity
- internal colour differences between clustered patches

These measurements would require a second colour-clustering step within the animal mask. I should only add them if the clustering works consistently across online images.

## Current conclusion

D04 shows that colour pattern boldness is not represented by one measurement. It includes luminance contrast, chromatic contrast, boundary strength, patch geometry and pattern regularity.

My current workflow already covers animal-background contrast and some simple animal-only variation. The clearest possible additions are brightness CV, saturation CV and mean edge strength.

Patch-based measurements could provide more information about pattern geometry, but they would add another processing step and may be less reliable with online images. I should test a simple colour-clustering method before deciding whether to include them.

---

## D05 – Signal detectability and boldness are not the same: the function of defensive coloration in nudibranchs is distance-dependent

Paper: van den Berg, Endler and Cheney (2023)

This paper separates detectability from boldness.

Detectability describes how different the animal's local edge-contrast pattern is from its immediate background. Boldness describes the strength and variation of local edge contrast within the animal itself.

The study analysed calibrated photographs of 226 individuals from 13 dorid nudibranch species. The images were modelled using the visual system of a triggerfish at viewing distances of 2, 5, 10 and 30 cm.

The study used Local Edge Intensity Analysis (LEIA) to measure local achromatic and chromatic edge contrast. The main statistics were Lum.CoV and Col.CoV.

| Measurement | Region used | What does it measure? | Closest measurement in my workflow | Decision |
|-------------|-------------|-----------------------|------------------------------------|----------|
| Achromatic detectability (Lum.CoV) | Animal value compared with background value | The absolute difference between the animal's Lum.CoV and the immediate background's Lum.CoV | No direct equivalent; conceptually closest: `brightness_contrast` | Consider adding a simplified luminance-edge comparison |
| Chromatic detectability (Col.CoV) | Animal value compared with background value | The absolute difference between the animal's Col.CoV and the immediate background's Col.CoV | No direct equivalent; conceptually closest: `saturation_contrast` and `lab_colour_distance` | Keep the current colour measurements for now |
| Achromatic boldness (Lum.CoV) | Animal only | The coefficient of variation of local luminance-edge contrast within the animal | No direct equivalent; related to `animal_brightness_sd` and `animal_edge_density` | Consider adding a simplified animal luminance-edge measurement |
| Chromatic boldness (Col.CoV) | Animal only | The coefficient of variation of local chromatic edge contrast within the animal | No direct equivalent; conceptually related to `animal_saturation_sd` | Keep the current colour measurement for now |

## Difference between detectability and boldness

D05 used Lum.CoV and Col.CoV for both detectability and boldness, but the values were used differently.

For boldness, the authors used the value calculated from the animal alone.

For detectability, the authors calculated the absolute difference between the animal value and the value from its immediate background.

Therefore:

```text
boldness
= animal-only Lum.CoV or Col.CoV

detectability
= absolute difference between the animal value and the background value

```

## Comparison with my current workflow

My current workflow already separates the animal from its immediate background using an animal mask and a 120 px background ring.

### Current animal-background measurements

- `gray_contrast`
- `brightness_contrast`
- `saturation_contrast`
- `lab_colour_distance`

These measurements compare average properties of the animal with average properties of the background.

For example, `brightness_contrast` compares mean animal brightness with mean background brightness.

D05 used a different approach. It compared the coefficient of variation of local edge contrast in the animal with the same measurement in the background.

Therefore, my current animal-background measurements address a similar biological question, but they are not direct equivalents of D05 detectability.

### Current animal-only measurements

- `animal_brightness_mean`
- `animal_saturation_mean`
- `animal_brightness_sd`
- `animal_saturation_sd`
- `animal_gray_sd`
- `animal_edge_density`

These measurements describe brightness, colour variation and edge abundance within the animal.

However, `animal_edge_density` only measures how many edge pixels are present. It does not measure how strong those edges are or how variable their contrast is.

Therefore, my current animal-only measurements are related to D05 boldness, but they do not reproduce Lum.CoV or Col.CoV.

## Candidate measurements suggested by D05

D05 suggests that luminance-edge variation may be useful for separating boldness from detectability.

Three simplified measurements could be tested:

- `animal_luminance_edge_cv`
- `background_luminance_edge_cv`
- `luminance_edge_cv_difference`

The animal value would describe luminance-edge variation within the animal.

The background value would describe luminance-edge variation within the 120 px background ring.

The difference value would compare the animal with its immediate background:

```text
luminance_edge_cv_difference
= absolute difference between animal_luminance_edge_cv
  and background_luminance_edge_cv
 ```

 ---

## D06 – Highly defended nudibranchs “escape” to visually distinct background habitats

Paper: van den Berg, Santon, Endler and Cheney (2024)

This paper focuses on the visual properties of the natural backgrounds where nudibranchs were found.

Unlike D05, it does not mainly calculate the difference between each animal and its background. Instead, it analyses the background region itself and asks whether species with different chemical defences occur on visually different or more variable backgrounds.

The study tested part of the “escape and radiate” hypothesis. This hypothesis suggests that chemically defended species may be less dependent on matching one specific background and may therefore use a wider range of habitats.

## Images and background selection

The study analysed calibrated photographs of 184 individuals from 12 dorid nudibranch species.

The animal and its background were manually separated. The background region was drawn around the area immediately surrounding each animal.

Out-of-focus areas and areas containing strong shadows from artificial lighting were excluded from the background region.

The images were analysed using the visual system of a triggerfish at two viewing distances:

- 2 cm
- 30 cm

The 2 cm distance represented a close predator encounter. The 30 cm distance represented a greater viewing distance where fine spatial details would be less visible.

## Background measurements

The study used QCPA to calculate 157 colour-pattern statistics for each background.

These measurements came from four analysis groups:

- Colour Adjacency Analysis (CAA)
- Visual Contrast Analysis (VCA)
- Boundary Strength Analysis (BSA)
- Local Edge Intensity Analysis (LEIA)

The 157 measurements were filtered to remove strongly correlated variables. Seventeen measurements were retained for the factor analysis.

The retained measurements were:

- `BSA.BCVL.Hrz`
- `BSA.BCVSsat.Hrz`
- `BSA.BML.Vrt`
- `BSA.BMS.Hrz`
- `BSA.BsSsat.Hrz`
- `CAA.Asp`
- `CAA.PT`
- `CAA.Qc.Vrt`
- `CAA.Qt`
- `Col.kurtosis`
- `Col.mean.vrt`
- `Lum.CoV`
- `Lum.kurtosis.vrt`
- `Lum.mean.vrt`
- `VCA.CVS.Hrz`
- `VCA.ML.Vrt`
- `VCA.MSL.Vrt`

The measurements ending in `Hrz` describe the horizontal direction. Measurements ending in `Vrt` describe the vertical direction.

## Main types of background information

| Background property | Example measurements in D06 | What does it describe? | Closest information in my workflow | Decision for my project |
|---------------------|-----------------------------|-------------------------|------------------------------------|-------------------------|
| Luminance edge contrast | `Lum.mean.vrt`, `VCA.ML.Vrt`, `VCA.MSL.Vrt`, `BSA.BML.Vrt` | The strength of brightness differences and brightness boundaries in the background | The 120 px ring is already used for brightness measurements, but background edge strength should be checked separately | Consider a simple background luminance-edge measurement |
| Chromatic edge contrast | `Col.mean.vrt`, `BSA.BMS.Hrz`, `BSA.BsSsat.Hrz` | The strength of colour or saturation differences in the background | Background colour contributes to `saturation_contrast` and `lab_colour_distance` | Retain the existing simple colour measurements |
| Contrast variability | `Lum.CoV`, `Lum.kurtosis.vrt`, `Col.kurtosis`, `BSA.BCVL.Hrz`, `BSA.BCVSsat.Hrz`, `VCA.CVS.Hrz` | Whether edge contrast is consistent or highly variable across the background | No confirmed direct equivalent as a separate background output | Consider simple background variation measurements |
| Patch size and direction | `CAA.PT`, `CAA.Asp` | The typical size and orientation of background colour patches | Not implemented | Not a priority |
| Pattern evenness and transitions | `CAA.Qc.Vrt`, `CAA.Qt` | How evenly colours are distributed and how regularly colour patches change | Not implemented | Not a priority |

## Factors identified in D06

The 17 measurements were reduced to four factors. Together, the four factors explained 39% of the variation in the backgrounds.

### Factor 1: overall background colour and luminance contrast

Factor 1 was mainly associated with luminance edge contrast, chromatic edge contrast, contrast variability and patch-size information.

This was the only factor that showed a clear difference between the backgrounds of defended and undefended species.

Chemically defended species were found on backgrounds with greater chromatic and achromatic contrast than undefended species.

This difference was present at both 2 cm and 30 cm.

However, the backgrounds of moderately defended and highly defended species were not clearly different from each other.

### Factor 2: contrast between patches and background evenness

Factor 2 represented stronger luminance and saturation contrast between background patches together with lower background evenness.

There was no clear difference in Factor 2 between chemical-defence groups.

Factor 2 changed with viewing distance, but this change was similar across the different defence groups.

### Factor 3: variability and pattern regularity

Factor 3 represented increased variability in luminance and colour contrast together with reduced average pattern regularity.

There was no clear difference in Factor 3 between chemical-defence groups.

### Factor 4: patch contrast and boundary contrast

Factor 4 represented relationships between achromatic patch contrast, achromatic boundary contrast and chromatic boundary variability.

There was no clear difference in Factor 4 between chemical-defence groups.

## Main findings from D06

Chemically defended nudibranch species occurred on backgrounds that were visually different from the backgrounds of undefended species.

The clearest difference was that the backgrounds of defended species had greater colour and luminance contrast.

This difference remained visible at both close and greater viewing distances.

However, the study did not find evidence that defended species occurred on a more variable range of backgrounds.

This means that defended species were associated with different background properties, but not necessarily with greater background diversity.

The strength of chemical defence also did not show a simple gradual relationship with background appearance. Moderately defended and highly defended species often had similar background properties.

## Relationship with my 120 px background ring

My workflow uses a fixed 120 px ring around the segmented animal.

This is conceptually similar to D06 because both methods aim to measure the immediate visual background surrounding the animal.

However, the methods are not identical.

D06 manually selected the background region and excluded:

- out-of-focus areas;
- excessive shadows;
- unsuitable parts of the photograph.

My method automatically uses a fixed-width ring. It may therefore include unsuitable background pixels unless the image passes visual quality control.

D06 also used calibrated photographs, triggerfish visual modelling, colour clustering and viewing-distance modelling. My workflow uses uncalibrated citizen-science images and simpler computer-vision measurements.

The 120 px ring should therefore be described as a standardised local background sample, not as an exact reproduction of the D06 background method.

## Background measurements relevant to my project

My current workflow already uses the background ring when calculating:

- `gray_contrast`
- `brightness_contrast`
- `saturation_contrast`
- `lab_colour_distance`

These measurements compare the animal with its background.

D06 shows that the visual properties of the background may also be biologically relevant by themselves.

The next code review should check whether the following background-only measurements are already saved as separate variables:

- mean background brightness;
- variation in background brightness;
- mean background saturation;
- variation in background saturation;
- background edge density.

The following simple background measurements may be useful if they are not already included:

- `background_brightness_sd`
- `background_saturation_sd`
- `background_edge_density`
- `background_mean_luminance_edge_strength`

The D05 candidate measurement should also be retained for testing:

- `background_luminance_edge_cv`

These measurements would provide simple information about background contrast and complexity without attempting to reproduce the complete QCPA method.

## Measurements not selected at this stage

I will not currently add the full CAA patch-geometry measurements.

These include patch size, aspect ratio, colour evenness and transition regularity.

They require reliable colour clustering of the background. Online images have variable lighting, compression, focus and colour balance, so background colour clustering may not be consistent.

I will also not attempt to reproduce predator-specific chromatic contrast values from D06.

The existing saturation and Lab-based measurements will be used as simpler colour descriptors, with their limitations stated clearly.

## Current conclusion

D06 shows that background appearance should not only be treated as a reference used to calculate animal-background contrast.

The background can also be analysed as a set of visual traits.

The strongest result from D06 was that chemically defended species occurred on backgrounds with greater luminance and colour contrast than undefended species.

For my project, this supports retaining the 120 px background ring and saving a small number of background-only measurements.

The most useful candidates are background brightness variation, saturation variation, edge density and luminance-edge strength.

These should be checked and tested on the pilot images before the final measurement set is selected.

My project should not claim that a fixed 120 px ring reproduces the manually selected and predator-modelled background regions used in D06.