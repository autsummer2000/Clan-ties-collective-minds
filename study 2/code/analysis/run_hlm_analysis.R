suppressPackageStartupMessages({
  library(data.table)
  library(readxl)
  library(openxlsx)
  library(stringr)
  library(lme4)
  library(lmerTest)
})

options(stringsAsFactors = FALSE)

weibo_col_candidates <- list(
  txt = c("txt", "txt\u6587\u4ef6\u540d"),
  individualism = c("individualism", "\u4e2a\u4f53\u4e3b\u4e49"),
  collectivism = c("collectivism", "\u96c6\u4f53\u4e3b\u4e49"),
  control_words = c("control_words", "\u63a7\u5236\u8bcd"),
  i = c("i", "I"),
  we = c("we", "We"),
  you = c("you", "You")
)

excluded_provinces <- c(
  "\u4e0a\u6d77", "\u4e91\u5357", "\u5185\u8499\u53e4", "\u53f0\u6e7e", "\u56db\u5ddd", "\u5929\u6d25",
  "\u5b81\u590f", "\u5e7f\u897f", "\u65b0\u7586", "\u6d77\u5357", "\u6fb3\u95e8", "\u897f\u85cf",
  "\u8d35\u5dde", "\u91cd\u5e86", "\u9752\u6d77", "\u9999\u6e2f", "\u5317\u4eac", "\u5176\u4ed6",
  "\u6d77\u5916", "NONE"
)

resolve_existing_path <- function(candidates, error_message) {
  existing <- candidates[file.exists(candidates)]
  if (length(existing) == 0) stop(error_message)
  existing[[1]]
}

resolve_existing_name <- function(candidates, available, error_message) {
  existing <- candidates[candidates %in% available]
  if (length(existing) == 0) stop(error_message)
  existing[[1]]
}

fmt_num <- function(x) {
  if (is.na(x)) return("")
  s <- sprintf("%.3f", x)
  s <- sub("^-0\\.", "-.", s)
  s <- sub("^0\\.", ".", s)
  s
}

fmt_p_stars <- function(p) {
  if (is.na(p)) return("")
  if (p < .001) return("***")
  if (p < .01) return("**")
  if (p < .05) return("*")
  ""
}

fmt_est <- function(est, p) {
  if (is.na(est)) return("")
  paste0(fmt_num(est), fmt_p_stars(p))
}

fmt_se <- function(se) {
  if (is.na(se)) return("")
  paste0("(", fmt_num(se), ")")
}

extract_coef <- function(model, term) {
  sm <- summary(model)$coefficients
  if (!(term %in% rownames(sm))) {
    return(list(est = NA_real_, se = NA_real_, p = NA_real_))
  }
  p_col <- grep("^Pr\\(>\\|[tz]\\|\\)$", colnames(sm), value = TRUE)
  p_val <- if (length(p_col) > 0) sm[term, p_col[1]] else NA_real_
  list(
    est = unname(sm[term, "Estimate"]),
    se = unname(sm[term, "Std. Error"]),
    p = unname(p_val)
  )
}

get_var_comp <- function(model) {
  vc <- as.data.frame(VarCorr(model))
  tau <- vc$vcov[vc$grp == "city" & vc$var1 == "(Intercept)"]
  sigma <- sigma(model)^2
  c(tau = tau[1], sigma = sigma)
}

calc_r2_rb <- function(null_model, model) {
  v0 <- get_var_comp(null_model)
  v1 <- get_var_comp(model)
  r2_within <- (v0["sigma"] - v1["sigma"]) / v0["sigma"]
  r2_between <- (v0["tau"] - v1["tau"]) / v0["tau"]
  r2_total <- ((v0["sigma"] + v0["tau"]) - (v1["sigma"] + v1["tau"])) /
    (v0["sigma"] + v0["tau"])
  setNames(
    c(unname(r2_within), unname(r2_between), unname(r2_total)),
    c("r2_within", "r2_between", "r2_total")
  )
}

normalize_city <- function(x) {
  x <- as.character(x)
  x <- str_trim(x)
  str_replace(x, "\u5e02.*$", "")
}

