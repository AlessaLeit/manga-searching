"""Máscaras de entrada da API.

Uma máscara não rejeita nada: ela *normaliza* o valor que chegou para o
formato que o resto do sistema espera. Quem rejeita é a validação do schema
(`backend/src/schemas/search.py`).

O front aplica as mesmas regras enquanto o usuário digita, mas o back não
pode confiar nisso: a API também responde a curl, Postman e a qualquer outro
cliente.
"""
import re

TAMANHO_MAXIMO_EXPRESSAO = 60

# Pontuação que aparece de verdade em título de mangá ("Re:Zero", "Fruits
# Basket - Another", "Yotsuba&!"). O resto some.
_PONTUACAO_PERMITIDA = frozenset(" .,:'!?&+-")

_ESPACOS = re.compile(r"\s+")


def _permitido(caractere: str) -> bool:
    # isalnum() cobre letras acentuadas e caracteres japoneses, então
    # "Shingeki no Kyojin" e "進撃の巨人" passam inteiros.
    return caractere.isalnum() or caractere in _PONTUACAO_PERMITIDA


def mascarar_expressao(valor: str) -> str:
    """Limpa o termo de busca: tira símbolo estranho, espaço repetido e excesso.

    >>> mascarar_expressao("  <b>Naruto</b>   Gaiden!!  ")
    'bNarutob Gaiden!!'
    """
    if not isinstance(valor, str):
        return valor

    # Quebra de linha e tabulação viram espaço antes do filtro; sem isso
    # "one\npiece" viraria "onepiece".
    achatado = _ESPACOS.sub(" ", valor)

    limpo = "".join(c for c in achatado if _permitido(c))
    return _ESPACOS.sub(" ", limpo).strip()[:TAMANHO_MAXIMO_EXPRESSAO]


def mascarar_filtro(valor):
    """Aceita ?filters=NOVO, ?filters=' usado ' e devolve o valor canônico."""
    return valor.strip().lower() if isinstance(valor, str) else valor


def tem_conteudo_util(valor: str) -> bool:
    """Termo só com pontuação ("...", "!!") não identifica nenhum mangá."""
    return any(c.isalnum() for c in valor)
