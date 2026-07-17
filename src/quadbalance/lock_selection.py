"""Helpers for choosing the final locked configuration."""

from __future__ import annotations

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
            "_raw": bundle,
        }
    if isinstance(bundle, dict):
        bundle = dict(bundle)
        bundle.setdefault("_raw", bundle.get("_raw", bundle))
        return bundle
    return bundle


def prefer_lock_candidate(current, candidate, intended_profile: str | None = None):
    current = _as_bundle(current)
    candidate = _as_bundle(candidate)
    if current is None:
        return candidate.get("_raw", candidate) if isinstance(candidate, dict) else candidate

    if intended_profile is None:
        chosen = candidate if float(candidate.get("annualized_return", 0.0)) > float(current.get("annualized_return", 0.0)) else current
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