read_weibo_year <- function(year) {
  dir_path <- resolve_existing_path(
    candidates = c(
      file.path("data", "raw", "weibo", as.character(year)),
      file.path("data", "\u5fae\u535a\u6570\u636e", as.character(year))
    ),
    error_message = paste0("No Weibo directory found for year ", year)
  )
  files <- list.files(dir_path, pattern = "\\.csv$", full.names = TRUE)
  if (length(files) == 0) stop("No Weibo files found for year ", year)

  sample_cols <- names(fread(files[[1]], nrows = 0, showProgress = FALSE))
  selected_cols <- vapply(
    names(weibo_col_candidates),
    FUN.VALUE = character(1),
    function(target) {
      resolve_existing_name(
        candidates = weibo_col_candidates[[target]],
        available = sample_cols,
        error_message = paste0(
          "Cannot find required Weibo column for target '", target, "' in file: ", files[[1]]
        )
      )
    }
  )

  rbindlist(lapply(files, function(f) {
    dt <- fread(f, select = unname(selected_cols), showProgress = FALSE)
    setnames(dt, old = unname(selected_cols), new = names(selected_cols))
    dt[, year := as.character(year)]
    dt
  }), use.names = TRUE, fill = TRUE)
}

read_city_files <- function() {
  xlsx_files <- list.files(
    file.path("data", "raw", "city_level"),
    pattern = "\\.xlsx$",
    full.names = TRUE
  )
  city_year_files <- list()
  clan_file <- NULL
  for (f in xlsx_files) {
    cols <- names(read_xlsx(f, n_max = 0))
    if (all(c("year", "province", "city", "pd", "gdp", "noarg") %in% cols)) {
      year_val <- str_extract(basename(f), "20\\d{2}")
      city_year_files[[year_val]] <- f
    } else if (all(c("city", "fertility", "RSB", "non_agr", "clan", "rice") %in% cols)) {
      clan_file <- f
    }
  }
  if (is.null(clan_file)) stop("Cannot find clan city-level file.")
  if (is.null(city_year_files[["2011"]]) || is.null(city_year_files[["2012"]])) {
    stop("Cannot find 2011/2012 city-level files.")
  }
  list(city_year_files = city_year_files, clan_file = clan_file)
}

fit_models_method4 <- function(use_dt) {
  ctrl <- lmerControl(optimizer = "bobyqa")
  model1 <- lmer(collectivism ~ (1 | city), data = use_dt, control = ctrl)
  model2 <- lmer(
    collectivism ~ clan.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )
  model3 <- lmer(
    collectivism ~ fertility.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )
  model4 <- lmer(
    collectivism ~ RSB.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )

  model5 <- lmer(individualism ~ (1 | city), data = use_dt, control = ctrl)
  model6 <- lmer(
    individualism ~ fertility.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )
  model7 <- lmer(
    individualism ~ clan.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )
  model8 <- lmer(
    individualism ~ RSB.x + noarg + rice.x + gdp.x + lon.x + lat.x + pd.x + f + (1 | city),
    data = use_dt, control = ctrl
  )
  list(model1, model2, model3, model4, model5, model6, model7, model8)
}

