#!/usr/bin/env python
"""
Run the Table 9 SEM model from original Study 3 notebook logic and export
independent result files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from semopy import Model
from semopy import stats as sstats
from semopy.inspector import inspect


AREA_PROVINCES = [
    "\u5e7f\u4e1c",
    "\u6c5f\u897f",
    "\u798f\u5efa",
    "\u6d59\u6c5f",
    "\u5b89\u5fbd",
    "\u6c5f\u82cf",
    "\u6e56\u5317",
    "\u6e56\u5357",
    "\u6cb3\u5357",
    "\u5c71\u897f",
    "\u7518\u8083",
    "\u6cb3\u5317",
    "\u5c71\u4e1c",
    "\u8fbd\u5b81",
    "\u5409\u6797",
    "\u9ed1\u9f99\u6c5f",
    "\u9655\u897f",
]


def find_file_and_sheet_by_columns(raw_dir: Path, required_cols: set[str]) -> tuple[Path, str]:
    for xlsx in sorted(raw_dir.glob("*.xlsx")):
        excel = pd.ExcelFile(xlsx)
        for sheet in excel.sheet_names:
            cols = set(pd.read_excel(xlsx, sheet_name=sheet, nrows=1).columns)
            if required_cols.issubset(cols):
                return xlsx, sheet
    raise FileNotFoundError(f"Cannot find xlsx with columns: {required_cols}")


def build_scaled_data(raw_dir: Path) -> pd.DataFrame:
    macro_file, macro_sheet = find_file_and_sheet_by_columns(
        raw_dir, {"Province", "City", "distance", "Fertility rate of 2010"}
    )
    pop_file, pop_sheet = find_file_and_sheet_by_columns(raw_dir, {"city", "pd"})
    lonlat_file, lonlat_sheet = find_file_and_sheet_by_columns(raw_dir, {"NAME"})

    macro = pd.read_excel(macro_file, sheet_name=macro_sheet)
    area_data = macro[macro["Province"].isin(AREA_PROVINCES)].copy()

    area_data.columns = [
        "province",
        "city",
        "rice_ratio",
        "Lineage",
        "GDP",
        "nap",
        "CD",
        "FS",
        "P_ila",
        "P_tgf",
        "sex_ratio",
        "dr",
        "fr",
        "distance",
    ]

    people = pd.read_excel(pop_file, sheet_name=pop_sheet)[["city", "pd"]].copy()
    lonlat = pd.read_excel(lonlat_file, sheet_name=lonlat_sheet).copy()
    other_cols = [c for c in lonlat.columns if c != "NAME"]
    lon_col, lat_col = other_cols[0], other_cols[1]
    lonlat = lonlat[["NAME", lon_col, lat_col]].copy()

    people["city"] = people["city"].astype(str).str[:2]
    lonlat["NAME"] = lonlat["NAME"].astype(str).str[:2]
    area_data["city"] = area_data["city"].astype(str)

    data_copy = area_data.merge(people, how="left", on="city")
    data_copy = data_copy.loc[~data_copy.duplicated(), :]
    data_copy = data_copy.merge(lonlat, how="left", left_on="city", right_on="NAME")
    data_copy = data_copy.loc[~data_copy["city"].duplicated(), :]
    data_copy = data_copy.loc[~data_copy["pd"].isna(), :]

    data_copy = data_copy.rename(columns={lon_col: "lon", lat_col: "lat"})

    variable_name = [
        "distance",
        "pd",
        "lon",
        "lat",
        "rice_ratio",
        "GDP",
        "nap",
        "CD",
        "Lineage",
        "fr",
        "sex_ratio",
        "FS",
        "P_tgf",
        "P_ila",
        "dr",
    ]

    scaled = data_copy[variable_name].copy()
    for col in variable_name:
        x = scaled[col].astype(float).values
        scaled[col] = (x - np.mean(x)) / np.std(x)
    return scaled


def format_table9_style(raw_df: pd.DataFrame) -> pd.DataFrame:
    name_map = {
        "collectivism": "Collectivism",
        "individualism": "Individualism",
        "zongzu": "Chinese clan system",
        "distance": "Distance",
        "pd": "Population density",
        "rice_ratio": "Rice planting ratio",
        "lon": "Longitude",
        "lat": "Latitude",
        "GDP": "GDP",
        "nap": "PNAP",
        "CD": "Climate demand",
        "Lineage": "Surname concentration",
        "sex_ratio": "Sex ratio of newborn",
        "fr": "Fertility rate",
        "FS": "FS",
        "P_tgf": "P_TGF",
        "P_ila": "P_PLA",
        "dr": "DR",
    }

    latent = {"collectivism", "individualism", "zongzu"}

    out = raw_df.copy()
    out["Variable 1"] = out["lval"].map(lambda x: name_map.get(x, x))
    out["Variable 2"] = out["rval"].map(lambda x: name_map.get(x, x))
    out["Operator"] = out["op"]

    # Convert measurement rows to manuscript-style "~=" direction:
    # semopy: observed ~ latent  -> manuscript: observed ~= latent
    mask_measure = (out["op"] == "~") & out["lval"].isin([k for k in name_map if k not in latent]) & out["rval"].isin(latent)
    out.loc[mask_measure, "Operator"] = "~="

    out = out.rename(
        columns={
            "Estimate": "Estimated",
            "Std. Err": "SE",
            "z-value": "z",
            "p-value": "p",
        }
    )
    keep = ["Variable 1", "Operator", "Variable 2", "Estimated", "SE", "z", "p"]
    return out[keep]


def main() -> None:
    study_root = Path(__file__).resolve().parents[2]
    raw_dir = study_root / "data" / "raw"
    results_dir = study_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    data_scaled = build_scaled_data(raw_dir)

    # This model corresponds to Analysis_2.ipynb cell set that produced
    # chi2=585.18872 (Table 9 matching section).
    model_desc = """
collectivism ~ zongzu+distance+pd+rice_ratio+lon+lat+GDP+nap+CD
individualism ~ zongzu+distance+pd+rice_ratio+lon+lat+GDP+nap+CD
zongzu ~ distance
collectivism =~ P_tgf+FS
individualism =~ dr
zongzu =~ Lineage+sex_ratio+fr

distance ~~ rice_ratio
distance ~~ CD
distance ~~ lon
distance ~~ lat
CD ~~ rice_ratio
CD ~~ lon
CD ~~ lat
rice_ratio ~~ lon
rice_ratio ~~ lat
rice_ratio ~~ nap
lon ~~ GDP
lat ~~ GDP
GDP ~~ nap
GDP ~~ pd
pd ~~ nap

collectivism ~~ individualism

Lineage ~~ sex_ratio
Lineage ~~ fr
sex_ratio ~~ fr

FS ~~ P_tgf

nap ~~ zongzu
zongzu ~~ CD
zongzu ~~ rice_ratio
zongzu ~~ GDP
zongzu ~~ pd
"""

    model = Model(model_desc)
    model.fit(data_scaled, obj="MLW")

    sem_raw = inspect(model)
    table9_style = format_table9_style(sem_raw)
    table9_style.to_csv(
        results_dir / "table9_sem_paths_from_program_table9_style.csv",
        index=False,
        encoding="utf-8-sig",
    )

    fit_df = sstats.calc_stats(model).reset_index()
    fit_df.to_csv(
        results_dir / "table9_sem_fit_from_program.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("[OK] Table 9 SEM model finished.")
    print(results_dir / "table9_sem_paths_from_program_table9_style.csv")
    print(results_dir / "table9_sem_fit_from_program.csv")


if __name__ == "__main__":
    main()

