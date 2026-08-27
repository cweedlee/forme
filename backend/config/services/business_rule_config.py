import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class NominatorRuleConfig:
    gross_amount: dict[str, int | None]
    domestic_country_codes: set[str]


@dataclass(frozen=True)
class BusinessRuleConfig:
    nominator: NominatorRuleConfig


def load_business_rule_config(config_path: Path | None = None) -> BusinessRuleConfig:
    path = config_path or settings.BUSINESS_RULE_CONFIG_PATH
    with path.open(encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    return parse_business_rule_config(raw_config)


def parse_business_rule_config(raw_config: dict[str, Any]) -> BusinessRuleConfig:
    nominator = raw_config.get("contract-type", {}).get("nominator", {})
    gross_amount = nominator.get("gross_amount", {})
    return BusinessRuleConfig(
        nominator=NominatorRuleConfig(
            gross_amount={
                "domestic": _optional_int(gross_amount.get("domestic")),
                "overseas": _optional_int(gross_amount.get("overseas")),
            },
            domestic_country_codes={
                str(value).strip()
                for value in raw_config.get("domestic_country_codes", [])
                if str(value).strip()
            },
        )
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
