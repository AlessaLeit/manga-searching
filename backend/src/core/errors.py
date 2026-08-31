"""Tratamento centralizado de erros da API.

Todo erro sai daqui no mesmo formato — `{"detail": "mensagem"}` — porque é
isso que o front lê para mostrar ao usuário. Um traceback nunca vaza para a
resposta: ele vai para o log do servidor.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("mangasearch")

# Nomes técnicos dos campos traduzidos para algo que o usuário entenda.
_APELIDOS = {
    "search_expression": "pesquisa",
    "filters": "filtro",
}


class FonteIndisponivelError(Exception):
    """Nenhuma fonte respondeu: erro de conexão com os sites consultados."""

    def __init__(self, fontes: list[str]):
        self.fontes = fontes
        super().__init__(", ".join(fontes))


def _nome_do_campo(loc: tuple) -> str:
    """Extrai o campo de loc = ("query", "filters", 0).

    O último item pode ser o índice dentro de uma lista, que não diz nada ao
    usuário; interessa o último nome.
    """
    nomes = [parte for parte in loc if isinstance(parte, str)]
    campo = nomes[-1] if nomes else "campo"
    return _APELIDOS.get(campo, campo)


def _erro_para_mensagem(erro: dict) -> str:
    """Transforma um erro do pydantic em uma frase legível."""
    campo = _nome_do_campo(erro.get("loc") or ())
    tipo = erro.get("type", "")

    if tipo == "missing":
        return f"O campo '{campo}' é obrigatório."
    if tipo in {"string_too_short", "too_short"}:
        return f"O campo '{campo}' está curto demais."
    if tipo in {"string_too_long", "too_long"}:
        return f"O campo '{campo}' está longo demais."
    if tipo == "enum":
        return (f"Valor inválido para '{campo}'. "
                f"{erro.get('msg', '')}".replace("Input should be", "Use").strip())

    # Validadores próprios já escrevem a mensagem final em português.
    return erro.get("msg", f"Valor inválido para '{campo}'.").removeprefix(
        "Value error, "
    )


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    """Liga os tratadores na aplicação. Chamado uma vez, no main."""

    @app.exception_handler(RequestValidationError)
    async def dados_invalidos(_: Request, exc: RequestValidationError):
        """422 — o cliente mandou dados que não passam na validação."""
        erros = exc.errors()
        mensagem = (_erro_para_mensagem(erros[0]) if erros
                    else "Dados da requisição inválidos.")

        return JSONResponse(
            # 422 literal: a constante mudou de nome entre versões do starlette.
            status_code=422,
            # `errors` fica disponível para quem quiser detalhe campo a campo.
            content={"detail": mensagem, "errors": len(erros)},
        )

    @app.exception_handler(FonteIndisponivelError)
    async def fonte_indisponivel(_: Request, exc: FonteIndisponivelError):
        """502 — a API está de pé, mas os sites consultados não responderam."""
        logger.warning("fontes indisponíveis: %s", exc)

        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detail": "As lojas consultadas estão indisponíveis no momento. "
                          "Tente novamente em alguns instantes.",
                "fontes_com_falha": exc.fontes,
            },
        )

    @app.exception_handler(TimeoutError)
    async def tempo_esgotado(_: Request, exc: TimeoutError):
        """504 — a busca demorou mais do que o limite configurado."""
        logger.warning("busca excedeu o tempo limite")

        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": "A busca demorou demais para responder. "
                               "Tente novamente."},
        )

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_: Request, exc: StarletteHTTPException):
        """Mantém 404/405/etc. no mesmo formato dos demais erros."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def erro_inesperado(_: Request, exc: Exception):
        """500 — bug não previsto. Log completo aqui, mensagem genérica lá."""
        logger.exception("erro inesperado: %s", exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno no servidor. Tente novamente."},
        )