build_table_matrix <- function(models, year_label) {
  model_names <- c(
    "Model 1 (null)", "Model 2", "Model 3", "Model 4",
    "Model 5 (null)", "Model 6", "Model 7", "Model 8"
  )
  mat <- matrix("", nrow = 29, ncol = 9)
  colnames(mat) <- c("", model_names)
  mat[1, ] <- c(
    "",
    rep(paste0(year_label, " Collectivism"), 4),
    rep(paste0(year_label, " Individualism"), 4)
  )
  mat[2, ] <- c("", model_names)

  mat[3, 1] <- "Intercept (gamma00)"
  mat[4, 1] <- "Intercept (gamma00)"
  for (i in seq_along(models)) {
    out <- extract_coef(models[[i]], "(Intercept)")
    mat[3, i + 1] <- fmt_est(out$est, out$p)
    mat[4, i + 1] <- fmt_se(out$se)
  }

  fill_term <- function(term, row_est, row_se, model_idx) {
    for (i in model_idx) {
      out <- extract_coef(models[[i]], term)
      mat[row_est, i + 1] <<- fmt_est(out$est, out$p)
      mat[row_se, i + 1] <<- fmt_se(out$se)
    }
  }

  mat[5, 1] <- "City level"
  mat[6, 1] <- "Surname concentration"
  mat[7, 1] <- "Surname concentration"
  fill_term("clan.x", 6, 7, c(2, 7))

  mat[8, 1] <- "Fertility rate"
  mat[9, 1] <- "Fertility rate"
  fill_term("fertility.x", 8, 9, c(3, 6))

  mat[10, 1] <- "Sex ratio"
  mat[11, 1] <- "Sex ratio"
  fill_term("RSB.x", 10, 11, c(4, 8))

  mat[12, 1] <- "PNAP"
  mat[13, 1] <- "PNAP"
  fill_term("noarg", 12, 13, c(2, 3, 4, 6, 7, 8))

  mat[14, 1] <- "Rice planting ratio"
  mat[15, 1] <- "Rice planting ratio"
  fill_term("rice.x", 14, 15, c(2, 3, 4, 6, 7, 8))

  mat[16, 1] <- "GDP"
  mat[17, 1] <- "GDP"
  fill_term("gdp.x", 16, 17, c(2, 3, 4, 6, 7, 8))

  mat[18, 1] <- "Longitude"
  mat[19, 1] <- "Longitude"
  fill_term("lon.x", 18, 19, c(2, 3, 4, 6, 7, 8))

  mat[20, 1] <- "Latitude"
  mat[21, 1] <- "Latitude"
  fill_term("lat.x", 20, 21, c(2, 3, 4, 6, 7, 8))

  mat[22, 1] <- "Population density"
  mat[23, 1] <- "Population density"
  fill_term("pd.x", 22, 23, c(2, 3, 4, 6, 7, 8))

  mat[24, 1] <- "Individual level"
  mat[25, 1] <- "Female"
  mat[26, 1] <- "Female"
  fill_term("f", 25, 26, c(2, 3, 4, 6, 7, 8))

  r2_collect <- list(
    calc_r2_rb(models[[1]], models[[2]]),
    calc_r2_rb(models[[1]], models[[3]]),
    calc_r2_rb(models[[1]], models[[4]])
  )
  r2_indiv <- list(
    calc_r2_rb(models[[5]], models[[6]]),
    calc_r2_rb(models[[5]], models[[7]]),
    calc_r2_rb(models[[5]], models[[8]])
  )
  mat[27, 1] <- "R2within"
  mat[28, 1] <- "R2between"
  mat[29, 1] <- "R2total"

  cols_collect <- c(3, 4, 5)
  cols_indiv <- c(7, 8, 9)
  for (k in seq_along(r2_collect)) {
    mat[27, cols_collect[k]] <- fmt_num(r2_collect[[k]]["r2_within"])
    mat[28, cols_collect[k]] <- fmt_num(r2_collect[[k]]["r2_between"])
    mat[29, cols_collect[k]] <- fmt_num(r2_collect[[k]]["r2_total"])
  }
  for (k in seq_along(r2_indiv)) {
    mat[27, cols_indiv[k]] <- fmt_num(r2_indiv[[k]]["r2_within"])
    mat[28, cols_indiv[k]] <- fmt_num(r2_indiv[[k]]["r2_between"])
    mat[29, cols_indiv[k]] <- fmt_num(r2_indiv[[k]]["r2_total"])
  }
  mat
}

table_to_md <- function(mat, caption) {
  df <- as.data.frame(mat, stringsAsFactors = FALSE)
  names(df)[1] <- " "
  align <- paste(rep(":---:", ncol(df)), collapse = "|")
  header <- paste(names(df), collapse = "|")
  lines <- c(
    paste0("**", caption, "**"),
    "",
    paste0("|", header, "|"),
    paste0("|", align, "|")
  )
  for (i in seq_len(nrow(df))) {
    lines <- c(lines, paste0("|", paste(df[i, ], collapse = "|"), "|"))
  }
  lines
}

cor_sig_stars <- function(p) {
  if (is.na(p)) return("")
  if (p < .001) return("***")
  if (p < .01) return("**")
  if (p < .05) return("*")
  ""
}

