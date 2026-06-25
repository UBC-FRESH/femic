#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

arg_value <- function(flag, default = NULL) {
  idx <- match(flag, args)
  if (is.na(idx) || idx == length(args)) {
    return(default)
  }
  args[[idx + 1]]
}

query_file <- arg_value("--query-file")
summary_csv <- arg_value("--summary-csv")
manifest_json <- arg_value("--manifest-json")
limit <- as.integer(arg_value("--limit", "5"))
local_lib <- arg_value("--lib", "runtime/phase75/r-lib")

if (is.null(query_file) || is.null(summary_csv) || is.null(manifest_json)) {
  stop(
    "Usage: phase75_bcdata_resolve_baseline.r --query-file PATH ",
    "--summary-csv PATH --manifest-json PATH [--limit N] [--lib PATH]",
    call. = FALSE
  )
}

if (dir.exists(local_lib)) {
  .libPaths(c(normalizePath(local_lib, winslash = "/"), .libPaths()))
}

suppressPackageStartupMessages({
  library(bcdata)
  library(jsonlite)
})

read_queries <- function(path) {
  lines <- readLines(path, warn = FALSE, encoding = "UTF-8")
  lines <- trimws(lines)
  lines <- lines[nzchar(lines)]
  lines <- lines[!startsWith(lines, "#")]
  unique(lines)
}

as_text <- function(value) {
  if (is.null(value) || length(value) == 0 || is.na(value[[1]])) {
    return("")
  }
  as.character(value[[1]])
}

record_url <- function(record) {
  name <- as_text(record[["name"]])
  if (!nzchar(name)) {
    return("")
  }
  paste0("https://catalogue.data.gov.bc.ca/dataset/", name)
}

resource_list <- function(record) {
  resources <- record[["resources"]]
  if (is.null(resources)) {
    return(list())
  }
  resources
}

resource_value <- function(resource, field) {
  as_text(resource[[field]])
}

resource_object_names <- function(record) {
  values <- vapply(resource_list(record), resource_value, character(1), field = "object_name")
  values[nzchar(values)]
}

resource_classes <- function(record) {
  resources <- resource_list(record)
  if (length(resources) == 0) {
    return("")
  }
  classes <- vapply(resources, function(resource) {
    access <- tolower(resource_value(resource, "resource_access_method"))
    storage <- tolower(resource_value(resource, "resource_storage_location"))
    url <- resource_value(resource, "url")
    bcdc_type <- tolower(resource_value(resource, "bcdc_type"))
    resource_type <- tolower(resource_value(resource, "resource_type"))
    if (nzchar(url) && !grepl("bc geographic warehouse", storage, fixed = TRUE)) {
      return("direct_data_download")
    }
    if (grepl("bc geographic warehouse", storage, fixed = TRUE) ||
        grepl("indirect", access, fixed = TRUE)) {
      return("indirect_custom_download")
    }
    if (bcdc_type %in% c("webservice", "web service") ||
        resource_type %in% c("api", "service")) {
      return("service")
    }
    if (resource_type %in% c("documentation", "document")) {
      return("supporting_document")
    }
    "other"
  }, character(1))
  paste(sort(unique(classes)), collapse = "|")
}

has_direct_download <- function(record) {
  any(vapply(resource_list(record), function(resource) {
    url <- resource_value(resource, "url")
    storage <- tolower(resource_value(resource, "resource_storage_location"))
    nzchar(url) && !grepl("bc geographic warehouse", storage, fixed = TRUE)
  }, logical(1)))
}

has_dwds_candidate <- function(record) {
  any(vapply(resource_list(record), function(resource) {
    storage <- tolower(resource_value(resource, "resource_storage_location"))
    object_name <- resource_value(resource, "object_name")
    grepl("bc geographic warehouse", storage, fixed = TRUE) && nzchar(object_name)
  }, logical(1)))
}

