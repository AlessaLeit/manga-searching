"""Navegador headless compartilhado pelas fontes que dependem de JavaScript.

Estante Virtual e MangaDex entregam tudo por HTTP simples. Google e Bing só
montam os resultados dentro do navegador, então essas duas fontes sobem um
Chromium — e é este módulo que centraliza esse custo.
"""
from contextlib import contextmanager

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0.0.0 Safari/537.36")

TIMEOUT_MS = 20_000


class PlaywrightIndisponivel(RuntimeError):
    """Playwright ou o Chromium não estão instalados.

    Vira falha explícita da fonte em vez de lista vazia, para não parecer
    que a loja simplesmente não tinha o mangá.
    """


@contextmanager
def pagina(locale: str = "pt-BR"):
    """Entrega uma página pronta e garante o fechamento do navegador."""
    # Import tardio: sem Playwright instalado o resto do scraper segue
    # funcionando, em vez de quebrar o import da aplicação inteira.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        raise PlaywrightIndisponivel(
            "Playwright não instalado — rode: pip install playwright "
            "&& playwright install chromium"
        ) from erro

    with sync_playwright() as p:
        try:
            navegador = p.chromium.launch(headless=True)
        except Exception as erro:
            raise PlaywrightIndisponivel(
                f"Não foi possível abrir o Chromium ({erro}). "
                "Rode: playwright install chromium"
            ) from erro

        try:
            contexto = navegador.new_context(
                locale=locale, user_agent=USER_AGENT
            )
            yield contexto.new_page()
        finally:
            navegador.close()
