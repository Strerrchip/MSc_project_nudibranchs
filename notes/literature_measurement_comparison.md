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