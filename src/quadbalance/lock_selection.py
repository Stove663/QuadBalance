"""Helpers for choosing the final locked configuration."""

from __future__ import annotations

STOCK_SPLIT_RETURN_EDGE_BP = 0.005  # 50bp
RETURN_EDGE_BP = STOCK_SPLIT_RETURN_EDGE_BP

LOCK_SELECTION_RANKING_KEYS = (
    "lockable over soft-pass (material needs_review without sign-off excluded)",
    "suitability rank for intended profile (suitable > caution > unsuitable) when supplied",
    "stocks sub-split risk-budget preference (60-40 over 40-60 when return edge < 50bp or extra CB reviews)",
    "same-return pending-cash preference (lower pending_cash_days when return edge < 50bp)",
    "higher annualized return",
    "lower absolute maximum drawdown",
    "higher QDII fill rate",
    "lexicographic configuration ID ascending",
)


def _as_bundle(bundle):
    if isinstance(bundle, tuple) and len(bundle) == 3:
        validation, config, result = bundle
        profile_classification = validation.profile_suitability.get("accumulation", {}).get("classification", "caution")
        qdii = getattr(result, "qdii_metrics", None)
        return {
            "validation_classification": profile_classification,
            "annualized_return": validation.metrics.annualized_return,
            "max_drawdown": validation.metrics.max_drawdown,
            "qdii_fill_rate": getattr(qdii, "qdii_fill_rate", 0.0) if qdii is not None else 0.0,
            "pending_cash_days": int(getattr(qdii, "pending_cash_days", 0) or 0) if qdii is not None else 0,
            "config_id": config.config_id,
            "lockable": getattr(validation, "lockable", False),
            "stock_sub_split": getattr(config, "stock_sub_split", "60-40"),
            "allocation_name": getattr(config, "allocation_name", ""),
            "material_cb_reviews": _material_cb_count(validation),
            "_raw": bundle,
        }
    if isinstance(bundle, dict):
        bundle = dict(bundle)
        validation = bundle.get("validation")
        config = bundle.get("config")
        sim_result = bundle.get("sim_result")
        if validation is not None:
            bundle.setdefault("lockable", getattr(validation, "lockable", False))
            bundle.setdefault("material_cb_reviews", _material_cb_count(validation))
            metrics = getattr(validation, "metrics", None)
            if metrics is not None:
                bundle.setdefault("annualized_return", metrics.annualized_return)
                bundle.setdefault("max_drawdown", metrics.max_drawdown)
        if config is not None:
            bundle.setdefault("stock_sub_split", getattr(config, "stock_sub_split", "60-40"))
            bundle.setdefault("config_id", config.config_id)
            bundle.setdefault("allocation_name", getattr(config, "allocation_name", ""))
        if sim_result is not None and "pending_cash_days" not in bundle:
            qdii = getattr(sim_result, "qdii_metrics", None)
            bundle["pending_cash_days"] = (
                int(getattr(qdii, "pending_cash_days", 0) or 0) if qdii is not None else 0
            )
        bundle.setdefault("pending_cash_days", int(bundle.get("pending_cash_days") or 0))
        bundle.setdefault("_raw", bundle.get("_raw", bundle))
        return bundle
    return bundle


def _material_cb_count(validation) -> int:
    needs = list(getattr(validation, "needs_review", None) or [])
    return sum(1 for item in needs if "cross-border" in item.lower())


def _stock_split_rank(split: str) -> int:
    # Higher is preferred under risk-budget (domestic-heavier first).
    order = {"60-40": 2, "50-50": 1, "40-60": 0}
    return order.get(str(split), 0)


def _unwrap(chosen):
    return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen


def _within_return_edge(a: dict, b: dict) -> bool:
    return abs(float(a.get("annualized_return", 0.0)) - float(b.get("annualized_return", 0.0))) < RETURN_EDGE_BP


