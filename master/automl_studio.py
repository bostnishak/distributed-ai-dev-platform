from __future__ import annotations

import math
from typing import Any

import numpy as np


def _try_parse_float(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float, np.number)):
        fval = float(val)
        return None if (math.isnan(fval) or math.isinf(fval)) else fval
    if isinstance(val, str):
        stripped = val.strip()
        if not stripped:
            return None
        normalized = stripped.replace(",", "") if stripped.count(",") == 1 and "." in stripped else stripped
        try:
            fval = float(normalized)
            return None if (math.isnan(fval) or math.isinf(fval)) else fval
        except ValueError:
            return None
    return None


def _is_missing(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return True
    if isinstance(val, str) and val.strip().lower() in {"", "na", "n/a", "null", "none", "nan"}:
        return True
    return False


def profile_dataset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "column_count": 0,
            "numeric_columns": [],
            "categorical_columns": [],
            "missing_counts": {},
            "numeric_stats": {},
            "categorical_stats": {},
            "correlation_matrix": {},
            "anomalies": [],
        }

    all_cols: list[str] = []
    for row in rows:
        for k in row.keys():
            if k not in all_cols:
                all_cols.append(str(k))

    row_count = len(rows)
    missing_counts: dict[str, int] = {col: 0 for col in all_cols}
    numeric_values_by_col: dict[str, list[tuple[int, float]]] = {col: [] for col in all_cols}
    raw_values_by_col: dict[str, list[str]] = {col: [] for col in all_cols}

    for r_idx, row in enumerate(rows):
        for col in all_cols:
            val = row.get(col)
            if _is_missing(val):
                missing_counts[col] += 1
                continue
            parsed = _try_parse_float(val)
            if parsed is not None:
                numeric_values_by_col[col].append((r_idx, parsed))
            raw_values_by_col[col].append(str(val).strip())

    numeric_columns: list[str] = []
    categorical_columns: list[str] = []

    for col in all_cols:
        non_missing = row_count - missing_counts[col]
        num_count = len(numeric_values_by_col[col])
        if non_missing > 0 and (num_count / non_missing) >= 0.8:
            numeric_columns.append(col)
        else:
            categorical_columns.append(col)

    numeric_stats: dict[str, dict[str, float]] = {}
    anomalies_by_row: dict[int, list[str]] = {}

    for col in numeric_columns:
        pairs = numeric_values_by_col[col]
        if not pairs:
            continue
        arr = np.array([v for _, v in pairs], dtype=np.float64)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr, ddof=0))
        min_val = float(np.min(arr))
        q25 = float(np.percentile(arr, 25))
        median_val = float(np.median(arr))
        q75 = float(np.percentile(arr, 75))
        max_val = float(np.max(arr))
        iqr_val = q75 - q25

        numeric_stats[col] = {
            "count": float(len(arr)),
            "mean": round(mean_val, 6),
            "std": round(std_val, 6),
            "min": round(min_val, 6),
            "q25": round(q25, 6),
            "median": round(median_val, 6),
            "q75": round(q75, 6),
            "max": round(max_val, 6),
            "iqr": round(iqr_val, 6),
        }

        lower_iqr = q25 - 1.5 * iqr_val
        upper_iqr = q75 + 1.5 * iqr_val

        for r_idx, val in pairs:
            reasons: list[str] = []
            if std_val > 1e-12:
                z_score = abs(val - mean_val) / std_val
                if z_score > 2.5:
                    reasons.append(f"{col}: z_score={z_score:.2f} (val={val})")
            if iqr_val > 1e-12 and (val < lower_iqr or val > upper_iqr):
                reasons.append(f"{col}: iqr_outlier val={val} outside [{lower_iqr:.2f}, {upper_iqr:.2f}]")
            if reasons:
                anomalies_by_row.setdefault(r_idx, []).extend(reasons)

    categorical_stats: dict[str, dict[str, Any]] = {}
    for col in categorical_columns:
        vals = raw_values_by_col[col]
        counts: dict[str, int] = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        sorted_top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        categorical_stats[col] = {
            "unique_count": len(counts),
            "top_values": [{"value": k, "count": c} for k, c in sorted_top],
        }

    correlation_matrix: dict[str, dict[str, float]] = {c: {} for c in numeric_columns}
    col_dense_arrays: dict[str, np.ndarray] = {}
    for col in numeric_columns:
        mean_fill = numeric_stats.get(col, {}).get("mean", 0.0)
        vec = np.full(row_count, mean_fill, dtype=np.float64)
        for r_idx, val in numeric_values_by_col[col]:
            vec[r_idx] = val
        col_dense_arrays[col] = vec

    for i, col_a in enumerate(numeric_columns):
        vec_a = col_dense_arrays[col_a]
        std_a = float(np.std(vec_a))
        for j, col_b in enumerate(numeric_columns):
            if i == j:
                correlation_matrix[col_a][col_b] = 1.0
                continue
            vec_b = col_dense_arrays[col_b]
            std_b = float(np.std(vec_b))
            if std_a <= 1e-12 or std_b <= 1e-12:
                correlation_matrix[col_a][col_b] = 0.0
            else:
                corr = float(np.corrcoef(vec_a, vec_b)[0, 1])
                if math.isnan(corr):
                    corr = 0.0
                correlation_matrix[col_a][col_b] = round(corr, 6)

    anomalies = [
        {
            "row_index": r_idx,
            "reasons": reasons,
            "row": rows[r_idx],
        }
        for r_idx, reasons in sorted(anomalies_by_row.items())
    ]

    return {
        "row_count": row_count,
        "column_count": len(all_cols),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "missing_counts": missing_counts,
        "numeric_stats": numeric_stats,
        "categorical_stats": categorical_stats,
        "correlation_matrix": correlation_matrix,
        "anomalies": anomalies,
    }


