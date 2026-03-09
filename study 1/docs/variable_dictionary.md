# Study1_1 Variable Dictionary (Table 2)

This dictionary matches the current implementation in
`code/reproduce/table2_ccsei_collectivism.py`.

## Core variables

- `collectivism`: row mean of `A1__*` items.
- `zongzu3`: `D1 + D2 + D3`.

## Coding rules

- `collectivism` is derived from all `A1__*` items after Likert recoding, with
  reverse coding applied to `A1__13` and `A1__14`.
- `zongzu3` is computed by recoding and combining `D1`, `D2`, and `D3`.
- Exact category-to-value mappings are implemented in
  `code/reproduce/table2_ccsei_collectivism.py`.

## Controls

- `male` from `G1` (binary recode)
- `age` from `G2` (numeric)
- `NYLL` from `G4` (numeric)
- `town` from `G5` (binary recode)
- `education_ord` from `G7` (ordinal recode)
- `PCMHI_ord` from `G9` (ordinal recode)
- `SES = (G10__1 + G11__1) / 2`

## Estimation spec

- Variables in the model are z-scored with sample SD (`ddof=1`).
- OLS robust SE can be selected by `--se-type`:
  - `hc3` (default)
  - `cluster_province`
