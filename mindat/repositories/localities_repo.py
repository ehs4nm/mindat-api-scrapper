from typing import Iterator
from ..api_client import MindatClient

class LocalitiesRepository:
    """
    Repository = where your querying logic lives (strategies, params).
    Changing filters/endpoints should be done here or in endpoints/config — not in CLI/Service.
    """
    def __init__(self, client: MindatClient, search_strategies: list[dict]):
        self.client = client
        self.strategies = search_strategies

    def iter_mines_in_country(self, country: str) -> Iterator[dict]:
        """
        Try configured strategies in order until we get at least one result, then stream all.
        Strategies come from config.yaml (e.g., ltype=60, txt=Mine, etc.)
        """
        base = {"format": "json", "country": country}
        seen_any = False
        for strat in self.strategies:
            params = base | {strat["param"]: strat["value"]}
            gen = self.client.search_localities(params)
            # try first item to confirm
            first = None
            try:
                first = next(gen)
                seen_any = True
                yield first
                # then yield the rest
                for item in gen:
                    yield item
                break  # stop trying more strategies
            except StopIteration:
                # no results for this strategy, try next
                continue
        if not seen_any:
            # yield nothing; caller decides how to handle "no results"
            return
