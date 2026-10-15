"""Navegador headless compartilhado pelas fontes que dependem de JavaScript.

Estante Virtual e MangaDex entregam tudo por HTTP simples. Bing, Enjoei e OLX
só montam os resultados dentro do navegador, e é este módulo que centraliza
esse custo.

Memória é o recurso escasso: um Chromium ocupa ~250 MB, e a VM de produção tem
1 GB no total. Por isso as três fontes compartilham **uma** instância por
busca (`sessao()`), em vez de subir uma cada — foi o que derrubou o servidor
quando as três entraram no ar.
"""
import threading
from contextlib import contextmanager

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0.0.0 Safari/537.36")

TIMEOUT_MS = 20_000

# `--disable-dev-shm-usage` é obrigatório em container: o /dev/shm padrão do
# Docker tem 64 MB e o Chromium quebra ao enchê-lo. Os demais cortam subsistemas
# que não usamos. Imagens ficam LIGADAS de propósito: o Bing só preenche o src
# da capa depois de carregá-la, e é assim que pegamos a imagem do produto.
ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--mute-audio",
    "--no-first-run",
]

# O navegador aberto pela sessão atual. Thread-local porque cada busca roda na
# sua própria thread (a rota usa asyncio.to_thread).
_atual = threading.local()


class PlaywrightIndisponivel(RuntimeError):
    """Playwright ou o Chromium não estão instalados.

    Vira falha explícita da fonte em vez de lista vazia, para não parecer
    que a loja simplesmente não tinha o mangá.
    """


def _sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        raise PlaywrightIndisponivel(
            "Playwright não instalado — rode: pip install playwright "
            "&& playwright install chromium"
        ) from erro
    return sync_playwright


@contextmanager
def sessao():
    """Abre um Chromium que as fontes seguintes reaproveitam.

    Quem chama `pagina()` dentro deste bloco ganha uma aba do mesmo navegador.
    Fora dele, `pagina()` sobe e derruba um navegador próprio — conveniente
    para rodar uma fonte isolada, caro demais para a busca completa.
    """
    sync_playwright = _sync_playwright()

    with sync_playwright() as p:
        try:
            navegador = p.chromium.launch(headless=True, args=ARGS)
        except Exception as erro:
            raise PlaywrightIndisponivel(
                f"Não foi possível abrir o Chromium ({erro}). "
                "Rode: playwright install chromium"
            ) from erro

        _atual.navegador = navegador
        try:
            yield
        finally:
            # O finally garante que o Chromium morre junto com a busca,
            # mesmo se uma fonte estourar. Processo órfão aqui significa
            # memória que não volta.
            _atual.navegador = None
            navegador.close()


@contextmanager
def pagina(locale: str = "pt-BR"):
    """Entrega uma página pronta, reaproveitando a sessão quando existir."""
    compartilhado = getattr(_atual, "navegador", None)

    if compartilhado is not None:
        contexto = compartilhado.new_context(locale=locale,
                                             user_agent=USER_AGENT)
        try:
            yield contexto.new_page()
        finally:
            contexto.close()
        return

    # Sem sessão: navegador avulso, fechado ao fim.
    with sessao():
        with pagina(locale) as page:
            yield page
