"""Google Shopping — via Playwright.

Diferente das outras fontes, o Google monta os resultados por JavaScript: o
HTML que chega no `requests` não tem um preço sequer. Por isso aqui subimos um
Chromium headless e lemos o DOM já renderizado.

Custo: cada busca abre um navegador (segundos, não milissegundos). Por isso a
fonte é opcional — ligue com GOOGLE_SHOPPING_ENABLED=1. Sem isso ela devolve
lista vazia e as outras fontes respondem sozinhas.

Os nomes de classe do Google são gerados e mudam sem aviso, então não
dependemos deles: procuramos o texto "R$" e subimos até o card que o contém.
"""
import os
import re

from ..models import Condicao

NOME = "Google Shopping"
BUSCA = "https://www.google.com/search"

TIMEOUT_MS = 20_000
_MARCADORES_USADO = ("usado", "usada", "seminovo", "semi-novo", "used")


class BloqueadoPeloGoogle(RuntimeError):
    """O Google respondeu com a página de verificação anti-robô (/sorry/).

    Vira falha explícita (e não lista vazia) para o usuário conseguir
    distinguir "não achei nada" de "a fonte me barrou".
    """


def habilitado() -> bool:
    return os.getenv("GOOGLE_SHOPPING_ENABLED", "").strip().lower() in {
        "1", "true", "yes", "sim",
    }


def _condicao(texto: str) -> Condicao:
    minusculo = texto.lower()
    return (Condicao.USADO if any(m in minusculo for m in _MARCADORES_USADO)
            else Condicao.NOVO)


# Roda dentro do navegador: varre os cards e devolve os campos crus.
# Ancorar em "R$" em vez de classes geradas ("jsname=ZvZkAe" e afins) é o que
# faz isso sobreviver às trocas de layout do Google.
_EXTRAI_JS = """
(limite) => {
  const vistos = new Set();
  const itens = [];

  for (const no of document.querySelectorAll('a[href]')) {
    if (itens.length >= limite) break;

    // Sobe até um bloco grande o bastante para ser o card do produto.
    let card = no;
    for (let i = 0; i < 6 && card.parentElement; i++) {
      if (/R\\$/.test(card.innerText || '') && (card.innerText || '').length > 25) break;
      card = card.parentElement;
    }

    const texto = (card.innerText || '').trim();
    const preco = texto.match(/R\\$\\s*[\\d.,]+/);
    if (!preco) continue;

    const linhas = texto.split('\\n').map(l => l.trim()).filter(Boolean);
    const nome = linhas.find(l => !/R\\$/.test(l) && l.length > 8);
    if (!nome || vistos.has(nome)) continue;
    vistos.add(nome);

    // A loja costuma vir numa linha curta depois do preco ("Amazon.com.br").
    const iPreco = linhas.findIndex(l => /R\\$/.test(l));
    const loja = linhas.slice(iPreco + 1).find(
      l => l.length < 40 && !/R\\$|avalia|frete/i.test(l)
    );

    itens.push({
      nome,
      preco: preco[0],
      loja: loja || null,
      link: no.href,
      texto,
    });
  }

  return itens;
}
"""


def _recusar_cookies(page) -> None:
    """Se o Google interpuser o banner de consentimento, recusa o que der.

    Só clicamos em recusar/rejeitar — nunca em aceitar.
    """
    for rotulo in ("Rejeitar tudo", "Reject all", "Recusar tudo"):
        try:
            botao = page.get_by_role("button", name=rotulo)
            if botao.count():
                botao.first.click(timeout=3_000)
                page.wait_for_timeout(1_000)
                return
        except Exception:
            continue


def _limpar(itens: list[dict], condicoes: set[Condicao]) -> list[dict]:
    limpos = []
    for item in itens:
        condicao = _condicao(item.pop("texto", ""))
        if condicao not in condicoes:
            continue
        item["condicao"] = condicao
        item["loja"] = item["loja"] or NOME
        item["autor"] = None
        item["ano"] = None
        item["ofertas"] = None
        limpos.append(item)
    return limpos


def buscar(query: str, condicoes: set[Condicao], limite: int = 20) -> list[dict]:
    if not habilitado():
        return []
    if not ({Condicao.NOVO, Condicao.USADO} & condicoes):
        return []

    # Import tardio: sem Playwright instalado, a fonte se desliga em vez de
    # quebrar o import de `sources` (e derrubar a API inteira).
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        try:
            page = navegador.new_page(
                locale="pt-BR",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126.0.0.0 Safari/537.36",
            )
            page.goto(
                f"{BUSCA}?tbm=shop&q={query}&hl=pt-BR&gl=br",
                timeout=TIMEOUT_MS,
                wait_until="domcontentloaded",
            )
            _recusar_cookies(page)

            # O Google desvia para /sorry/index quando classifica o acesso
            # como robô. Aí não adianta esperar: nada vai renderizar.
            if "/sorry/" in page.url:
                raise BloqueadoPeloGoogle(
                    "Google exigiu verificação anti-robô (CAPTCHA) para esta busca"
                )

            # Espera os precos aparecerem; se nao vierem, devolve vazio.
            try:
                page.wait_for_function(
                    "() => /R\\$\\s*[\\d.,]+/.test(document.body.innerText)",
                    timeout=TIMEOUT_MS,
                )
            except Exception:
                return []

            brutos = page.evaluate(_EXTRAI_JS, limite)
        finally:
            navegador.close()

    return _limpar(brutos, condicoes)
