from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def correlation_analysis(data: pd.DataFrame, variable_names: list[str]) -> pd.DataFrame:
    n_vars = len(variable_names)
    corr_matrix = pd.DataFrame(index=variable_names, columns=variable_names)

    for i in range(n_vars):
        for j in range(n_vars):
            if i == j:
                corr_matrix.iloc[i, j] = "-"
            else:
                r, p = stats.pearsonr(
                    data[variable_names[i]].dropna(),
                    data[variable_names[j]].dropna()
                )
                corr_matrix.iloc[i, j] = f"{r:.3f}{stars(p)}"

    return corr_matrix


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Table 1 correlation matrix from survey data."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="Optional input path (.xlsx/.csv). Default: data/raw/survey_data_new2.xlsx",
    )
    return parser.parse_args()


def load_mappings(script_path: Path) -> dict:
    mapping_path = script_path.with_name("mappings.json")
    with mapping_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    args = build_args()
    mappings = load_mappings(Path(__file__).resolve())

    study1 = Path(__file__).resolve().parents[2]
    default_input = study1 / "data" / "raw" / "survey_data_new2.xlsx"
    input_path = Path(args.input).resolve() if args.input else default_input.resolve()

    res_dir = study1 / "results"
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

    age = pd.to_numeric(df["G2"], errors="coerce") if "G2" in df.columns else np.nan
    nyll = pd.to_numeric(df["G4"], errors="coerce") if "G4" in df.columns else np.nan

    edu_map = mappings["education_map"]
    education_ord = df["G7"].map(edu_map) if "G7" in df.columns else np.nan

    income_map = mappings["income_map"]
    pcmhi_ord = df["G9"].map(income_map) if "G9" in df.columns else np.nan

    g10 = pd.to_numeric(df["G10__1"], errors="coerce") if "G10__1" in df.columns else np.nan
    g11 = pd.to_numeric(df["G11__1"], errors="coerce") if "G11__1" in df.columns else np.nan
    ses = (g10 + g11) / 2

    analysis_data = pd.DataFrame(
        {
            "Collectivism": collectivism,
            "CCSEI": zongzu3,
            "Age": age,
            "NYLL": nyll,
            "Education level": education_ord,
            "PCMHI": pcmhi_ord,
            "SES": ses,
        }
    ).dropna()

    variable_names = [
        "Collectivism",
        "CCSEI",
        "Age",
        "NYLL",
        "Education level",
        "PCMHI",
        "SES",
    ]

    corr_table = correlation_analysis(analysis_data, variable_names)

    desc_stats = analysis_data.describe().T[["mean", "std"]]
    desc_stats.columns = ["M", "SD"]

    combined_table = pd.DataFrame(index=variable_names)
    combined_table["M"] = desc_stats["M"].values
    combined_table["SD"] = desc_stats["SD"].values
    for i, _ in enumerate(variable_names):
        combined_table[str(i + 1)] = corr_table.iloc[:, i].values
    combined_table.index = [f"{i+1}. {name}" for i, name in enumerate(variable_names)]
    combined_table.to_csv(res_dir / "table1_correlations.csv", encoding="utf-8-sig")

    print("DONE")
    print("input:", input_path)
    print("N:", len(analysis_data))
    print("results:", res_dir)


if __name__ == "__main__":
    main()



