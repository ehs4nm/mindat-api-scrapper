import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .errors import MindatAuthError, MindatHTTPError, MindatJSONError

class HttpSession:
    def __init__(self, connect_to: str, retries, timeouts, api_key: str):
        self.base = connect_to
        self.session = requests.Session()
        retry = Retry(
            total=retries.total,
            connect=retries.total,
            read=retries.total,
            backoff_factor=retries.backoff_factor,
            status_forcelist=retries.status_forcelist,
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter); self.session.mount("http://", adapter)
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "mindat-dl/1.0 (+requests)",
            "Authorization": f"Token {api_key}",
        })
        self.timeout = (timeouts.connect, timeouts.read)

    def get_json(self, url: str, params: dict | None = None) -> dict:
        r = self.session.get(url, params=params or {}, timeout=self.timeout)
        if r.status_code in (401, 403):
            raise MindatAuthError(f"Unauthorized: {r.status_code} {r.url}")
        if r.status_code != 200:
            raise MindatHTTPError(f"HTTP {r.status_code} {r.url}")
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "application/json" not in ctype:
            raise MindatJSONError(f"Non-JSON body from {r.url}")
        try:
            return r.json()
        except Exception as e:
            raise MindatJSONError(f"JSON parse error: {e} @ {r.url}") from e
