"""Limpeza, filtro de relevância e ordenação dos itens crus das fontes."""
import re
import unicodedata

from .models import Condicao, Produto

# Fração mínima dos termos da busca que precisa aparecer no título.
# As lojas caem em busca aproximada quando não há resultado exato e devolvem
# catálogo aleatório; sem esse corte, "xyzabc" retorna 40 livros irrelevantes.
LIMIAR_RELEVANCIA = 0.6


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


def e_relevante(nome: str, query: str) -> bool:
    procurados = _tokens(query)
    if not procurados:
        return True
    encontrados = procurados & _tokens(nome)
    return len(encontrados) / len(procurados) >= LIMIAR_RELEVANCIA


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
            link=item.get("link"),
            autor=item.get("autor"),
            ano=item.get("ano"),
            ofertas=item.get("ofertas"),
        ))

    produtos.sort(key=_chave_ordem)
    return produtos
