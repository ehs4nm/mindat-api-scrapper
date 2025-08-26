from dataclasses import dataclass

@dataclass
class PromptResult:
    country: str
    ltype: str
    page_size: int

class Questioner:
    """Interface for asking user inputs — replaceable by GUI/TUI later."""
    def ask(self) -> PromptResult:
        country = input("Country [Iran]: ").strip() or "Iran"
        ltype = input("Locality type [Mine]: ").strip() or "Mine"
        ps = input("Page size [100]: ").strip()
        page_size = int(ps) if ps.isdigit() else 100
        return PromptResult(country, ltype, page_size)
