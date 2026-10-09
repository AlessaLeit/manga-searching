"""Bing Shopping — ofertas de lojas grandes (sobretudo Amazon BR).

Vale como fonte porque alcança lojas que bloqueiam scraping direto: a Amazon
responde com bloqueio quando acessada de frente, mas suas ofertas aparecem
aqui, com preço e link.

Dois achados que ditaram a implementação:

1. `mkt=pt-BR` e `cc=br` são obrigatórios, e só juntos. Sem eles o Bing
   devolve 200 com uma página sem nenhuma oferta — falha silenciosa.
2. Via requests o resultado é intermitente (funciona uma vez, depois volta
   vazio, mesmo com minutos de espera). Com navegador real é consistente.
   Por isso esta fonte usa Playwright, como a do Google.

Os links dos cards são redirecionamentos do Bing (/aclick) com a URL real da
loja embutida em base64 no parâmetro `u`, que decodificamos para mandar o
usuário direto ao anúncio.
"""
import base64
import os
import re
import urllib.parse as urlparse

from .. import navegador
from ..models import Condicao

NOME = "Bing Shopping"
BUSCA = "https://www.bing.com/shop"

_MARCADORES_USADO = ("usado", "usada", "seminovo", "semi-novo", "used")


def habilitado() -> bool:
    """Ligada por padrão; desligue com BING_SHOPPING_ENABLED=0."""
    return os.getenv("BING_SHOPPING_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "nao", "não",
    }


def _condicao(texto: str) -> Condicao:
    minusculo = texto.lower()
    return (Condicao.USADO if any(m in minusculo for m in _MARCADORES_USADO)
            else Condicao.NOVO)


def link_real(href: str) -> str | None:
    """Extrai a URL da loja de dentro do redirecionamento do Bing."""
    if not href:
        return None
    if "/aclick" not in href:
        return href

    codificado = urlparse.parse_qs(urlparse.urlparse(href).query).get("u", [""])[0]
    if not codificado:
        return href

    try:
        # "===" cobre qualquer falta de padding; b64decode ignora o excesso.
        bruto = base64.b64decode(codificado + "===").decode("utf-8", "ignore")
    except Exception:
        return href

    destino = urlparse.unquote(bruto)
    return destino if destino.startswith("http") else href


# Lido dentro do navegador: os campos vêm de classes estáveis do Bing
# (br-offTtl, br-price, br-offSlrTxt), não de nomes gerados.
_EXTRAI_JS = """
(limite) => {
  const itens = [];
  const texto = (no, sel) => {
    const alvo = no.querySelector(sel);
    return alvo ? alvo.innerText.trim() : null;
  };

  for (const card of document.querySelectorAll('div.br-gOffCard')) {
    if (itens.length >= limite) break;

    const nome = texto(card, '.br-offTtl');
    const preco = texto(card, '.br-price');
    if (!nome || !preco) continue;

    const link = card.querySelector('a.br-offLink');

    // Cada card tem DUAS <img>: a primeira é um data:image de espera, a
    // segunda é a miniatura real (th.bing.com), preenchida só depois que o
    // Bing carrega a imagem. Por isso varremos todas e exigimos http —
    // pegar a primeira <img> devolveria sempre o placeholder.
    const imagem = [...card.querySelectorAll('img')]
      .map((i) => i.currentSrc || i.src || i.getAttribute('data-src'))
      .find((u) => u && u.startsWith('http')) || null;

    itens.push({
      nome,
      preco,
      loja: texto(card, '.br-offSlrTxt'),
      href: link ? link.getAttribute('href') : null,
      imagem,
      texto: card.innerText || '',
    });
  }

  return itens;
}
"""


# Proporção de capas exigida antes de extrair. Medindo, as 20 miniaturas
# ficam prontas em 1 a 4s, então dá para exigir todas; o timeout abaixo evita
# ficar refém de um card com imagem quebrada.
PROPORCAO_CAPAS = 1.0
ESPERA_CAPAS_MS = 6_000

_CAPAS_PRONTAS_JS = """
() => {
  const cards = [...document.querySelectorAll('div.br-gOffCard')];
  if (!cards.length) return false;

  const carregada = (card) => [...card.querySelectorAll('img')]
    .some((i) => (i.currentSrc || i.src || '').startsWith('http'));

  const prontas = cards.filter(carregada).length;
  return prontas >= Math.ceil(cards.length * %s);
}
""" % PROPORCAO_CAPAS


def _limpar(brutos: list[dict], condicoes: set[Condicao]) -> list[dict]:
    itens = []
    for bruto in brutos:
        # Só leitura: mutar `bruto` aqui faria uma segunda passada sobre os
        # mesmos dados perder o texto e classificar tudo como novo.
        condicao = _condicao(bruto.get("texto", ""))
        if condicao not in condicoes:
            continue

        itens.append({
            "nome": bruto["nome"],
            "preco": bruto["preco"],
            "loja": bruto.get("loja") or NOME,
            "condicao": condicao,
            "link": link_real(bruto.get("href") or ""),
            "imagem": bruto.get("imagem"),
            "autor": None,
            "ano": None,
            "ofertas": None,
        })
    return itens


def buscar(query: str, condicoes: set[Condicao], limite: int = 20) -> list[dict]:
    if not ({Condicao.NOVO, Condicao.USADO} & condicoes):
        return []

    with navegador.pagina() as page:
        page.goto(
            f"{BUSCA}?{urlparse.urlencode({'q': query, 'mkt': 'pt-BR', 'cc': 'br'})}",
            timeout=navegador.TIMEOUT_MS,
            wait_until="domcontentloaded",
        )

        # Busca sem resultado simplesmente não renderiza cards: o timeout
        # aqui é resposta vazia legítima, não erro.
        try:
            page.wait_for_selector("div.br-gOffCard", timeout=10_000)
        except Exception:
            return []

        # Os cards aparecem antes das miniaturas, e as capas entram em lotes:
        # medindo, ~8 de 20 estão prontas no instante zero e todas em ~1s.
        # Esperar só a primeira (o que fazíamos antes) extraía cedo demais e
        # perdia a maioria das capas. Se estourar, seguimos com as que deram:
        # capa é opcional, preço não.
        try:
            page.wait_for_function(_CAPAS_PRONTAS_JS, timeout=ESPERA_CAPAS_MS)
        except Exception:
            pass

        brutos = page.evaluate(_EXTRAI_JS, limite)

    return _limpar(brutos, condicoes)
