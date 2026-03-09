# Variable Dictionary

This document describes key variables and data flow used in Study 2.

## 1. Data Overview

- Final Method 4 sample:
  - 2011: 194 cities, 314,575 individuals
  - 2012: 195 cities, 293,068 individuals
- Years covered: 2011 and 2012
- Scope: mainland China city-level and individual-level records after filtering

## 2. Raw Data Files

### 2.1 Weibo feature files

- Location: `data/raw/weibo/2011/` and `data/raw/weibo/2012/`
- Number of files: 45 CSV files (2011), 15 CSV files (2012)
- Naming pattern: `big5-swb_wf*.csv`
- Raw columns include language-specific labels; the analysis script maps these to standardized English names.

### 2.2 User profile file

- File: `data/raw/AllUidV5.txt`
- Format: tab-delimited text
- Approximate size: 1.16 million users
- Fields used:
  - `V1`: user id
  - `V5`: gender
  - `V11`: area string (`province city`)

### 2.3 City-level files

- `data/raw/city_level/city_clan_data.xlsx`
  - Core fields: `city`, `fertility`, `RSB`, `non_agr`, `clan`, `rice`, `lon`, `lat`
- `data/raw/city_level/city_data_2011.xlsx`
- `data/raw/city_level/city_data_2012.xlsx`
  - Core fields: `year`, `province`, `city`, `pd`, `gdp`, `noarg`

## 3. Individual-Level Variables

### Outcomes

- `individualism`: individualism score from Weibo lexical frequency
- `collectivism`: collectivism score from Weibo lexical frequency

### Controls

- `control_words`: control-word frequency
- `f`: gender dummy (`1` female, `0` male)
- `gender`: original gender code (`"f"` or `"m"`)

### Identifiers

- `uid`: unique user id
- `txt`: text file identifier
- `year`: data year (`2011` or `2012`)
- `city`: normalized city name
- `province`: province parsed from `V11`

## 4. City-Level Variables

### Clan and demographic variables

- `clan`: surname concentration
- `fertility`: fertility rate
- `RSB`: sex ratio at birth

### Geographic variables

- `lon`: longitude
- `lat`: latitude

### Economic and population variables

- `gdp`: GDP per capita
- `pd`: population density
- `noarg`: proportion of non-agricultural population (PNAP)

### Agriculture variable

- `rice`: rice planting ratio

## 5. Model Metrics

### HLM variance components

- `tau`: between-city variance
- `sigma`: within-city variance

### Explained variance metrics

- `R2within`
- `R2between`
- `R2total`

## 6. Variable Usage by Model

### Table 3 style city-level correlation matrix

Variables included: `fertility`, `RSB`, `clan`, `rice`, `lon`, `lat`, `pd`, `gdp`, `noarg`.

### Table 4 and Table 5 HLM models

- Model 1 (null): `collectivism ~ (1 | city)`
- Model 2: `collectivism ~ clan + controls + f + (1 | city)`
- Model 3: `collectivism ~ fertility + controls + f + (1 | city)`
- Model 4: `collectivism ~ RSB + controls + f + (1 | city)`
- Model 5 (null): `individualism ~ (1 | city)`
- Model 6: `individualism ~ fertility + controls + f + (1 | city)`
- Model 7: `individualism ~ clan + controls + f + (1 | city)`
- Model 8: `individualism ~ RSB + controls + f + (1 | city)`

Where controls are `noarg`, `rice`, `gdp`, `lon`, `lat`, and `pd`.

## 7. Processing Workflow

1. Read all Weibo CSV files for 2011 and 2012.
2. Extract `uid` from `txt`.
3. Read user profile data from `data/raw/AllUidV5.txt`.
4. Parse province and city from `V11`.
5. Exclude predefined non-target provinces/regions.
6. Read and merge city-level files.
7. Normalize city names and remove duplicate city-level records.
8. Keep cities with sample size greater than 30.
9. Standardize variables (`z` score).
10. Run HLM and correlation analyses.

### Missing value strategy

- `pd` and `gdp`: mean imputation
- `noarg`: fill missing values with `0`

## 8. Output Files

Primary outputs in `results/`:

- `table4_table5_results.xlsx`
- `city_corr_2011_r.csv`
- `city_corr_2011_p.csv`
- `city_corr_2012_r.csv`
- `city_corr_2012_p.csv`
- `individual_cor_tests.csv`

## 9. Notes

- Continuous variables are standardized before modeling.
- Significance coding used in Excel tables:
  - `*` for `p < .05`
  - `**` for `p < .01`
  - `***` for `p < .001`