pairwise_cor_with_p <- function(df) {
  m <- as.matrix(df)
  vars <- colnames(m)
  r <- cor(m, use = "pairwise.complete.obs", method = "pearson")
  p <- matrix(NA_real_, nrow = ncol(m), ncol = ncol(m), dimnames = list(vars, vars))
  for (i in seq_len(ncol(m))) {
    for (j in seq_len(ncol(m))) {
      if (i == j) {
        p[i, j] <- 0
      } else {
        ct <- suppressWarnings(cor.test(m[, i], m[, j], method = "pearson"))
        p[i, j] <- ct$p.value
      }
    }
  }
  list(r = r, p = p)
}

cor_to_md <- function(cor_obj, caption) {
  r <- cor_obj$r
  p <- cor_obj$p
  vars <- colnames(r)
  rows <- list()
  header <- paste(c("Variable", vars), collapse = "|")
  align <- paste(c(":---", rep(":---:", length(vars))), collapse = "|")
  rows[[1]] <- paste0("**", caption, "**")
  rows[[2]] <- ""
  rows[[3]] <- paste0("|", header, "|")
  rows[[4]] <- paste0("|", align, "|")
  for (i in seq_along(vars)) {
    vals <- c(vars[i], sapply(seq_along(vars), function(j) {
      paste0(fmt_num(r[i, j]), cor_sig_stars(p[i, j]))
    }))
    rows[[length(rows) + 1]] <- paste0("|", paste(vals, collapse = "|"), "|")
  }
  unlist(rows)
}

run_method4_year <- function(year_value, final_data, city_files) {
  ana_data <- final_data[year == as.character(year_value)]
  city_list_100 <- ana_data[, .N, by = city][N > 30, .(city)]
  ana_data <- ana_data[city %in% city_list_100$city]

  city_data <- as.data.table(read_xlsx(city_files$clan_file))
  city_yr <- as.data.table(read_xlsx(city_files$city_year_files[[as.character(year_value)]]))

  if (!("lon" %in% names(city_data))) {
    lon_col <- names(city_data)[names(city_data) %in% c("\u7ecf\u5ea6")]
    if (length(lon_col) > 0) setnames(city_data, lon_col[[1]], "lon")
  }
  if (!("lat" %in% names(city_data))) {
    lat_col <- names(city_data)[names(city_data) %in% c("\u7eac\u5ea6")]
    if (length(lat_col) > 0) setnames(city_data, lat_col[[1]], "lat")
  }

  city_data[, city := normalize_city(city)]
  city_yr[, city := normalize_city(city)]

  city_yr[, pd := as.numeric(pd)]
  city_yr[, gdp := as.numeric(gdp)]
  city_yr[, noarg := as.numeric(noarg)]
  city_yr[is.na(pd), pd := mean(pd, na.rm = TRUE)]
  city_yr[is.na(gdp), gdp := mean(gdp, na.rm = TRUE)]
  city_yr[is.na(noarg), noarg := 0]

  citylist <- ana_data[, .N, by = city][N > 30, .(city)]

  cityall <- merge(citylist, city_data, by = "city", all = FALSE)
  cityall <- cityall[!duplicated(city)]
  cityall <- merge(cityall, city_yr, by = "city", all = FALSE)
  cityall <- cityall[, .(city, fertility, RSB, clan, rice, lon, lat, pd, gdp, noarg)]

  city_scaled <- as.data.table(scale(cityall[, -"city"]))
  city_scaled[, city := cityall$city]
  setcolorder(city_scaled, c("city", "fertility", "RSB", "clan", "rice", "lon", "lat", "pd", "gdp", "noarg"))

  setnames(
    city_scaled,
    c("fertility", "RSB", "clan", "rice", "lon", "lat", "pd", "gdp"),
    c("fertility.x", "RSB.x", "clan.x", "rice.x", "lon.x", "lat.x", "pd.x", "gdp.x")
  )

  use <- merge(city_scaled, ana_data, by = "city", all = FALSE)
  use[, city := as.factor(city)]

  models <- fit_models_method4(use)
  list(
    models = models,
    table = build_table_matrix(models, as.character(year_value)),
    n_city = uniqueN(use$city),
    n_individual = nrow(use),
    cityall = cityall,
    use = use
  )
}

message("Step 1/5: Reading Weibo 2011/2012 data ...")
weibo_2011 <- read_weibo_year(2011)
weibo_2012 <- read_weibo_year(2012)
weibo_all <- rbindlist(list(weibo_2011, weibo_2012), use.names = TRUE)
rm(weibo_2011, weibo_2012); gc()

