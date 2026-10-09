"""Limpeza, filtro de relevância e ordenação dos itens crus das fontes."""
import re
import unicodedata
from difflib import SequenceMatcher

from .models import Condicao, Produto

# Fração mínima dos termos da busca que precisa aparecer no título.
# As lojas caem em busca aproximada quando não há resultado exato e devolvem
# catálogo aleatório; sem esse corte, "xyzabc" retorna 40 livros irrelevantes.
LIMIAR_RELEVANCIA = 0.6

# Quanto dois termos precisam se parecer para contarem como o mesmo.
# O usuário digita "demons slayer" e o título é "Demon Slayer": sem tolerância
# a busca inteira era descartada por causa de um "s".
LIMIAR_SEMELHANCA = 0.85


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokens(texto: str) -> set[str]:
    limpo = re.sub(r"[^a-z0-9\s]", " ", _sem_acento(texto).lower())
    return {t for t in limpo.split() if len(t) >= 3}


def _limpar_preco(texto) -> float | None:
    """Converte "R$ 1.234,56" em 1234.56. Aceita valor já numérico."""
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)

    bruto = texto.replace("R$", "").replace(" ", " ")
    m = re.search(r"\d[\d.,]*", bruto)
    if not m:
        return None

    valor = m.group(0)
    # pt-BR: ponto é milhar, vírgula é decimal.
    valor = valor.replace(".", "").replace(",", ".") if "," in valor else valor
    try:
        return float(valor)
    except ValueError:
        return None


def _sao_o_mesmo_termo(procurado: str, achado: str) -> bool:
    """Compara dois termos tolerando plural e erro de digitação."""
    if procurado == achado:
        return True

    # Cobre plural e prefixo ("demons"/"demon", "manga"/"mangas").
    if min(len(procurado), len(achado)) >= 4 and (
        procurado.startswith(achado) or achado.startswith(procurado)
    ):
        return True

    return SequenceMatcher(None, procurado, achado).ratio() >= LIMIAR_SEMELHANCA


def e_relevante(nome: str, query: str) -> bool:
    procurados = _tokens(query)
    if not procurados:
        return True

    no_titulo = _tokens(nome)
    encontrados = sum(
        any(_sao_o_mesmo_termo(p, t) for t in no_titulo) for p in procurados
    )
    return encontrados / len(procurados) >= LIMIAR_RELEVANCIA


def _limpar_url(valor, aceitar_embutida: bool = False) -> str | None:
    """Só deixa passar URL que o navegador pode abrir com segurança.

    As URLs vêm de HTML de terceiros. Um `javascript:...` num href, ou num
    src de imagem, viraria execução de código na página do usuário — então
    aceitamos apenas http/https (e data:image, que algumas lojas usam para
    miniatura embutida).
    """
    if not isinstance(valor, str):
        return None

    url = valor.strip()
    if url.startswith(("http://", "https://")):
        return url
    if aceitar_embutida and url.startswith("data:image/"):
        return url
    # Protocolo relativo ("//host/capa.jpg") é comum em HTML de loja.
    if url.startswith("//"):
        return f"https:{url}"

    return None


def _chave_ordem(p: Produto) -> tuple:
    # Itens com preço primeiro (mais barato antes); leitura online por último.
    return (p.preco is None, p.preco if p.preco is not None else 0.0)


def normalizar(itens: list[dict], query: str) -> list[Produto]:
    produtos: list[Produto] = []
    vistos: set[tuple] = set()

    for item in itens:
        nome = (item.get("nome") or "").strip()
        if not nome or not e_relevante(nome, query):
            continue

        condicao = Condicao(item.get("condicao", Condicao.NOVO))
        preco = _limpar_preco(item.get("preco"))

        # Opção de compra sem preço legível não serve para comparar.
        if preco is None and condicao is not Condicao.ONLINE:
            continue

        chave = (nome.lower(), condicao, item.get("link"))
        if chave in vistos:
            continue
        vistos.add(chave)

        produtos.append(Produto(
            nome=nome,
            condicao=condicao,
            loja=item.get("loja") or "desconhecida",
            preco=preco,
            link=_limpar_url(item.get("link")),
            imagem=_limpar_url(item.get("imagem"), aceitar_embutida=True),
            autor=item.get("autor"),
            ano=item.get("ano"),
            ofertas=item.get("ofertas"),
        ))

    produtos.sort(key=_chave_ordem)
    return produtos
