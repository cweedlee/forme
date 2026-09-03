from dataclasses import dataclass

from config.services.contract_table import ContractTable
from config.services.nominator_source import NominatorContractTable


@dataclass(frozen=True)
class ContractPage:
    table_class: type[ContractTable]
    template_name: str


CONTRACT_PAGES: dict[str, ContractPage] = {
    "nominator": ContractPage(
        table_class=NominatorContractTable,
        template_name="contracts/nominator.html",
    ),
}



def get_contract_page(contract_type: str) -> ContractPage | None:
    return CONTRACT_PAGES.get(contract_type)