def _apply_split_risk_budget(current: dict, candidate: dict):
    curr_split = str(current.get("stock_sub_split", "60-40"))
    cand_split = str(candidate.get("stock_sub_split", "60-40"))
    if curr_split == cand_split or not _within_return_edge(current, candidate):
        return None
    curr_cb = int(current.get("material_cb_reviews", 0))
    cand_cb = int(candidate.get("material_cb_reviews", 0))
    if cand_cb != curr_cb:
        return candidate if cand_cb < curr_cb else current
    if _stock_split_rank(cand_split) != _stock_split_rank(curr_split):
        return candidate if _stock_split_rank(cand_split) > _stock_split_rank(curr_split) else current
    return None


def _apply_pending_preference(current: dict, candidate: dict):
    if not _within_return_edge(current, candidate):
        return None
    curr_pend = int(current.get("pending_cash_days", 0) or 0)
    cand_pend = int(candidate.get("pending_cash_days", 0) or 0)
    if cand_pend != curr_pend:
        return candidate if cand_pend < curr_pend else current
    return None


def prefer_lock_candidate(current, candidate, intended_profile: str | None = None):
    current = _as_bundle(current)
    candidate = _as_bundle(candidate)
    if current is None:
        return _unwrap(candidate)

    # Prefer lockable over soft-pass.
    curr_lock = bool(current.get("lockable", False))
    cand_lock = bool(candidate.get("lockable", False))
    if curr_lock != cand_lock:
        return _unwrap(candidate if cand_lock else current)

    if intended_profile is None:
        split_pick = _apply_split_risk_budget(current, candidate)
        if split_pick is not None:
            return _unwrap(split_pick)

        pending_pick = _apply_pending_preference(current, candidate)
        if pending_pick is not None:
            return _unwrap(pending_pick)

        curr_ret = float(current.get("annualized_return", 0.0))
        cand_ret = float(candidate.get("annualized_return", 0.0))
        chosen = candidate if cand_ret > curr_ret else current
        return _unwrap(chosen)

    def _profile(bundle):
        return str(
            bundle.get("profile_suitability", {})
            .get(intended_profile, {})
            .get("classification", bundle.get("validation_classification", "caution"))
        )

    current_profile = _profile(current)
    candidate_profile = _profile(candidate)
    order = {"suitable": 2, "caution": 1, "unsuitable": 0}
    if order.get(candidate_profile, 1) != order.get(current_profile, 1):
        chosen = candidate if order.get(candidate_profile, 1) > order.get(current_profile, 1) else current
        return _unwrap(chosen)

    cand_ret = float(candidate.get("annualized_return", 0.0))
    curr_ret = float(current.get("annualized_return", 0.0))
    if cand_ret != curr_ret:
        split_pick = _apply_split_risk_budget(current, candidate)
        if split_pick is not None:
            return _unwrap(split_pick)
        pending_pick = _apply_pending_preference(current, candidate)
        if pending_pick is not None:
            return _unwrap(pending_pick)
        chosen = candidate if cand_ret > curr_ret else current
        return _unwrap(chosen)

    pending_pick = _apply_pending_preference(current, candidate)
    if pending_pick is not None:
        return _unwrap(pending_pick)

    cand_dd = float(candidate.get("max_drawdown", 0.0))
    curr_dd = float(current.get("max_drawdown", 0.0))
    if cand_dd != curr_dd:
        chosen = candidate if cand_dd > curr_dd else current
        return _unwrap(chosen)

    cand_qdii = float(candidate.get("qdii_fill_rate", 0.0))
    curr_qdii = float(current.get("qdii_fill_rate", 0.0))
    if cand_qdii != curr_qdii:
        chosen = candidate if cand_qdii > curr_qdii else current
        return _unwrap(chosen)

    chosen = candidate if str(candidate.get("config_id", "")) < str(current.get("config_id", "")) else current
    return _unwrap(chosen)
