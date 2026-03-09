# Study 2 Data and Analysis Notes

## Data Summary

### Weibo text data
- Includes 2011 and 2012 Weibo text feature files.
- Each CSV file contains user-level frequency statistics for individualism and collectivism related terms.
- Key variables used in this project: `txt`, `individualism`, `collectivism`, `control_words`, `I`, `We`, `You`.

### City-level data
- Includes city-level indicators such as clan strength, fertility, sex ratio, GDP, and population density.
- Key variables used in analysis: `fertility`, `RSB`, `clan`, `rice`, `lon`, `lat`, `pd`, `gdp`, `noarg`.

### User profile data
- `data/raw/AllUidV5.txt` includes basic profile information for roughly 1.2 million users.
- Main fields used here: user id, gender, and geographic location (province, city).

## Analysis Method

This project uses hierarchical linear models (HLM) to estimate how city-level factors are associated with individual-level individualism and collectivism.

### Main analysis script

`code/analysis/run_hlm_analysis.R` performs the full pipeline:
- Reads 2011 and 2012 Weibo data.
- Merges city-level covariates (surname concentration, fertility, sex ratio, and controls).
- Handles missing values (`pd`/`gdp` mean imputation, `noarg` zero fill).
- Fits 8 HLM models (4 collectivism models + 4 individualism models).
- Exports Table 4 and Table 5 style outputs.
- Computes city-level and individual-level correlation outputs.

## Run Guide

### Environment
- R >= 4.0
- Required packages: `data.table`, `readxl`, `openxlsx`, `stringr`, `lme4`, `lmerTest`

### Package Installation

Before running the analysis, install the required R packages:

```r
install.packages(c("data.table", "readxl", "openxlsx", "stringr", "lme4", "lmerTest"))
```

### Steps
1. Set working directory to the project root.
2. Run:

```r
source("code/analysis/run_hlm_analysis.R")
```

3. Outputs are written to the `results/` directory.

### Output files

Running the analysis script generates the following files in `results/`:

- `table4_table5_results.xlsx`: Combined Excel report with HLM results (Table 4 & 5)
- `city_corr_2011_r.csv`: 2011 city-level correlation coefficients
- `city_corr_2011_p.csv`: 2011 city-level p-values
- `city_corr_2012_r.csv`: 2012 city-level correlation coefficients
- `city_corr_2012_p.csv`: 2012 city-level p-values
- `individual_cor_tests.csv`: Individual-level correlation tests

## Table Mapping

- Table 3 (city-level correlation matrix): `results/city_corr_2011_*.csv` and `results/city_corr_2012_*.csv`
- Table 4 (2011 HLM results): `results/table4_table5_results.xlsx`
- Table 5 (2012 HLM results): `results/table4_table5_results.xlsx`
- Individual-level correlation analysis: `results/individual_cor_tests.csv`

