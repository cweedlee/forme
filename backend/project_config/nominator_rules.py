from dataclasses import dataclass


NOMINATOR_ENGAGEMENT_TYPE = "nominator"
NOMINATOR_ENGAGEMENT_ALIASES = {"nominator", "노미네이터"}

# Confirm these two values against the operating contract budget before using
# them for final contract generation.
NOMINATOR_FEES_KRW = {
    "domestic": None,
    "overseas": None,
}

DOMESTIC_COUNTRY_CODES = {"KR", "KOR", "대한민국", "한국", "South Korea", "Republic of Korea"}


@dataclass(frozen=True)
class NominatorFeeDecision:
    status: str
    amount_krw: int | None
    category: str | None
    reason: str

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"


def decide_nominator_fee(
    *,
    engagement_type: str | None,
    residence_country: str | None,
) -> NominatorFeeDecision:
    if _normalize(engagement_type) not in NOMINATOR_ENGAGEMENT_ALIASES:
        return NominatorFeeDecision(
            status="NOT_APPLICABLE",
            amount_krw=None,
            category=None,
            reason="참여유형이 노미네이터가 아닙니다.",
        )

    country = _normalize(residence_country)
    if not country:
        return _manual_review("거주국 값이 비어 있어 국내/국외를 판단할 수 없습니다.")

    category = "domestic" if country in {_normalize(value) for value in DOMESTIC_COUNTRY_CODES} else "overseas"
    amount = NOMINATOR_FEES_KRW[category]
    label = "국내" if category == "domestic" else "국외"
    if amount is None:
        return _manual_review(f"{label} 노미네이터 금액이 아직 설정되지 않았습니다.")

    return NominatorFeeDecision(
        status="READY",
        amount_krw=amount,
        category=category,
        reason=f"거주국 {residence_country} 기준 {label} 노미네이터 금액을 적용합니다.",
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
