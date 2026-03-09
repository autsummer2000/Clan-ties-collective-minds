# Study 1 Analysis Package

This folder contains the data analysis workflow for Study 1, which examines the relationship between clan culture and collectivism.

## Dependencies

Install required packages from the `study1` directory:

```powershell
pip install -r .\requirements.txt
```

## Running the Analysis

Generate Table 1 (correlation matrix):

```powershell
python .\code\reproduce\table1_correlations.py
```

Generate Table 2 with HC3 robust standard errors (default):

```powershell
python .\code\reproduce\table2_ccsei_collectivism.py
```

Generate Table 2 with province-clustered standard errors:

```powershell
python .\code\reproduce\table2_ccsei_collectivism.py --se-type cluster_province
```

## Script Parameters

`table2_ccsei_collectivism.py` supports:

- `--se-type hc3|cluster_province` - Robust standard error type (default: `hc3`)
- `--input <path>` - Use a custom input dataset instead of the default

## Output Files

- `results/table1_correlations.csv` - Correlation table (includes M/SD + correlation columns)
- `results/table2_ccsei_collectivism.csv` - Regression results
- `data/processed/try_data_for_regression.csv` - Regression-ready dataset
- `data/processed/city_data.csv` - City-level data (when `--export-city-data` is used)

## Data

Raw survey data: `data/raw/survey_data_new2.xlsx`
