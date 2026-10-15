"""As fontes leves nunca podem ficar reféns das que sobem navegador.

A VM tem 1 GB. Subir três Chromium por busca a derrubou: o servidor parou de
responder até o /health, e toda busca virava 504. Estes testes travam as
defesas que vieram daí.
"""
import threading
import time

import pytest

from backend.src.scraper import navegador, scraper
from backend.src.scraper.models import Condicao


class _FonteLeve:
    """Responde por HTTP, rápido."""
    USA_NAVEGADOR = False

    def __init__(self, nome="Leve"):
        self.NOME = nome
        self.chamada = False

    def buscar(self, query, condicoes, limite):
        self.chamada = True
        return [{"nome": "Berserk Vol. 1", "preco": "R$ 30,00", "loja": self.NOME,
                 "condicao": Condicao.USADO, "link": f"https://x/{self.NOME}"}]


class _FontePesada:
    """Sobe navegador. Pode demorar o quanto o teste mandar."""
    USA_NAVEGADOR = True

    def __init__(self, nome="Pesada", demora=0.0):
        self.NOME = nome
        self.demora = demora
        self.chamada = False

    def buscar(self, query, condicoes, limite):
        self.chamada = True
        time.sleep(self.demora)
        return [{"nome": "Berserk Vol. 2", "preco": "R$ 40,00", "loja": self.NOME,
                 "condicao": Condicao.USADO, "link": f"https://y/{self.NOME}"}]


@pytest.fixture
def sem_navegador_real(monkeypatch):
    """Neutraliza o Chromium: aqui interessa a orquestração, não o browser."""
    from contextlib import contextmanager

    @contextmanager
    def falsa():
        yield

    monkeypatch.setattr(navegador, "sessao", falsa)


def test_leves_respondem_mesmo_sem_tempo_para_as_pesadas(monkeypatch,
                                                         sem_navegador_real):
    """Regressão: a busca inteira virava 504 por causa das fontes pesadas."""
    leve, pesada = _FonteLeve(), _FontePesada()
    monkeypatch.setattr(scraper, "FONTES", [leve, pesada])

    # Orçamento abaixo do mínimo para uma fonte com navegador.
    resultado = scraper.buscar("berserk", {Condicao.USADO},
                               orcamento_segundos=1.0)

    assert leve.chamada, "a fonte leve precisa rodar sempre"
    assert not pesada.chamada, "sem tempo, a pesada nem deve ser tentada"
    assert resultado.total_opcoes == 1
    assert resultado.fontes_consultadas == ["Leve"]
    assert resultado.fontes_com_falha == ["Pesada"]


def test_leves_vem_antes_das_pesadas(monkeypatch, sem_navegador_real):
    ordem = []

    class _Registra(_FonteLeve):
        def buscar(self, query, condicoes, limite):
            ordem.append(self.NOME)
            return []

    class _RegistraPesada(_FontePesada):
        def buscar(self, query, condicoes, limite):
            ordem.append(self.NOME)
            return []

    # Pesada declarada ANTES da leve: a ordem da lista não deve mandar.
    monkeypatch.setattr(scraper, "FONTES",
                        [_RegistraPesada("Pesada"), _Registra("Leve")])

    scraper.buscar("berserk", {Condicao.USADO}, orcamento_segundos=60)

    assert ordem == ["Leve", "Pesada"]


def test_uma_busca_com_navegador_por_vez(monkeypatch, sem_navegador_real):
    """Duas instâncias do Chromium não cabem em 1 GB."""
    simultaneas = []
    pico = []

    class _Concorrente(_FontePesada):
        def buscar(self, query, condicoes, limite):
            simultaneas.append(1)
            pico.append(len(simultaneas))
            time.sleep(0.3)
            simultaneas.pop()
            return []

    monkeypatch.setattr(scraper, "FONTES", [_Concorrente("Pesada")])

    threads = [threading.Thread(
        target=scraper.buscar, args=("berserk", {Condicao.USADO}),
        kwargs={"orcamento_segundos": 60}) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max(pico) == 1, f"rodaram {max(pico)} buscas com navegador ao mesmo tempo"


def test_servidor_ocupado_entrega_as_leves_em_vez_de_esperar(monkeypatch,
                                                             sem_navegador_real):
    """Sob carga, degradar é melhor que enfileirar até estourar o prazo."""
    leve = _FonteLeve()
    monkeypatch.setattr(scraper, "FONTES", [leve, _FontePesada(demora=5)])

    # Semáforo já tomado por outra busca.
    scraper._VEZ_DO_NAVEGADOR.acquire()
    try:
        comeco = time.monotonic()
        resultado = scraper.buscar("berserk", {Condicao.USADO},
                                   orcamento_segundos=14)
        gasto = time.monotonic() - comeco
    finally:
        scraper._VEZ_DO_NAVEGADOR.release()

    assert resultado.total_opcoes == 1, "as leves precisam chegar ao usuário"
    assert resultado.fontes_com_falha == ["Pesada"]
    assert gasto < 5, f"esperou {gasto:.1f}s pela vez em vez de desistir"


def test_chromium_ausente_nao_derruba_a_busca(monkeypatch):
    """Sem navegador instalado, as leves seguem respondendo."""
    from contextlib import contextmanager

    @contextmanager
    def explode():
        raise navegador.PlaywrightIndisponivel("sem chromium")
        yield  # pragma: no cover

    monkeypatch.setattr(navegador, "sessao", explode)

    leve = _FonteLeve()
    monkeypatch.setattr(scraper, "FONTES", [leve, _FontePesada()])

    resultado = scraper.buscar("berserk", {Condicao.USADO},
                               orcamento_segundos=60)

    assert resultado.total_opcoes == 1
    assert resultado.fontes_com_falha == ["Pesada"]


def test_sem_orcamento_tudo_roda(monkeypatch, sem_navegador_real):
    """Uso direto do scraper (scripts, testes) não deve ganhar prazo oculto."""
    leve, pesada = _FonteLeve(), _FontePesada()
    monkeypatch.setattr(scraper, "FONTES", [leve, pesada])

    resultado = scraper.buscar("berserk", {Condicao.USADO})

    assert leve.chamada and pesada.chamada
    assert resultado.fontes_com_falha == []


def test_fontes_pesadas_compartilham_uma_sessao(monkeypatch):
    """Uma sessão por busca, não uma por fonte — é o cerne da economia."""
    sessoes = []
    from contextlib import contextmanager

    @contextmanager
    def contando():
        sessoes.append(1)
        yield

    monkeypatch.setattr(navegador, "sessao", contando)
    monkeypatch.setattr(scraper, "FONTES", [
        _FontePesada("A"), _FontePesada("B"), _FontePesada("C"),
    ])

    scraper.buscar("berserk", {Condicao.USADO}, orcamento_segundos=60)

    assert len(sessoes) == 1, f"abriu {len(sessoes)} navegadores para 3 fontes"
