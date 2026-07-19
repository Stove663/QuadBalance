"""Strategy lock integrity: material reviews, lockable gate, human sign-off."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Short-horizon stresses that are material lock blockers when review-required.
MATERIAL_STRESS_IDS = frozenset({"S14", "S15", "S20"})
PENDING_CASH_DAYS_MATERIAL = 252
WEIGHT_GAP_PP_MATERIAL = 0.02
WEIGHT_GAP_MONTHS_MATERIAL = 12


@dataclass(frozen=True)
class HumanSignOff:
    reviewer: str
    rationale: str
    acknowledged_items: tuple[str, ...]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def to_dict(self) -> dict[str, object]:
        return {
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "rationale": self.rationale,
            "acknowledged_items": list(self.acknowledged_items),
        }


def is_material_review_item(item: str) -> bool:
    text = item.lower()
    if "cross-border" in text or "path stress" in text:
        return True
    if "product-level" in text:
        return True
    if "unrecovered" in text or "not fully recovered" in text:
        return True
    if "seq_inflation" in text or "inflation-escalating" in text or "inflation withdrawal" in text:
        return True
    if "pending-cash" in text or "pending cash" in text:
        return True
    if "weight gap" in text or "qdii weight" in text:
        return True
    if "post-rebalance deviation" in text:
        return True
    for sid in MATERIAL_STRESS_IDS:
        if f"stress {sid.lower()}" in text or f"stress {sid}" in item:
            return True
    return False


def material_needs_review(needs_review: list[str]) -> list[str]:
    return [item for item in needs_review if is_material_review_item(item)]


def compute_lockable(
    passed: bool,
    needs_review: list[str],
    sign_off: HumanSignOff | None = None,
) -> bool:
    if not passed:
        return False
    material = material_needs_review(needs_review)
    if not material:
        return True
    if sign_off is None:
        return False
    acknowledged = set(sign_off.acknowledged_items)
    return all(item in acknowledged for item in material) and bool(sign_off.reviewer.strip()) and bool(sign_off.rationale.strip())


def qdii_quality_reviews(
    *,
    pending_cash_days: int,
    qdii_friction_months: int,
    avg_qdii_weight_gap: float,
    max_post_rebalance_deviation: float | None,
    rebalance_threshold: float,
) -> list[str]:
    reviews: list[str] = []
    if pending_cash_days > PENDING_CASH_DAYS_MATERIAL:
        reviews.append(
            f"Criterion 3: QDII pending-cash days {pending_cash_days} exceed {PENDING_CASH_DAYS_MATERIAL}"
        )
    if qdii_friction_months >= WEIGHT_GAP_MONTHS_MATERIAL and abs(avg_qdii_weight_gap) > WEIGHT_GAP_PP_MATERIAL:
        reviews.append(
            f"Criterion 3: QDII weight gap {avg_qdii_weight_gap:+.2%} sustained for {qdii_friction_months} months"
        )
    if max_post_rebalance_deviation is not None and max_post_rebalance_deviation > rebalance_threshold:
        reviews.append(
            f"Criterion 3: max post-rebalance deviation {max_post_rebalance_deviation:.2%} exceeds threshold {rebalance_threshold:.2%}"
        )
    return reviews


def format_sign_off_markdown(sign_off: HumanSignOff | None) -> str:
    if sign_off is None:
        return ""
    lines = [
        "## Human Sign-off",
        "",
        f"- Reviewer: {sign_off.reviewer}",
        f"- Timestamp: {sign_off.timestamp}",
        f"- Rationale: {sign_off.rationale}",
        "- Acknowledged open items:",
    ]
    for item in sign_off.acknowledged_items:
        lines.append(f"  - {item}")
    lines.append("")
    return "\n".join(lines)
