"""Off-exchange fund instrument pool with primary and ranked backups.

Selection priority (in order):
1. Subscription quota available (QDII often limited; verify on purchase day)
2. Tracking quality (direct index replication preferred over ETF feeder-of-feeder)
3. Low purchase and holding cost (C-share for long DCA; A-share for one-shot buys)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from quadbalance.config import Quadrant

QuotaRisk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class FundInstrument:
    code: str
    name: str
    quadrant: Quadrant
    role: Literal["primary", "backup"]
    rank: int  # 1 = primary, 2+ = backup priority
    share_class: str
    purchase_fee: str
    mgmt_fee: str
    tracking_note: str
    quota_risk: QuotaRisk
    notes: str

    @property
    def is_primary(self) -> bool:
        return self.role == "primary"


# --- Stocks: domestic (60% of stocks quadrant) ---

STOCKS_DOMESTIC_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="110020",
        name="易方达沪深300ETF联接A",
        quadrant="stocks",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="0.12%（常见1折后0.12%）",
        mgmt_fee="0.15%",
        tracking_note="联接510300，规模大、流动性好，跟踪沪深300",
        quota_risk="low",
        notes="默认主选；大额一次性买入选A类",
    ),
    FundInstrument(
        code="005658",
        name="华夏沪深300ETF联接C",
        quadrant="stocks",
        role="backup",
        rank=2,
        share_class="C",
        purchase_fee="0%",
        mgmt_fee="0.15%+销售服务费0.25%",
        tracking_note="联接510330，跟踪误差同类领先",
        quota_risk="low",
        notes="长期定投备选；持有>30天通常免赎回费",
    ),
    FundInstrument(
        code="000051",
        name="华夏沪深300ETF联接A",
        quadrant="stocks",
        role="backup",
        rank=3,
        share_class="A",
        purchase_fee="0.12%（1折后）",
        mgmt_fee="0.15%",
        tracking_note="联接510330，历史长（2009）",
        quota_risk="low",
        notes="平台缺 110020 时使用",
    ),
)

# --- Stocks: QDII global (40% of stocks quadrant) ---

STOCKS_QDII_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="161125",
        name="易方达标普500指数（QDII-LOF）A",
        quadrant="stocks",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="1.2%（1折后0.12%）",
        mgmt_fee="0.50%",
        tracking_note="直接复制标普500，年化跟踪误差约0.3%，优于双层联接",
        quota_risk="high",
        notes="当前锁定主选；限购常见（常100元/日）",
    ),
    FundInstrument(
        code="050025",
        name="博时标普500ETF联接（QDII）A",
        quadrant="stocks",
        role="backup",
        rank=2,
        share_class="A",
        purchase_fee="1.0%（1折后0.10%）",
        mgmt_fee="0.60%",
        tracking_note="联接513500，双层结构跟踪略逊于161125",
        quota_risk="high",
        notes="161125额度不足时使用",
    ),
    FundInstrument(
        code="006075",
        name="博时标普500ETF联接（QDII）C",
        quadrant="stocks",
        role="backup",
        rank=3,
        share_class="C",
        purchase_fee="0%",
        mgmt_fee="0.60%+销售服务费0.25%",
        tracking_note="同050025标的，C类持有成本低",
        quota_risk="high",
        notes="长期定投备选；与050025共享QDII额度",
    ),
)

# --- Bonds B1: short/intermediate (5-year treasury proxy) ---

BONDS_B1_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="003358",
        name="嘉实3-5年国债ETF联接A",
        quadrant="bonds",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="0.06%（1折后）",
        mgmt_fee="0.15%",
        tracking_note="跟踪3-5年国债指数，对应511010逻辑",
        quota_risk="low",
        notes="B1默认主选",
    ),
    FundInstrument(
        code="161119",
        name="易方达中债新综合指数（LOF）A",
        quadrant="bonds",
        role="backup",
        rank=2,
        share_class="A",
        purchase_fee="0.08%（1折后）",
        mgmt_fee="0.15%",
        tracking_note="中债新综合全价指数，久期略长于3-5年",
        quota_risk="low",
        notes="003358暂停申购时的宽基国债替代",
    ),
)

# --- Bonds B2: long (7-10 year CDB) ---

BONDS_B2_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="003327",
        name="易方达中债7-10年国开行债券指数A",
        quadrant="bonds",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="0.08%（1折后）",
        mgmt_fee="0.25%",
        tracking_note="跟踪7-10年国开债，对应511260逻辑",
        quota_risk="low",
        notes="B2默认主选",
    ),
    FundInstrument(
        code="161716",
        name="招商双债增强债券（LOF）A",
        quadrant="bonds",
        role="backup",
        rank=2,
        share_class="A",
        purchase_fee="0.08%（1折后）",
        mgmt_fee="0.30%",
        tracking_note="国债+企债增强，非纯指数，波动略高",
        quota_risk="low",
        notes="纯指数不可用时；接受略高信用敞口",
    ),
)

# --- Gold ---

GOLD_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="000216",
        name="华安黄金ETF联接A",
        quadrant="gold",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="0.60%（1折后0.06%）",
        mgmt_fee="0.50%",
        tracking_note="联接518880，跟踪国内黄金现货",
        quota_risk="low",
        notes="默认主选",
    ),
    FundInstrument(
        code="002963",
        name="易方达黄金ETF联接C",
        quadrant="gold",
        role="backup",
        rank=2,
        share_class="C",
        purchase_fee="0%",
        mgmt_fee="0.50%+销售服务费0.35%",
        tracking_note="联接1024，跟踪误差小",
        quota_risk="low",
        notes="长期定投备选",
    ),
    FundInstrument(
        code="000218",
        name="国泰黄金ETF联接A",
        quadrant="gold",
        role="backup",
        rank=3,
        share_class="A",
        purchase_fee="0.60%（1折后0.06%）",
        mgmt_fee="0.50%",
        tracking_note="联接518800",
        quota_risk="low",
        notes="第三备选",
    ),
)

# --- Cash ---

CASH_POOL: tuple[FundInstrument, ...] = (
    FundInstrument(
        code="006874",
        name="泰康现金管家货币A",
        quadrant="cash",
        role="primary",
        rank=1,
        share_class="A",
        purchase_fee="0%",
        mgmt_fee="0.15%",
        tracking_note="货币市场基金，7日年化收益稳定",
        quota_risk="low",
        notes="默认主选；申赎T+1",
    ),
    FundInstrument(
        code="070009",
        name="嘉实超短债债券A",
        quadrant="cash",
        role="backup",
        rank=2,
        share_class="A",
        purchase_fee="0.40%（1折后0.04%）",
        mgmt_fee="0.30%",
        tracking_note="超短债，波动极低，近似现金",
        quota_risk="low",
        notes="货币基金额度紧张时；历史数据长（回测代理）",
    ),
)

POOLS_BY_KEY: dict[str, tuple[FundInstrument, ...]] = {
    "stocks_domestic": STOCKS_DOMESTIC_POOL,
    "stocks_qdii": STOCKS_QDII_POOL,
    "bonds_b1": BONDS_B1_POOL,
    "bonds_b2": BONDS_B2_POOL,
    "gold": GOLD_POOL,
    "cash": CASH_POOL,
}

ALL_INSTRUMENTS: dict[str, FundInstrument] = {
    f.code: f for pool in POOLS_BY_KEY.values() for f in pool
}


def pool_for_quadrant(quadrant: Quadrant, bond_variant: str = "B1") -> list[FundInstrument]:
    """Return ranked instrument pool for a quadrant."""
    if quadrant == "stocks":
        return list(STOCKS_DOMESTIC_POOL) + list(STOCKS_QDII_POOL)
    if quadrant == "bonds":
        return list(BONDS_B1_POOL if bond_variant == "B1" else BONDS_B2_POOL)
    if quadrant == "gold":
        return list(GOLD_POOL)
    return list(CASH_POOL)


def primary_code(pool_key: str) -> str:
    pool = POOLS_BY_KEY[pool_key]
    return next(f.code for f in pool if f.is_primary)


def backups(pool_key: str) -> list[FundInstrument]:
    pool = POOLS_BY_KEY[pool_key]
    return sorted([f for f in pool if not f.is_primary], key=lambda f: f.rank)


def select_on_quota_unavailable(pool_key: str) -> list[FundInstrument]:
    """Return backup list to try when primary has no subscription quota."""
    return backups(pool_key)


def format_pool_markdown() -> str:
    """Render instrument pools as markdown for strategy lock document."""
    lines = ["## Instrument Pool (场外)", ""]
    for key, pool in POOLS_BY_KEY.items():
        lines.append(f"### {key}")
        lines.append("")
        lines.append("| Rank | Code | Name | Quota | Tracking | Cost | Notes |")
        lines.append("|------|------|------|-------|----------|------|-------|")
        for f in sorted(pool, key=lambda x: x.rank):
            role = "主选" if f.is_primary else f"备选{f.rank - 1}"
            lines.append(
                f"| {role} | {f.code} | {f.name} | {f.quota_risk} | "
                f"{f.tracking_note[:20]}… | 申购{f.purchase_fee} | {f.notes} |"
            )
        lines.append("")
    lines.extend(
        [
            "### Selection Rules",
            "",
            "1. **额度**：申购前在平台确认当日可购额度；QDII 优先选开放额度最大的标的",
            "2. **跟踪**：同标的优先直接指数基金，其次 ETF 联接",
            "3. **成本**：一次性大额底仓用 A 类；长期月定投优先 C 类（持有>30天）",
            "4. **切换**：仅当主选暂停申购/额度不足时使用备选，并在策略日志记录",
            "",
        ]
    )
    return "\n".join(lines)
