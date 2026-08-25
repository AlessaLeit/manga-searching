"""Cliente HTTP compartilhado pelas fontes: sessão única, retry e backoff."""
import random
import time

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = 20
_sessao = requests.Session()
_sessao.headers.update(HEADERS)


def get(url: str, params: dict | None = None, retries: int = 3,
        headers: dict | None = None) -> requests.Response | None:
    """GET com retry em erros de rede e em respostas de throttling.

    Devolve None quando todas as tentativas falham, para que uma fonte
    indisponível não derrube a busca inteira.
    """
    for tentativa in range(retries):
        try:
            r = _sessao.get(url, params=params, timeout=TIMEOUT, headers=headers)
        except requests.RequestException:
            time.sleep(2 * (tentativa + 1))
            continue

        if r.status_code == 200:
            return r
        if r.status_code in (429, 503):
            time.sleep(5 * (tentativa + 1) + random.uniform(0, 2))
            continue
        return None
    return None