weibo_all[, uid := tstrsplit(txt, "_", fixed = TRUE, keep = 1L)]
scale_vars <- c("individualism", "collectivism", "control_words", "i", "we", "you")
weibo_all[, (scale_vars) := lapply(.SD, function(x) as.numeric(scale(x))), by = year, .SDcols = scale_vars]

message("Step 2/5: Reading uid info and cleaning ...")
uid_path <- resolve_existing_path(
  candidates = c(file.path("data", "raw", "AllUidV5.txt"), "AllUidV5.txt"),
  error_message = "Cannot find AllUidV5.txt in data/raw or project root."
)
uid_info <- fread(
  uid_path,
  sep = "\t",
  fill = TRUE,
  quote = "",
  select = c("V1", "V5", "V11"),
  colClasses = c(V1 = "character", V5 = "character", V11 = "character"),
  showProgress = FALSE
)
setnames(uid_info, c("V1", "V5", "V11"), c("uid", "gender", "area"))
uid_info[, c("province", "city") := tstrsplit(area, " ", fixed = TRUE, keep = 1:2)]
uid_clean <- uid_info[!province %in% excluded_provinces]
uid_clean <- uid_clean[complete.cases(uid_clean[, .(uid, gender, area, province, city)])]
uid_clean[, city := normalize_city(city)]

message("Step 3/5: Building final individual-level data ...")
final_data <- merge(
  weibo_all[, .(uid, year, individualism, collectivism, control_words, i, we, you)],
  uid_clean[, .(uid, gender, province, city)],
  by = "uid",
  all = FALSE
)
final_data[, f := fifelse(gender == "f", 1, 0)]

city_files <- read_city_files()

message("Step 4/5: Running Method 4 models for 2011 and 2012 ...")
res2011 <- run_method4_year(2011, final_data, city_files)
res2012 <- run_method4_year(2012, final_data, city_files)

message("Step 4.5/5: Running correlation analyses ...")
city_cor2011 <- pairwise_cor_with_p(as.data.frame(res2011$cityall[, -"city"]))
city_cor2012 <- pairwise_cor_with_p(as.data.frame(res2012$cityall[, -"city"]))

ind_cor2011 <- cor.test(res2011$use$collectivism, res2011$use$individualism, method = "pearson")
ind_cor2012 <- cor.test(res2012$use$collectivism, res2012$use$individualism, method = "pearson")

message("Step 5/5: Writing Excel tables ...")
dir.create("results", showWarnings = FALSE)
out_file <- file.path("results", "table4_table5_results.xlsx")

# Create workbook
wb <- createWorkbook()

# === Sheet 1: Summary ===
addWorksheet(wb, "Summary")

# Title
title_style <- createStyle(fontSize = 14, textDecoration = "bold")
writeData(wb, "Summary", "Study 2 Results Summary", startRow = 1, startCol = 1)
addStyle(wb, "Summary", title_style, rows = 1, cols = 1)

# Individual-level correlations
writeData(wb, "Summary", "Individual-level Correlations", startRow = 3, startCol = 1)
addStyle(wb, "Summary", createStyle(textDecoration = "bold"), rows = 3, cols = 1)

ind_summary <- data.frame(
  Year = c(2011, 2012),
  r = c(unname(ind_cor2011$estimate), unname(ind_cor2012$estimate)),
  CI_lower = c(ind_cor2011$conf.int[1], ind_cor2012$conf.int[1]),
  CI_upper = c(ind_cor2011$conf.int[2], ind_cor2012$conf.int[2]),
  p_value = c(ind_cor2011$p.value, ind_cor2012$p.value)
)
writeData(wb, "Summary", ind_summary, startRow = 4, startCol = 1)

# === Sheet 2: Table 4 (2011 HLM) ===
addWorksheet(wb, "Table4_2011")
writeData(wb, "Table4_2011",
  sprintf("Table 4: 2011 HLM Results (Ncity = %d, Nindividual = %d)",
    res2011$n_city, res2011$n_individual),
  startRow = 1, startCol = 1)
addStyle(wb, "Table4_2011", title_style, rows = 1, cols = 1)

