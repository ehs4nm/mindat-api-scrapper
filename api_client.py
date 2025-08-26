from typing import Iterator
from .endpoints import MindatEndpoints
from .http import HttpSession

def _extract_page(data: dict) -> tuple[list[dict], int | None, str | None]:
    if isinstance(data, list):
        return data, None, None
    if isinstance(data, dict):
        res = data.get("results")
        if isinstance(res, list):
            return res, data.get("count"), data.get("next")
    return [], None, None

class MindatClient:
    """Thin, testable wrapper over Mindat endpoints (no CLI/UI here)."""
    def __init__(self, http: HttpSession, ep: MindatEndpoints, page_size: int):
        self.http, self.ep, self.page_size = http, ep, page_size

    def search_localities(self, base_params: dict) -> Iterator[dict]:
        """Yield all localities by following 'next'; trust results more than count."""
        url = self.ep.url_localities()
        params = dict(base_params)
        params["page_size"] = self.page_size
        page = self.http.get_json(url, params)
        results, _, next_url = _extract_page(page)
        for item in results:
            yield item
        while next_url:
            page = self.http.get_json(next_url)
            results, _, next_url = _extract_page(page)
            for item in results:
                yield item

    def get_locality_detail(self, loc_id: int, expand_geomaterials: bool = True) -> dict:
        url = self.ep.url_locality_detail(loc_id)
        params = {"format": "json"}
        if expand_geomaterials:
            params["expand"] = "geomaterials"
        return self.http.get_json(url, params)

    def list_locality_minerals(self, loc_id: int, page_size: int | None = None) -> list[dict]:
        url = self.ep.url_locality_minerals()
        params = {"format": "json", "locality": loc_id, "page_size": page_size or self.page_size}
        out: list[dict] = []
        page = self.http.get_json(url, params)
        results, _, next_url = _extract_page(page)
        out.extend(results)
        while next_url:
            page = self.http.get_json(next_url)
            results, _, next_url = _extract_page(page)
            out.extend(results)
        return out
