# Study 3 Data Dictionary

## 1. Data Overview

- **Sample Size**: 816 districts
- **Geographic Coverage**: 17 provinces (Guangdong, Jiangxi, Fujian, Zhejiang, Anhui, Jiangsu, Hubei, Hunan, Henan, Shanxi, Gansu, Hebei, Shandong, Liaoning, Jilin, Heilongjiang, Shaanxi)
- **Data Year**: 2010
- **Number of Variables**: 17 (2 identifier variables + 15 analysis variables)

## 2. Raw Data Files

### Files in data/raw/ directory:

1. **district_macro_data.xlsx**
   - Contains 14 columns: Province, District, Rice planting ratio, Lineage development, GDP, Proportion of non-agricultural population, Climate demand, Family size, Proportion living alone, Proportion of three-generation families, Sex ratio at birth, Divorce rate, Fertility rate, Distance

2. **district_population_density.xlsx**
   - Contains district-level population density data

3. **district_coordinates.xlsx**
   - Contains district geographic coordinates (longitude, latitude)

## 3. Variable Descriptions

### 3.1 Identifier Variables

| Variable | Description | Type |
|----------|-------------|------|
| province | Province name | Categorical |
| city | District name | Categorical |

### 3.2 Independent Variable

| Variable | Full Name | Unit | Mean | SD | Min | Max |
|----------|-----------|------|------|----|----|-----|
| distance | Road distance to Beijing | km | 1131.56 | 514.70 | 72.90 | 2580.30 |

### 3.3 Mediator Variables

| Variable | Full Name | Unit | Mean | SD | Min | Max |
|----------|-----------|------|------|----|----|-----|
| Lineage | Surname concentration | Proportion (0-1) | 0.80 | 0.09 | 0.00 | 1.00 |
| fr | Fertility rate | Persons/woman | 1.51 | 0.19 | 0.00 | 1.98 |
| sex_ratio | Sex ratio at birth | Males/100 females | 119.93 | 12.73 | 0.00 | 161.66 |

### 3.4 Dependent Variables

| Variable | Full Name | Unit | Mean | SD | Min | Max |
|----------|-----------|------|------|----|----|-----|
| FS | Average family size | Persons/household | 3.28 | 0.44 | 0.00 | 5.59 |
| P_tgf | Proportion of three-generation families | Percentage | 21.09 | 7.34 | 0.00 | 45.75 |
| P_ila | Proportion of people living alone | Percentage | 11.67 | 3.97 | 0.00 | 27.51 |
| dr | Divorce rate | Per thousand | 1.41 | 0.80 | 0.00 | 8.04 |

### 3.5 Control Variables

| Variable | Full Name | Unit | Mean | SD | Min | Max |
|----------|-----------|------|------|----|----|-----|
| pd | Population density | Persons/km² | 344.41 | 279.61 | 3.49 | 2727.27 |
| lon | Longitude | Degrees | 114.06 | 13.90 | 0.00 | 132.20 |
| lat | Latitude | Degrees | 33.47 | 6.95 | 0.00 | 52.32 |
| rice_ratio | Rice planting ratio | Percentage | 27.92 | 33.23 | 0.00 | 98.04 |
| GDP | GDP per capita | Yuan | 13832.36 | 16300.35 | 6.00 | 142185.00 |
| nap | Proportion of non-agricultural population | Percentage | 18.18 | 10.60 | 0.00 | 90.84 |
| CD | Climate demand | Index | 28.89 | 7.62 | 10.30 | 50.50 |

## 4. Column Name Mapping

| Original Column Name | Processed Column Name | Description |
|---------------------|----------------------|-------------|
| Province | province | Province name |
| City | city | District name |
| distance | distance | Road distance to Beijing |
| Rice planting ratio | rice_ratio | Rice planting ratio |
| Lineage development | Lineage | Surname concentration |
| Fertility rate of 2010 | fr | Fertility rate |
| Sex ratio at birth of 2010 | sex_ratio | Sex ratio at birth |
| Family scale of 2010 | FS | Average family size |
| Percentage of three-generation families of 2010 | P_tgf | Proportion of three-generation families |
| Percentage of individuals living alone at 2010 | P_ila | Proportion of people living alone |
| Divorce rate of 2010 | dr | Divorce rate |
| Population density (pd column) | pd | Population density |
| Longitude | lon | Longitude |
| Latitude | lat | Latitude |
| GDP_2010 | GDP | GDP per capita |
| Proportion of non-agricultural population | nap | Proportion of non-agricultural population |
| Climatic Demands | CD | Climate demand index |

## 5. Data Processing Workflow

### 5.1 Sample Construction Steps

1. Filter districts from 17 specified provinces in the macro data
2. Merge with population density data by `city` field (first 2 characters)
3. Merge with coordinate data by `city` field (first 2 characters)
4. Remove duplicate district records
5. Remove samples with missing population density
6. Final analysis sample: N=816

### 5.2 Standardization

All 15 analysis variables are z-score standardized:
- Formula: z = (x - mean) / sd
- After standardization: mean = 0, standard deviation = 1
- Standardized data saved in `study3_sample_816_standardized.csv`

## 6. Variable Usage in Analyses

### 6.1 Table 6 Correlation Analysis

Pearson correlation matrix computed using all 15 analysis variables.

### 6.2 Table 7 Mediation Analysis

**Mediation Paths** (10 paths):
- Distance → Lineage → FS
- Distance → fr → FS
- Distance → sex_ratio → FS
- Distance → Lineage → P_tgf
- Distance → fr → P_tgf
- Distance → sex_ratio → P_tgf
- Distance → sex_ratio → P_ila
- Distance → Lineage → dr
- Distance → fr → dr
- Distance → sex_ratio → dr

**Control Variable Specifications**:
- Outcome = FS: pd, lon, lat, GDP, nap, CD
- Outcome = P_tgf: pd, lon, lat, rice_ratio, GDP, nap, CD
- Outcome = P_ila: lat, rice_ratio, GDP, nap, CD
- Outcome = dr: pd, lon, lat, nap, CD

### 6.3 Table 8/9 Structural Equation Modeling

SEM analysis using all 15 standardized analysis variables.

## 7. Output Files

### 7.1 Processed Data

- `data/processed/study3_sample_816.csv` - Analysis sample in original scale
- `data/processed/study3_sample_816_standardized.csv` - Standardized analysis sample

### 7.2 Analysis Results

- `results/table6_correlations.csv` - Correlation matrix
- `results/table7_bootstrap_mediation.csv` - Bootstrap mediation analysis results
- `results/table9_sem_paths_from_program_table9_style.csv` - SEM path coefficients
- `results/table9_sem_fit_from_program.csv` - SEM fit indices
