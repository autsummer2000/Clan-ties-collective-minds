#!/usr/bin/env python
"""
Study 3 analysis pipeline.

This script builds the district/county analysis sample, runs correlation and
bootstrap mediation analyses.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


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

TABLE6_ORDER = [
    ("distance", "Distance"),
    ("pd", "Population density"),
    ("lon", "Longitude"),
    ("lat", "Latitude"),
    ("rice_ratio", "Rice planting ratio"),
    ("GDP", "GDP"),
    ("nap", "PNAP"),
    ("CD", "Climate demand"),
    ("Lineage", "Surname concentration"),
    ("fr", "Fertility rate"),
    ("sex_ratio", "Sex ratio of newborn"),
    ("FS", "FS"),
    ("P_tgf", "P_TGF"),
    ("P_ila", "P_PLA"),
    ("dr", "DR"),
]

MEDIATION_CONTROLS = {
    "FS": ["pd", "lon", "lat", "GDP", "nap", "CD"],
    "P_tgf": ["pd", "lon", "lat", "rice_ratio", "GDP", "nap", "CD"],
    "P_ila": ["lat", "rice_ratio", "GDP", "nap", "CD"],
    "dr": ["pd", "lon", "lat", "nap", "CD"],
}

# Table 7 paths reported in manuscript (10 paths).
MEDIATION_PATHS = [
    ("FS", "Lineage"),
    ("FS", "fr"),
    ("FS", "sex_ratio"),
    ("P_tgf", "Lineage"),
    ("P_tgf", "fr"),
    ("P_tgf", "sex_ratio"),
    ("P_ila", "sex_ratio"),
    ("dr", "Lineage"),
    ("dr", "fr"),
    ("dr", "sex_ratio"),
]


def find_file_and_sheet_by_columns(
    raw_dir: Path, required_columns: Iterable[str]
) -> tuple[Path, str]:
    required = set(required_columns)
    for xlsx_path in sorted(raw_dir.glob("*.xlsx")):
        excel = pd.ExcelFile(xlsx_path)
        for sheet in excel.sheet_names:
            cols = set(pd.read_excel(xlsx_path, sheet_name=sheet, nrows=1).columns)
            if required.issubset(cols):
                return xlsx_path, sheet
    raise FileNotFoundError(f"Could not find xlsx with columns: {sorted(required)}")


def build_study3_sample(raw_dir: Path) -> pd.DataFrame:
    macro_file, macro_sheet = find_file_and_sheet_by_columns(
        raw_dir, ["Province", "City", "distance", "Fertility rate of 2010"]
    )
    pop_file, pop_sheet = find_file_and_sheet_by_columns(raw_dir, ["city", "pd"])
    lonlat_file, lonlat_sheet = find_file_and_sheet_by_columns(raw_dir, ["NAME"])

    macro_df = pd.read_excel(macro_file, sheet_name=macro_sheet)
    area_df = macro_df[macro_df["Province"].isin(AREA_PROVINCES)].copy()
    area_df.columns = [
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

    pop_df = pd.read_excel(pop_file, sheet_name=pop_sheet)[["city", "pd"]].copy()
    pop_df["city"] = pop_df["city"].astype(str).str[:2]

    lonlat_df = pd.read_excel(lonlat_file, sheet_name=lonlat_sheet).copy()
    other_cols = [col for col in lonlat_df.columns if col != "NAME"]
    if len(other_cols) < 2:
        raise ValueError("Longitude/latitude columns not found in lonlat sheet.")
    lon_col, lat_col = other_cols[0], other_cols[1]
    lonlat_df = lonlat_df[["NAME", lon_col, lat_col]].copy()
    lonlat_df["NAME"] = lonlat_df["NAME"].astype(str).str[:2]

    area_df["city"] = area_df["city"].astype(str)
    merged = area_df.merge(pop_df, how="left", on="city")
    merged = merged.drop_duplicates()
    merged = merged.merge(lonlat_df, how="left", left_on="city", right_on="NAME")
    merged = merged.loc[~merged["city"].duplicated()].copy()
    merged = merged.loc[~merged["pd"].isna()].copy()
    merged = merged.rename(columns={lon_col: "lon", lat_col: "lat"})

    if merged.shape[0] != 816:
        raise ValueError(f"Unexpected sample size: {merged.shape[0]} (expected 816).")

    output_order = [
        "province",
        "city",
        "distance",
        "rice_ratio",
        "Lineage",
        "fr",
        "sex_ratio",
        "FS",
        "P_tgf",
        "P_ila",
        "dr",
        "pd",
        "lon",
        "lat",
        "GDP",
        "nap",
        "CD",
    ]
    return merged[output_order]


def zscore_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for col in columns:
        values = result[col].astype(float).values
        result[col] = (values - values.mean()) / values.std(ddof=0)
    return result


def significance_stars(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


def compute_correlations(
    standardized_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = [label for _, label in TABLE6_ORDER]
    keys = [key for key, _ in TABLE6_ORDER]
    n = len(keys)

    corr_matrix = np.zeros((n, n), dtype=float)
    p_matrix = np.zeros((n, n), dtype=float)

    for i in range(n):
        corr_matrix[i, i] = 1.0
        p_matrix[i, i] = 0.0
        for j in range(i + 1, n):
            r, p = stats.pearsonr(
                standardized_df[keys[i]].astype(float),
                standardized_df[keys[j]].astype(float),
            )
            corr_matrix[i, j] = corr_matrix[j, i] = r
            p_matrix[i, j] = p_matrix[j, i] = p

    corr_df = pd.DataFrame(corr_matrix, index=labels, columns=labels)
    p_df = pd.DataFrame(p_matrix, index=labels, columns=labels)
    formatted_df = corr_df.copy().astype(str)

    for i in range(n):
        for j in range(n):
            if i == j:
                formatted_df.iat[i, j] = "1.000***"
            else:
                r = corr_df.iat[i, j]
                p = p_df.iat[i, j]
                formatted_df.iat[i, j] = f"{r:.3f}{significance_stars(p)}"

    return corr_df, p_df, formatted_df


def ols_with_inference(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    xtx = X.T @ X
    xtx_inv = np.linalg.pinv(xtx)
    beta = xtx_inv @ X.T @ y
    residual = y - X @ beta

    n = X.shape[0]
    p = X.shape[1]
    dof = n - p
    sigma2 = float((residual.T @ residual) / dof)
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.diag(cov))
    t_values = beta / se
    p_values = 2 * stats.t.sf(np.abs(t_values), df=dof)
    return beta, se, t_values, p_values


def compute_mediation(
    standardized_df: pd.DataFrame, boot: int, seed: int
) -> pd.DataFrame:
    rows = []

    for outcome, mediator in MEDIATION_PATHS:
        controls = MEDIATION_CONTROLS[outcome]
        use_cols = ["distance", mediator, outcome] + controls
        data = standardized_df[use_cols].dropna().copy()
        n = data.shape[0]

        # Equivalent to PROCESS controls_in='all_to_y': controls only in Y model.
        X_m = np.column_stack([np.ones(n), data["distance"].values])
        y_m = data[mediator].values
        beta_m, _, _, _ = ols_with_inference(y_m, X_m)
        a_path = float(beta_m[1])

        y_col = data[outcome].values
        x_cols = ["distance", mediator] + controls
        X_y = np.column_stack([np.ones(n)] + [data[col].values for col in x_cols])
        beta_y, se_y, t_y, p_y = ols_with_inference(y_col, X_y)

        direct_effect = float(beta_y[1])
        direct_se = float(se_y[1])
        direct_t = float(t_y[1])
        direct_p = float(p_y[1])
        b_path = float(beta_y[2])
        indirect_effect = a_path * b_path

        rng = np.random.default_rng(seed)
        boot_values = np.empty(boot, dtype=float)
        for i in range(boot):
            idx = rng.integers(0, n, n)
            sample = data.iloc[idx]
            sample_n = sample.shape[0]

            X_m_b = np.column_stack([np.ones(sample_n), sample["distance"].values])
            y_m_b = sample[mediator].values
            a_b = float(ols_with_inference(y_m_b, X_m_b)[0][1])

            X_y_b = np.column_stack(
                [np.ones(sample_n)] + [sample[col].values for col in x_cols]
            )
            y_b = sample[outcome].values
            b_b = float(ols_with_inference(y_b, X_y_b)[0][2])
            boot_values[i] = a_b * b_b

        boot_se = float(boot_values.std(ddof=1))
        boot_ci_lower, boot_ci_upper = np.percentile(boot_values, [2.5, 97.5])

        path_name = f"Distance -> {mediator} -> {outcome}"

        rows.append(
            {
                "Path": path_name,
                "Effect Type": "Direct effect",
                "Effect": direct_effect,
                "SE": direct_se,
                "t": direct_t,
                "p": direct_p,
                "95% CI Lower": direct_effect - 1.96 * direct_se,
                "95% CI Upper": direct_effect + 1.96 * direct_se,
            }
        )
        rows.append(
            {
                "Path": path_name,
                "Effect Type": "Indirect effect",
                "Effect": indirect_effect,
                "SE": boot_se,
                "t": np.nan,
                "p": np.nan,
                "95% CI Lower": float(boot_ci_lower),
                "95% CI Upper": float(boot_ci_upper),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Study 3 analysis pipeline.")
    parser.add_argument("--boot", type=int, default=5000, help="Bootstrap iterations.")
    parser.add_argument("--seed", type=int, default=8911, help="Random seed.")
    args = parser.parse_args()

    study_root = Path(__file__).resolve().parents[2]
    raw_dir = study_root / "data" / "raw"
    processed_dir = study_root / "data" / "processed"
    results_dir = study_root / "results"

    processed_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    sample_df = build_study3_sample(raw_dir)
    sample_df.to_csv(processed_dir / "study3_sample_816.csv", index=False, encoding="utf-8-sig")

    analysis_cols = [key for key, _ in TABLE6_ORDER]
    standardized_df = zscore_columns(sample_df, analysis_cols)
    standardized_df.to_csv(
        processed_dir / "study3_sample_816_standardized.csv",
        index=False,
        encoding="utf-8-sig",
    )

    corr_df, p_df, corr_fmt_df = compute_correlations(standardized_df)
    corr_fmt_df.to_csv(results_dir / "table6_correlations.csv", encoding="utf-8-sig")

    mediation_df = compute_mediation(standardized_df, boot=args.boot, seed=args.seed)
    mediation_df.to_csv(
        results_dir / "table7_bootstrap_mediation.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "sample_size": int(sample_df.shape[0]),
        "province_count": int(sample_df["province"].nunique()),
        "city_count": int(sample_df["city"].nunique()),
        "bootstrap_iterations": int(args.boot),
        "random_seed": int(args.seed),
    }
    (processed_dir / "sample_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[OK] Study 3 pipeline completed.")
    print(f" - processed: {processed_dir}")
    print(f" - results:   {results_dir}")


if __name__ == "__main__":
    main()

