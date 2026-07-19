"""Return-seeking lock shortlist: primary / max-return contrast / step-down."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from quadbalance.lock_selection import RETURN_EDGE_BP, _as_bundle, prefer_lock_candidate
from quadbalance.sweep_constants import LOCK_SHORTLIST_JSON, LOCK_SHORTLIST_MD

STEP_DOWN_ALLOCATION = "25-25-25-25"
SHORTLIST_SCHEMA_VERSION = 1


def _norm_review(item: str) -> str:
    text = item.strip()
    text = re.sub(r"QDII pending-cash days \d+", "QDII pending-cash days N", text)
    text = re.sub(r"deviation [\d.]+%", "deviation X%", text)
    return text


def _material_list(bundle: dict[str, Any]) -> list[str]:
    validation = bundle.get("validation")
    if validation is not None:
        material = getattr(validation, "material_needs_review", None)
        if material:
            return list(material)
        needs = list(getattr(validation, "needs_review", None) or [])
        from quadbalance.lock_integrity import material_needs_review

        return material_needs_review(needs)
    raw = bundle.get("material_needs_review") or []
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(";") if p.strip()]
    return list(raw)


def _view(bundle: dict[str, Any]) -> dict[str, Any]:
    b = _as_bundle(bundle)
    config = b.get("config")
    validation = b.get("validation")
    return {
        "bundle": b.get("_raw", bundle),
        "config_id": str(b.get("config_id") or (config.config_id if config is not None else "")),
        "allocation_name": str(
            b.get("allocation_name") or (getattr(config, "allocation_name", "") if config is not None else "")
        ),
        "stock_sub_split": str(
            b.get("stock_sub_split") or (getattr(config, "stock_sub_split", "60-40") if config is not None else "60-40")
        ),
        "annualized_return": float(b.get("annualized_return", 0.0) or 0.0),
        "max_drawdown": float(b.get("max_drawdown", 0.0) or 0.0),
        "pending_cash_days": int(b.get("pending_cash_days", 0) or 0),
        "lockable": bool(b.get("lockable", False)),
        "material_needs_review": _material_list(b if isinstance(b, dict) else bundle),
        "passed": bool(getattr(validation, "passed", True)) if validation is not None else True,
    }


def _pick_best(pool: list[dict[str, Any]], intended_profile: str | None = None) -> dict[str, Any] | None:
    if not pool:
        return None
    best: dict[str, Any] | None = None
    for bundle in pool:
        best = prefer_lock_candidate(best, bundle, intended_profile)
    assert best is not None
    return best if isinstance(best, dict) else {"_raw": best}


def build_pros_cons(
    *,
    role: str,
    view: dict[str, Any],
    primary: dict[str, Any] | None,
    shared_reviews: list[str],
) -> dict[str, list[str]]:
    pros: list[str] = []
    cons: list[str] = []
    shared_norm = {_norm_review(x) for x in shared_reviews}
    extra = [item for item in view["material_needs_review"] if _norm_review(item) not in shared_norm]

    if role == "primary":
        pros.append("Return-band leader with lowest pending-cash days among near-max soft-passes")
        if view["pending_cash_days"]:
            cons.append(f"QDII pending-cash days still elevated ({view['pending_cash_days']})")
    elif role == "max_return_contrast" and primary is not None:
        d_ret = view["annualized_return"] - primary["annualized_return"]
        d_pend = view["pending_cash_days"] - primary["pending_cash_days"]
        pros.append(f"Higher annualized return than primary ({d_ret:+.2%})")
        cons.append(f"Pending-cash days vs primary: {d_pend:+d}")
    elif role == "step_down" and primary is not None:
        d_ret = view["annualized_return"] - primary["annualized_return"]
        d_pend = view["pending_cash_days"] - primary["pending_cash_days"]
        pros.append(f"Lower QDII pending friction vs primary ({d_pend:+d} days)")
        cons.append(f"Lower annualized return vs primary ({d_ret:+.2%})")
    else:
        pros.append(f"Role {role}")

    if shared_reviews:
        cons.append(f"Shared material reviews remain ({len(shared_reviews)}); sign-off required to lock")
    for item in extra[:3]:
        cons.append(f"Extra review: {item}")
    return {"pros": pros, "cons": cons}


def _entry_payload(role: str, bundle: dict[str, Any], primary_view: dict[str, Any] | None, shared: list[str]) -> dict[str, Any]:
    view = _view(bundle)
    pc = build_pros_cons(role=role, view=view, primary=primary_view, shared_reviews=shared)
    return {
        "role": role,
        "config_id": view["config_id"],
        "allocation_name": view["allocation_name"],
        "stock_sub_split": view["stock_sub_split"],
        "annualized_return": view["annualized_return"],
        "max_drawdown": view["max_drawdown"],
        "pending_cash_days": view["pending_cash_days"],
        "lockable": False,
        "material_needs_review": view["material_needs_review"],
        "pros": pc["pros"],
        "cons": pc["cons"],
        "bundle": bundle,
    }


def build_return_seeking_shortlist(
    soft_passes: list[dict[str, Any]],
    *,
    intended_profile: str | None = None,
) -> dict[str, Any]:
    """Build up to three shortlist roles from soft-pass bundles."""
    views = []
    for bundle in soft_passes:
        v = _view(bundle)
        if not v["passed"] or v["lockable"]:
            continue
        views.append((bundle, v))

    skipped: list[dict[str, str]] = []
    roles: list[dict[str, Any]] = []
    if not views:
        return {
            "schema_version": SHORTLIST_SCHEMA_VERSION,
            "preference": "return_pending",
            "roles": [],
            "skipped": [{"role": "primary", "reason": "no soft-pass candidates"}],
            "shared_material_reviews": [],
        }

    max_ret = max(v["annualized_return"] for _, v in views)
    band_bundles = [b for b, v in views if max_ret - v["annualized_return"] < RETURN_EDGE_BP]
    primary_bundle = _pick_best(band_bundles, intended_profile)
    assert primary_bundle is not None
    primary_view = _view(primary_bundle)

    family = primary_view["allocation_name"]
    family_bundles = [b for b, v in views if v["allocation_name"] == family]
    contrast_bundle = max(
        family_bundles,
        key=lambda b: (
            _view(b)["annualized_return"],
            -_view(b)["pending_cash_days"],
            _view(b)["config_id"],
        ),
    )
    contrast_view = _view(contrast_bundle)
    if contrast_view["config_id"] == primary_view["config_id"]:
        contrast_bundle = None
        skipped.append({"role": "max_return_contrast", "reason": "identical to primary"})

    step_candidates = [b for b, v in views if v["allocation_name"] == STEP_DOWN_ALLOCATION]
    step_bundle = None
    if step_candidates:
        same_split = [b for b in step_candidates if _view(b)["stock_sub_split"] == primary_view["stock_sub_split"]]
        pool = same_split or step_candidates
        # Prefer lower pending, then higher return via prefer_lock_candidate in pending-aware mode.
        step_bundle = _pick_best(pool, intended_profile)
    else:
        skipped.append({"role": "step_down", "reason": f"no {STEP_DOWN_ALLOCATION} soft-pass"})

    draft_bundles = [primary_bundle]
    if contrast_bundle is not None:
        draft_bundles.append(contrast_bundle)
    if step_bundle is not None:
        draft_bundles.append(step_bundle)

    review_sets = [set(_norm_review(x) for x in _view(b)["material_needs_review"]) for b in draft_bundles]
    shared_norm = set.intersection(*review_sets) if review_sets else set()
    # Recover a stable shared list from primary's wording.
    shared = [item for item in primary_view["material_needs_review"] if _norm_review(item) in shared_norm]

    roles.append(_entry_payload("primary", primary_bundle, None, shared))
    primary_for_pc = _view(primary_bundle)
    if contrast_bundle is not None:
        roles.append(_entry_payload("max_return_contrast", contrast_bundle, primary_for_pc, shared))
    if step_bundle is not None:
        roles.append(_entry_payload("step_down", step_bundle, primary_for_pc, shared))

    return {
        "schema_version": SHORTLIST_SCHEMA_VERSION,
        "preference": "return_pending",
        "roles": roles,
        "skipped": skipped,
        "shared_material_reviews": shared,
    }


def shortlist_public_payload(shortlist: dict[str, Any]) -> dict[str, Any]:
    """Drop in-memory bundles for JSON serialization."""
    roles = []
    for role in shortlist.get("roles", []):
        roles.append({k: v for k, v in role.items() if k != "bundle"})
    return {
        "schema_version": shortlist.get("schema_version", SHORTLIST_SCHEMA_VERSION),
        "preference": shortlist.get("preference", "return_pending"),
        "roles": roles,
        "skipped": list(shortlist.get("skipped", [])),
        "shared_material_reviews": list(shortlist.get("shared_material_reviews", [])),
    }


def format_lock_shortlist_markdown(shortlist: dict[str, Any]) -> str:
    public = shortlist_public_payload(shortlist)
    lines = [
        "# Lock Candidate Shortlist",
        "",
        f"**Preference:** `{public['preference']}`",
        f"**Schema:** {public['schema_version']}",
        "",
        "Shortlist membership does **not** make a configuration `lockable`. "
        "Active lock requires empty material reviews or human sign-off after an explicit pick.",
        "",
    ]
    if public["shared_material_reviews"]:
        lines.append("## Shared material reviews")
        lines.append("")
        for item in public["shared_material_reviews"]:
            lines.append(f"- {item}")
        lines.append("")

    for role in public["roles"]:
        lines.extend(
            [
                f"## {role['role']}",
                "",
                f"- **config_id:** `{role['config_id']}`",
                f"- **allocation:** {role['allocation_name']} / split {role['stock_sub_split']}",
                f"- **annualized return:** {role['annualized_return']:.2%}",
                f"- **max drawdown:** {role['max_drawdown']:.2%}",
                f"- **pending_cash_days:** {role['pending_cash_days']}",
                f"- **lockable:** {role['lockable']}",
                "",
                "### Pros",
                "",
            ]
        )
        for p in role.get("pros", []):
            lines.append(f"- {p}")
        lines.extend(["", "### Cons", ""])
        for c in role.get("cons", []):
            lines.append(f"- {c}")
        lines.append("")

    if public["skipped"]:
        lines.append("## Skipped roles")
        lines.append("")
        for row in public["skipped"]:
            lines.append(f"- `{row.get('role')}`: {row.get('reason')}")
        lines.append("")

    lines.extend(
        [
            "## How to lock",
            "",
            "Pick a `config_id` with `--lock-config-id` and supply `--sign-off-reviewer` / "
            "`--sign-off-rationale` when material reviews remain.",
            "",
        ]
    )
    return "\n".join(lines)


def write_lock_shortlist_artifacts(output_dir: Path, shortlist: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    public = shortlist_public_payload(shortlist)
    json_path = output_dir / LOCK_SHORTLIST_JSON
    md_path = output_dir / LOCK_SHORTLIST_MD
    json_path.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(format_lock_shortlist_markdown(shortlist), encoding="utf-8")
    return json_path, md_path