has_wfs_queryable <- function(record) {
  any(vapply(resource_list(record), function(resource) {
    url <- tolower(resource_value(resource, "url"))
    bcdc_type <- tolower(resource_value(resource, "bcdc_type"))
    grepl("ows", url, fixed = TRUE) ||
      grepl("wfs", url, fixed = TRUE) ||
      bcdc_type %in% c("webservice", "web service")
  }, logical(1)))
}

match_status <- function(query, record) {
  if (is.null(record)) {
    return("no_hit")
  }
  q <- tolower(query)
  title <- tolower(as_text(record[["title"]]))
  name <- tolower(as_text(record[["name"]]))
  object_names <- tolower(resource_object_names(record))
  if (q %in% c(title, name, object_names)) {
    return("exact_hit")
  }
  if (any(grepl(q, object_names, fixed = TRUE)) ||
      grepl(q, title, fixed = TRUE) ||
      grepl(q, name, fixed = TRUE)) {
    return("strong_hit")
  }
  "weak_hit"
}

summarize_query <- function(query) {
  start <- proc.time()[["elapsed"]]
  error <- NULL
  records <- tryCatch(
    bcdc_search(query, n = limit),
    error = function(e) {
      error <<- conditionMessage(e)
      list()
    }
  )
  elapsed <- proc.time()[["elapsed"]] - start
  records_list <- as.list(records)
  top_record <- if (length(records_list) > 0) records_list[[1]] else NULL

  row <- data.frame(
    query_text = query,
    tool = "bcdata_search",
    status = if (!is.null(error)) "error" else match_status(query, top_record),
    match_count = length(records_list),
    top_title = if (is.null(top_record)) "" else as_text(top_record[["title"]]),
    top_name = if (is.null(top_record)) "" else as_text(top_record[["name"]]),
    top_id = if (is.null(top_record)) "" else as_text(top_record[["id"]]),
    top_object_name = if (is.null(top_record)) "" else paste(resource_object_names(top_record), collapse = "|"),
    top_url = if (is.null(top_record)) "" else record_url(top_record),
    resource_classes = if (is.null(top_record)) "" else resource_classes(top_record),
    wfs_queryable = if (is.null(top_record)) FALSE else has_wfs_queryable(top_record),
    direct_download = if (is.null(top_record)) FALSE else has_direct_download(top_record),
    dwds_candidate = if (is.null(top_record)) FALSE else has_dwds_candidate(top_record),
    runtime_seconds = elapsed,
    notes = if (is.null(error)) "" else error,
    stringsAsFactors = FALSE
  )

  manifest_records <- lapply(records_list, function(record) {
    list(
      id = as_text(record[["id"]]),
      name = as_text(record[["name"]]),
      title = as_text(record[["title"]]),
      dataset_page_url = record_url(record),
      object_names = resource_object_names(record),
      resource_classes = resource_classes(record),
      direct_download = has_direct_download(record),
      dwds_candidate = has_dwds_candidate(record),
      wfs_queryable = has_wfs_queryable(record)
    )
  })

  list(row = row, records = manifest_records)
}

queries <- read_queries(query_file)
results <- lapply(queries, summarize_query)
summary <- do.call(rbind, lapply(results, `[[`, "row"))
manifest <- list(
  generated_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  query_count = length(queries),
  limit = limit,
  bcdata_version = as.character(utils::packageVersion("bcdata")),
  results = Map(function(query, result) {
    list(query = query, records = result$records)
  }, queries, results)
)

dir.create(dirname(summary_csv), recursive = TRUE, showWarnings = FALSE)
utils::write.csv(summary, summary_csv, row.names = FALSE, na = "")
write_json(manifest, manifest_json, auto_unbox = TRUE, pretty = TRUE)

cat("queries:", length(queries), "\n")
cat("summary_csv:", normalizePath(summary_csv, winslash = "/", mustWork = FALSE), "\n")
cat("manifest_json:", normalizePath(manifest_json, winslash = "/", mustWork = FALSE), "\n")
