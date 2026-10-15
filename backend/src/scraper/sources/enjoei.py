"""Enjoei — anúncios públicos de livros e outros itens usados.

A listagem é renderizada por JavaScript, então a coleta usa o Playwright
compartilhado. A URL contém apenas o termo de busca; não envia filtros ou
parâmetros de paginação.
"""
import os
import re
import unicodedata
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from .. import navegador
from ..models import Condicao

NOME = "Enjoei"
BASE = "https://www.enjoei.com.br"

# Sobe um Chromium: o orquestrador consulta estas por último e dentro
# de uma sessão compartilhada, porque memória é o recurso escasso.
USA_NAVEGADOR = True


_MARCADORES_NOVO = re.compile(r"\b(?:novo|nova|novos|novas)\b")


def habilitado() -> bool:
    """Ligada por padrão; desligue com ENJOEI_ENABLED=0."""
    return os.getenv("ENJOEI_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "nao", "não",
    }


def _sem_acento(texto: str) -> str:
    decomposicao = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in decomposicao if not unicodedata.combining(c))


def _slug(query: str) -> str:
    """Monta o segmento legível usado pela rota pública da Enjoei."""
    sem_acento = _sem_acento(query)
    return re.sub(r"[^a-z0-9]+", "-", sem_acento).strip("-") or "busca"


def _url_busca(query: str) -> str:
    """URL pública /<termo>/s, sem filtros de ordenação ou paginação."""
    parametros = urlencode({"ref": "products_search", "q": query})
    return f"{BASE}/{_slug(query)}/s?{parametros}"


def _condicao(texto: str) -> Condicao:
    """Lê marcadores explícitos; anúncios sem indicação ficam como usados."""
    return (Condicao.NOVO if _MARCADORES_NOVO.search(_sem_acento(texto))
            else Condicao.USADO)


# Coleta somente links de anúncio (/p/), ascendendo até o menor card com preço.
# A extração usa elementos semânticos e texto visível, evitando classes geradas.
_EXTRAI_JS = r"""
(limite) => {
  const vistos = new Set();
  const itens = [];
  const links = [...document.querySelectorAll('a[href*="/p/"]')];
  const precoRe = /R\$\s*[\d.,]+/i;

  for (const link of links) {
    if (itens.length >= limite) break;

    const url = new URL(link.href, location.origin);
    if (url.origin !== location.origin || !url.pathname.startsWith('/p/')) continue;
    if (vistos.has(url.pathname)) continue;

    let card = null;
    let texto = '';
    for (let nivel = 0, candidato = link; nivel < 8 && candidato;
         nivel++, candidato = candidato.parentElement) {
      const textoCandidato = (candidato.innerText || '').trim();
      const anuncios = new Set(
        [...candidato.querySelectorAll('a[href*="/p/"]')]
          .map(a => new URL(a.href, location.origin).pathname)
      );
      if (precoRe.test(textoCandidato) && anuncios.size <= 1 && textoCandidato.length < 800) {
        card = candidato;
        texto = textoCandidato;
        break;
      }
    }

    if (!card) continue;
    const linhas = texto.split('\n').map(l => l.trim()).filter(Boolean);
    const preco = texto.match(precoRe)?.[0] || null;
    const heading = card.querySelector('h1, h2, h3, h4, [role="heading"]');
    const linkComTexto = [...card.querySelectorAll('a[href*="/p/"]')]
      .map(a => (a.innerText || '').trim())
      .find(t => t.length > 3);
    const candidatas = linhas.filter(l =>
      !precoRe.test(l) && !/^\d+(?:[.,]\d+)?%$/.test(l) &&
      !/^barateou$/i.test(l) && !/^\d+$/.test(l)
    );
    const nome = (heading?.innerText || linkComTexto ||
      [...candidatas].sort((a, b) => b.length - a.length)[0] || '').trim();
    if (!nome) continue;

    const indiceNome = linhas.findIndex(l => l.toLowerCase() === nome.toLowerCase());
    const depoisDoNome = indiceNome >= 0 ? linhas.slice(indiceNome + 1) : candidatas;
    const loja = depoisDoNome.filter(l =>
      !precoRe.test(l) && !/^\d+(?:[.,]\d+)?%$/.test(l) &&
      !/^barateou$/i.test(l)
    ).at(-1) || null;
    const imagem = [...card.querySelectorAll('img')]
      .map(i => i.currentSrc || i.src || i.getAttribute('data-src'))
      .find(u => u && /^https?:\/\//i.test(u)) || null;

    vistos.add(url.pathname);
    itens.push({nome, preco, loja, href: url.pathname, imagem, texto});
  }

  return itens;
}
"""


def _limpar(brutos: list[dict], condicoes: set[Condicao]) -> list[dict]:
    """Converte os cards em itens aceitos pelo normalizador comum."""
    if not ({Condicao.NOVO, Condicao.USADO} & condicoes):
        return []

    itens = []
    for bruto in brutos:
        nome = (bruto.get("nome") or "").strip()
        preco = bruto.get("preco")
        if not nome or not preco:
            continue

        condicao = _condicao(bruto.get("texto") or "")
        if condicao not in condicoes:
            continue

        link = None
        href = bruto.get("href")
        if isinstance(href, str) and href:
            parsed = urlsplit(urljoin(BASE, href))
            if (parsed.hostname in {"www.enjoei.com.br", "enjoei.com.br"}
                    and parsed.path.startswith("/p/")):
                # Descarta parâmetros de rastreamento do link do anúncio.
                link = urlunsplit(("https", "www.enjoei.com.br", parsed.path, "", ""))

        itens.append({
            "nome": nome,
            "preco": preco,
            "loja": (bruto.get("loja") or "").strip() or NOME,
            "condicao": condicao,
            "link": link,
            "imagem": bruto.get("imagem"),
            "autor": None,
            "ano": None,
            "ofertas": None,
        })

    return itens


def buscar(query: str, condicoes: set[Condicao], limite: int = 20) -> list[dict]:
    if not habilitado() or not ({Condicao.NOVO, Condicao.USADO} & condicoes):
        return []

    with navegador.pagina() as page:
        page.goto(
            _url_busca(query),
            timeout=navegador.TIMEOUT_MS,
            wait_until="domcontentloaded",
        )

        # `state="attached"` é obrigatório aqui: no padrão ("visible") a
        # espera estoura mesmo com os 35 anúncios já no DOM, porque o primeiro
        # link da grade não conta como visível — e a fonte devolvia sempre
        # lista vazia, em silêncio.
        # Busca vazia ou sem anúncios: resultado vazio legítimo.
        try:
            page.wait_for_selector(
                'a[href*="/p/"]', state="attached", timeout=10_000
            )
        except Exception:
            return []

        brutos = page.evaluate(_EXTRAI_JS, max(0, min(limite, 40)))

    return _limpar(brutos, condicoes)