writeData(wb, "Table4_2011", res2011$table, startRow = 3, startCol = 1,
          colNames = TRUE, rowNames = FALSE)

header_style <- createStyle(textDecoration = "bold",
                            fgFill = "#D3D3D3",
                            border = "TopBottomLeftRight")
addStyle(wb, "Table4_2011", header_style, rows = 3,
         cols = 1:ncol(res2011$table), gridExpand = TRUE)

# === Sheet 3: Table 5 (2012 HLM) ===
addWorksheet(wb, "Table5_2012")
writeData(wb, "Table5_2012",
  sprintf("Table 5: 2012 HLM Results (Ncity = %d, Nindividual = %d)",
    res2012$n_city, res2012$n_individual),
  startRow = 1, startCol = 1)
addStyle(wb, "Table5_2012", title_style, rows = 1, cols = 1)

writeData(wb, "Table5_2012", res2012$table, startRow = 3, startCol = 1,
          colNames = TRUE, rowNames = FALSE)
addStyle(wb, "Table5_2012", header_style, rows = 3,
         cols = 1:ncol(res2012$table), gridExpand = TRUE)

# === Sheet 4: City Correlations 2011 ===
addWorksheet(wb, "City_Corr_2011")
writeData(wb, "City_Corr_2011", "City-level Correlation Matrix (2011)",
          startRow = 1, startCol = 1)
addStyle(wb, "City_Corr_2011", title_style, rows = 1, cols = 1)

city_cor_2011_combined <- city_cor2011$r
for (i in 1:nrow(city_cor_2011_combined)) {
  for (j in 1:ncol(city_cor_2011_combined)) {
    r_val <- city_cor2011$r[i, j]
    p_val <- city_cor2011$p[i, j]
    stars <- ifelse(p_val < 0.001, "***",
                   ifelse(p_val < 0.01, "**",
                         ifelse(p_val < 0.05, "*", "")))
    city_cor_2011_combined[i, j] <- sprintf("%.3f%s", r_val, stars)
  }
}
writeData(wb, "City_Corr_2011", city_cor_2011_combined,
          startRow = 3, startCol = 1, rowNames = TRUE)

# === Sheet 5: City Correlations 2012 ===
addWorksheet(wb, "City_Corr_2012")
writeData(wb, "City_Corr_2012", "City-level Correlation Matrix (2012)",
          startRow = 1, startCol = 1)
addStyle(wb, "City_Corr_2012", title_style, rows = 1, cols = 1)

city_cor_2012_combined <- city_cor2012$r
for (i in 1:nrow(city_cor_2012_combined)) {
  for (j in 1:ncol(city_cor_2012_combined)) {
    r_val <- city_cor2012$r[i, j]
    p_val <- city_cor2012$p[i, j]
    stars <- ifelse(p_val < 0.001, "***",
                   ifelse(p_val < 0.01, "**",
                         ifelse(p_val < 0.05, "*", "")))
    city_cor_2012_combined[i, j] <- sprintf("%.3f%s", r_val, stars)
  }
}
writeData(wb, "City_Corr_2012", city_cor_2012_combined,
          startRow = 3, startCol = 1, rowNames = TRUE)

# Save workbook
saveWorkbook(wb, out_file, overwrite = TRUE)

write.csv(city_cor2011$r, file.path("results", "city_corr_2011_r.csv"))
write.csv(city_cor2011$p, file.path("results", "city_corr_2011_p.csv"))
write.csv(city_cor2012$r, file.path("results", "city_corr_2012_r.csv"))
write.csv(city_cor2012$p, file.path("results", "city_corr_2012_p.csv"))

ind_out <- data.frame(
  year = c(2011, 2012),
  r = c(unname(ind_cor2011$estimate), unname(ind_cor2012$estimate)),
  conf_low = c(ind_cor2011$conf.int[1], ind_cor2012$conf.int[1]),
  conf_high = c(ind_cor2011$conf.int[2], ind_cor2012$conf.int[2]),
  p_value = c(ind_cor2011$p.value, ind_cor2012$p.value)
)
write.csv(ind_out, file.path("results", "individual_cor_tests.csv"), row.names = FALSE)

message("Done. Results written to: ", out_file)
