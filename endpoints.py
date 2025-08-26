from dataclasses import dataclass

@dataclass(frozen=True)
class MindatEndpoints:
    base_url: str
    localities: str
    locality_detail: str
    locality_minerals: str

    def url_localities(self) -> str:
        return f"{self.base_url}{self.localities}"

    def url_locality_detail(self, loc_id: int | str) -> str:
        return f"{self.base_url}{self.locality_detail.format(id=loc_id)}"

    def url_locality_minerals(self) -> str:
        return f"{self.base_url}{self.locality_minerals}"
