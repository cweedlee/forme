from dataclasses import dataclass

from config.services.business_rule_config import NominatorRuleConfig
from config.services.person_rows import PersonSourceRow


NOMINATOR_ENGAGEMENT_TYPE = "nominator"
NOMINATOR_ENGAGEMENT_ALIASES = {"nominator", "노미네이터"}


@dataclass(frozen=True)
class NominatorFeeDecision:
    status: str
    amount_krw: int | None
    category: str | None
    reason: str

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"


def decide_nominator_fee(person: PersonSourceRow, config: NominatorRuleConfig) -> NominatorFeeDecision:
    if _normalize(person.engagement_type) not in NOMINATOR_ENGAGEMENT_ALIASES:
        return NominatorFeeDecision(
            status="NOT_APPLICABLE",
            amount_krw=None,
            category=None,
            reason="참여유형이 노미네이터가 아닙니다.",
        )

    country = _normalize(person.residence_country or person.country_code)
    if not country:
        return _manual_review("거주국 값이 비어 있어 국내/국외를 판단할 수 없습니다.")

    domestic_codes = {_normalize(value) for value in config.domestic_country_codes}
    category = "domestic" if country in domestic_codes else "overseas"
    amount = config.gross_amount[category]
    label = "국내" if category == "domestic" else "국외"
    if amount is None:
        return _manual_review(f"{label} 노미네이터 금액이 아직 설정되지 않았습니다.")

    return NominatorFeeDecision(
        status="READY",
        amount_krw=amount,
        category=category,
        reason=f"거주국 {country} 기준 {label} 노미네이터 금액을 적용합니다.",
    )


def _manual_review(reason: str) -> NominatorFeeDecision:
    return NominatorFeeDecision(
        status="MANUAL_REVIEW",
        amount_krw=None,
        category=None,
        reason=reason,
    )


def _normalize(value: str | None) -> str:
    return str(value or "").strip()
