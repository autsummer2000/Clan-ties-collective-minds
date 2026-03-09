from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

MODEL_VARS = [
    "collectivism",
    "zongzu3",
    "male",
    "age",
    "NYLL",
    "town",
    "education_ord",
    "PCMHI_ord",
    "SES",
]
TERM_NAMES = [
    "Intercept",
    "zongzu3",
    "male",
    "age",
    "NYLL",
    "town",
    "education_ord",
    "PCMHI_ord",
    "SES",
]


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=1)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - s.mean()) / sd


def stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Table 2 regression results from survey data.")
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="Optional input path (.xlsx/.csv). Default: data/raw/survey_data_new2.xlsx",
    )
    parser.add_argument(
        "--se-type",
        type=str,
        choices=["hc3", "cluster_province"],
        default="hc3",
        help="Robust SE type. cluster_province uses province clusters.",
    )
    parser.add_argument(
        "--export-city-data",
        action="store_true",
        help="Export data/processed/city_data.csv (not required for Table 2 estimation).",
    )
    return parser.parse_args()


def load_mappings(script_path: Path) -> dict:
    mapping_path = script_path.with_name("mappings.json")
    with mapping_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fit_with_robust_se(zdf: pd.DataFrame, province_series: pd.Series, se_type: str):
    y = zdf["collectivism"]
    X = sm.add_constant(zdf[["zongzu3", "male", "age", "NYLL", "town", "education_ord", "PCMHI_ord", "SES"]])
    fit = sm.OLS(y, X).fit()

    if se_type == "cluster_province":
        groups = province_series.loc[zdf.index]
        if groups.nunique(dropna=True) < 2:
            raise ValueError("cluster_province requires at least two province clusters.")
        rob = fit.get_robustcov_results(cov_type="cluster", groups=groups)
        cov_label = "cluster(province)"
    else:
        rob = fit.get_robustcov_results(cov_type="HC3")
        cov_label = "HC3"
    return fit, rob, cov_label


def main() -> None:
    args = build_args()
    mappings = load_mappings(Path(__file__).resolve())

    study1 = Path(__file__).resolve().parents[2]
    default_input = study1 / "data" / "raw" / "survey_data_new2.xlsx"
    input_path = Path(args.input).resolve() if args.input else default_input.resolve()

    proc_dir = study1 / "data" / "processed"
    res_dir = study1 / "results"
    proc_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        df = pd.read_excel(input_path)

    a1_cols = [c for c in df.columns if c.startswith("A1__")]
    a1 = df[a1_cols].replace(mappings["a1_likert_map"])
    for c in ["A1__13", "A1__14"]:
        if c in a1.columns:
            a1[c] = a1[c].apply(lambda x: 6 - x if pd.notna(x) else np.nan)
    collectivism = a1.apply(pd.to_numeric, errors="coerce").mean(axis=1)

    d_map = mappings["d_binary_map"]
    d3_map = mappings["d3_frequency_map"]
    d1 = df["D1"].replace(d_map) if "D1" in df.columns else np.nan
    d2 = df["D2"].replace(d_map) if "D2" in df.columns else np.nan
    d3 = df["D3"].replace(d3_map) if "D3" in df.columns else np.nan
    zongzu3 = (
        pd.to_numeric(d1, errors="coerce").fillna(0)
        + pd.to_numeric(d2, errors="coerce").fillna(0)
        + pd.to_numeric(d3, errors="coerce").fillna(0)
    )

    male = df["G1"].map(mappings["gender_map"]) if "G1" in df.columns else np.nan
    age = pd.to_numeric(df["G2"], errors="coerce") if "G2" in df.columns else np.nan
    nyll = pd.to_numeric(df["G4"], errors="coerce") if "G4" in df.columns else np.nan
    town = df["G5"].map(mappings["town_map"]) if "G5" in df.columns else np.nan

    edu_map = mappings["education_map"]
    education_ord = df["G7"].map(edu_map) if "G7" in df.columns else np.nan

    income_map = mappings["income_map"]
    pcmhi_ord = df["G9"].map(income_map) if "G9" in df.columns else np.nan

    g10 = pd.to_numeric(df["G10__1"], errors="coerce") if "G10__1" in df.columns else np.nan
    g11 = pd.to_numeric(df["G11__1"], errors="coerce") if "G11__1" in df.columns else np.nan
    ses = (g10 + g11) / 2

    out = pd.DataFrame(
        {
            "rid": df["rid"] if "rid" in df.columns else np.arange(len(df)),
            "province": df["G3__1"] if "G3__1" in df.columns else np.nan,
            "city_x": df["G3__2"] if "G3__2" in df.columns else np.nan,
            "collectivism": collectivism,
            "zongzu3": zongzu3,
            "male": male,
            "age": age,
            "NYLL": nyll,
            "town": town,
            "education_ord": education_ord,
            "PCMHI_ord": pcmhi_ord,
            "SES": ses,
        }
    )
    out = out.dropna(subset=MODEL_VARS).copy()

    out.to_csv(proc_dir / "try_data_for_regression.csv", index=False, encoding="utf-8-sig")

    if args.export_city_data:
        city = (
            out.groupby(["province", "city_x"], as_index=False)[MODEL_VARS]
            .mean()
            .rename(columns={"city_x": "city"})
        )
        city.to_csv(proc_dir / "city_data.csv", index=False, encoding="utf-8-sig")

    zdf = out[MODEL_VARS].apply(zscore).dropna().copy()
    fit, rob, cov_label = fit_with_robust_se(zdf=zdf, province_series=out["province"], se_type=args.se_type)

    rows = []
    for i, nm in enumerate(TERM_NAMES):
        coef = float(rob.params[i])
        se = float(rob.bse[i])
        p = float(rob.pvalues[i])
        rows.append(
            {
                "term": nm,
                "coef": coef,
                "se_robust": se,
                "p_value": p,
                "stars": stars(p),
                "display": f"{coef:.3f}{stars(p)} ({se:.3f})",
            }
        )

    meta = {
        "N": int(len(zdf)),
        "R2": float(fit.rsquared),
        "Adj_R2": float(fit.rsquared_adj),
        "cov_type": cov_label,
        "se_type_arg": args.se_type,
    }

    table = pd.DataFrame(rows)
    stats_rows = pd.DataFrame(
        [
            {"term": "N", "coef": np.nan, "se_robust": np.nan, "p_value": np.nan, "stars": "", "display": str(meta["N"])},
            {"term": "R2", "coef": np.nan, "se_robust": np.nan, "p_value": np.nan, "stars": "", "display": f"{meta['R2']:.3f}"},
            {"term": "Adj_R2", "coef": np.nan, "se_robust": np.nan, "p_value": np.nan, "stars": "", "display": f"{meta['Adj_R2']:.3f}"},
        ]
    )
    table_with_stats = pd.concat([table, stats_rows], ignore_index=True)
    table_with_stats.to_csv(res_dir / "table2_ccsei_collectivism.csv", index=False, encoding="utf-8-sig")

    print("DONE")
    print("input:", input_path)
    print("N:", meta["N"])
    print("SE type:", meta["cov_type"])
    print("processed:", proc_dir)
    print("results:", res_dir)


if __name__ == "__main__":
    main()