def what_if_predict(
    weights: dict[str, float],
    feature_means: dict[str, float],
    overrides: dict[str, float] | None = None,
) -> float:
    overrides = overrides or {}
    pred = float(weights.get("__intercept__", 0.0))
    for feat_name, mean_val in feature_means.items():
        val = float(overrides.get(feat_name, mean_val))
        coef = float(weights.get(feat_name, 0.0))
        pred += coef * val
    if "__time_index__" in weights and "__time_index__" not in feature_means:
        t_val = float(overrides.get("__time_index__", 0.0))
        pred += float(weights["__time_index__"]) * t_val
    return round(pred, 6)


def train_and_forecast(
    rows: list[dict[str, Any]],
    target_col: str,
    horizon: int = 5,
    l2_alpha: float = 1e-2,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("Dataset `rows` cannot be empty.")
    if horizon < 1:
        raise ValueError("`horizon` must be at least 1.")

    profile = profile_dataset(rows)
    numeric_cols = profile["numeric_columns"]
    if target_col not in numeric_cols:
        raise ValueError(f"Target column `{target_col}` not found among numeric columns: {numeric_cols}")

    feature_cols = [c for c in numeric_cols if c != target_col]

    valid_rows: list[dict[str, float]] = []
    col_means: dict[str, float] = {
        c: profile["numeric_stats"].get(c, {}).get("mean", 0.0) for c in numeric_cols
    }

    for row in rows:
        target_val = _try_parse_float(row.get(target_col))
        if target_val is None:
            continue
        record: dict[str, float] = {target_col: target_val}
        for fcol in feature_cols:
            fval = _try_parse_float(row.get(fcol))
            record[fcol] = col_means[fcol] if fval is None else fval
        valid_rows.append(record)

    n_samples = len(valid_rows)
    if n_samples < 3:
        raise ValueError(f"Need at least 3 valid numeric rows for `{target_col}`, found {n_samples}.")

    model_feature_names = [*feature_cols, "__time_index__"]
    n_features = len(model_feature_names)

    x_raw = np.zeros((n_samples, n_features), dtype=np.float64)
    y_vec = np.zeros(n_samples, dtype=np.float64)

    for idx, rec in enumerate(valid_rows):
        y_vec[idx] = rec[target_col]
        for f_idx, fcol in enumerate(feature_cols):
            x_raw[idx, f_idx] = rec[fcol]
        x_raw[idx, -1] = float(idx)

    # Design matrix with intercept column first: [1, f_1, ..., f_k, time_index]
    x_design = np.column_stack([np.ones(n_samples, dtype=np.float64), x_raw])

    # Ridge regression via augmented linear least squares:
    # minimize ||X w - y||_2^2 + alpha * ||w_no_intercept||_2^2
    reg_matrix = np.sqrt(l2_alpha) * np.eye(n_features + 1, dtype=np.float64)
    reg_matrix[0, 0] = 0.0  # Do not regularize intercept
    x_aug = np.vstack([x_design, reg_matrix])
    y_aug = np.concatenate([y_vec, np.zeros(n_features + 1, dtype=np.float64)])

    theta, _, _, _ = np.linalg.lstsq(x_aug, y_aug, rcond=None)

    y_pred = x_design @ theta
    residuals = y_vec - y_pred

    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y_vec - np.mean(y_vec)) ** 2))
    r2_score = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))
    dof = max(1, n_samples - (n_features + 1))
    residual_std = float(np.sqrt(ss_res / dof))

    weights: dict[str, float] = {"__intercept__": round(float(theta[0]), 6)}
    for f_idx, fname in enumerate(model_feature_names):
        weights[fname] = round(float(theta[f_idx + 1]), 6)

    feature_means: dict[str, float] = {}
    raw_importances: dict[str, float] = {}
    for f_idx, fname in enumerate(model_feature_names):
        col_vec = x_raw[:, f_idx]
        feature_means[fname] = round(float(np.mean(col_vec)), 6)
        col_std = float(np.std(col_vec))
        coef = abs(float(theta[f_idx + 1]))
        raw_importances[fname] = coef * (col_std if col_std > 1e-12 else 1.0)

    total_imp = sum(raw_importances.values())
    if total_imp > 1e-12:
        feature_importance = {
            k: round(v / total_imp, 6)
            for k, v in sorted(raw_importances.items(), key=lambda kv: -kv[1])
        }
    else:
        uniform = round(1.0 / max(1, len(raw_importances)), 6)
        feature_importance = {k: uniform for k in raw_importances}

    # Estimate linear drift per feature over time for multi-step horizon forecasting
    t_vec = np.arange(n_samples, dtype=np.float64)
    t_design = np.column_stack([np.ones(n_samples, dtype=np.float64), t_vec])
    feature_trend_params: dict[str, np.ndarray] = {}
    for f_idx, fcol in enumerate(feature_cols):
        f_params, _, _, _ = np.linalg.lstsq(t_design, x_raw[:, f_idx], rcond=None)
        feature_trend_params[fcol] = f_params

    forecasts: list[dict[str, Any]] = []
    z_95 = 1.96
    for step in range(1, horizon + 1):
        future_t = float(n_samples - 1 + step)
        step_overrides: dict[str, float] = {"__time_index__": future_t}
        for fcol in feature_cols:
            f_params = feature_trend_params[fcol]
            projected_f = float(f_params[0] + f_params[1] * future_t)
            step_overrides[fcol] = projected_f

        point_pred = what_if_predict(weights, feature_means, step_overrides)
        ci_half_width = z_95 * residual_std * math.sqrt(1.0 + (step / n_samples))
        forecasts.append(
            {
                "step": step,
                "time_index": int(future_t),
                "prediction": round(point_pred, 6),
                "lower_ci": round(point_pred - ci_half_width, 6),
                "upper_ci": round(point_pred + ci_half_width, 6),
                "projected_features": {k: round(v, 6) for k, v in step_overrides.items()},
            }
        )

    return {
        "target_column": target_col,
        "sample_count": n_samples,
        "feature_columns": model_feature_names,
        "metrics": {
            "r2": round(r2_score, 6),
            "rmse": round(rmse, 6),
            "mae": round(mae, 6),
            "residual_std": round(residual_std, 6),
        },
        "weights": weights,
        "feature_means": feature_means,
        "feature_importance": feature_importance,
        "forecasts": forecasts,
    }
