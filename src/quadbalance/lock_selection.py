"""Helpers for choosing the final locked configuration."""

from __future__ import annotations

STOCK_SPLIT_RETURN_EDGE_BP = 0.005  # 50bp


def _as_bundle(bundle):
    if isinstance(bundle, tuple) and len(bundle) == 3:
        validation, config, result = bundle
        profile_classification = validation.profile_suitability.get("accumulation", {}).get("classification", "caution")
        return {
            "validation_classification": profile_classification,
            "annualized_return": validation.metrics.annualized_return,
            "max_drawdown": validation.metrics.max_drawdown,
            "qdii_fill_rate": getattr(result.qdii_metrics, "qdii_fill_rate", 0.0),
            "config_id": config.config_id,
            "lockable": getattr(validation, "lockable", False),
            "stock_sub_split": getattr(config, "stock_sub_split", "60-40"),
            "material_cb_reviews": _material_cb_count(validation),
            "_raw": bundle,
        }
    if isinstance(bundle, dict):
        bundle = dict(bundle)
        validation = bundle.get("validation")
        config = bundle.get("config")
        if validation is not None:
            bundle.setdefault("lockable", getattr(validation, "lockable", False))
            bundle.setdefault("material_cb_reviews", _material_cb_count(validation))
        if config is not None:
            bundle.setdefault("stock_sub_split", getattr(config, "stock_sub_split", "60-40"))
            bundle.setdefault("config_id", config.config_id)
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


def prefer_lock_candidate(current, candidate, intended_profile: str | None = None):
    current = _as_bundle(current)
    candidate = _as_bundle(candidate)
    if current is None:
        return candidate.get("_raw", candidate) if isinstance(candidate, dict) else candidate

    # Prefer lockable over soft-pass.
    curr_lock = bool(current.get("lockable", False))
    cand_lock = bool(candidate.get("lockable", False))
    if curr_lock != cand_lock:
        chosen = candidate if cand_lock else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    if intended_profile is None:
        # Risk-budget preference among stock splits when return edge is small.
        curr_split = str(current.get("stock_sub_split", "60-40"))
        cand_split = str(candidate.get("stock_sub_split", "60-40"))
        curr_ret = float(current.get("annualized_return", 0.0))
        cand_ret = float(candidate.get("annualized_return", 0.0))
        if curr_split != cand_split and abs(cand_ret - curr_ret) < STOCK_SPLIT_RETURN_EDGE_BP:
            curr_cb = int(current.get("material_cb_reviews", 0))
            cand_cb = int(candidate.get("material_cb_reviews", 0))
            if cand_cb != curr_cb:
                chosen = candidate if cand_cb < curr_cb else current
                return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen
            if _stock_split_rank(cand_split) != _stock_split_rank(curr_split):
                chosen = candidate if _stock_split_rank(cand_split) > _stock_split_rank(curr_split) else current
                return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

        chosen = candidate if cand_ret > curr_ret else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    def _profile(bundle):
        return str(bundle.get("profile_suitability", {}).get(intended_profile, {}).get("classification", bundle.get("validation_classification", "caution")))

    current_profile = _profile(current)
    candidate_profile = _profile(candidate)
    order = {"suitable": 2, "caution": 1, "unsuitable": 0}
    if order.get(candidate_profile, 1) != order.get(current_profile, 1):
        chosen = candidate if order.get(candidate_profile, 1) > order.get(current_profile, 1) else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    cand_ret = float(candidate.get("annualized_return", 0.0))
    curr_ret = float(current.get("annualized_return", 0.0))
    if cand_ret != curr_ret:
        # Still apply split risk-budget when edge < 50bp.
        curr_split = str(current.get("stock_sub_split", "60-40"))
        cand_split = str(candidate.get("stock_sub_split", "60-40"))
        if curr_split != cand_split and abs(cand_ret - curr_ret) < STOCK_SPLIT_RETURN_EDGE_BP:
            if _stock_split_rank(cand_split) != _stock_split_rank(curr_split):
                chosen = candidate if _stock_split_rank(cand_split) > _stock_split_rank(curr_split) else current
                return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen
        chosen = candidate if cand_ret > curr_ret else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    cand_dd = float(candidate.get("max_drawdown", 0.0))
    curr_dd = float(current.get("max_drawdown", 0.0))
    if cand_dd != curr_dd:
        chosen = candidate if cand_dd > curr_dd else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    cand_qdii = float(candidate.get("qdii_fill_rate", 0.0))
    curr_qdii = float(current.get("qdii_fill_rate", 0.0))
    if cand_qdii != curr_qdii:
        chosen = candidate if cand_qdii > curr_qdii else current
        return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen

    chosen = candidate if str(candidate.get("config_id", "")) < str(current.get("config_id", "")) else current
    return chosen.get("_raw", chosen) if isinstance(chosen, dict) else chosen
