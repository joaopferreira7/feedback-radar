"""Testes do agente analista (não chamam a API real)."""
import json
from pathlib import Path

import pytest

from feedback_radar.agente import Ferramentas, criar_indice, perguntar
from feedback_radar.busca import IndiceBusca
from feedback_radar.classificador import classificar_dataframe
from feedback_radar.leitura_csv import ler_csv
from feedback_radar.llm import ClienteSimulado, RespostaLLM

EXEMPLO = Path(__file__).parent.parent / "data" / "exemplos" / "avaliacoes_exemplo.csv"


@pytest.fixture(scope="module")
def df():
    bruto, _ = ler_csv(str(EXEMPLO))
    classificado, _ = classificar_dataframe(bruto, ClienteSimulado())
    return classificado


@pytest.fixture(scope="module")
def indice(df):
    return criar_indice(df, ClienteSimulado())


class ClienteRoteiro:
    """Devolve respostas prontas, uma por chamada, e guarda os prompts recebidos."""

    def __init__(self, respostas: list[dict]):
        self.respostas = [json.dumps(r, ensure_ascii=False) for r in respostas]
        self.prompts = []

    def gerar(self, sistema, usuario, dados_simulacao=None):
        self.prompts.append(usuario)
        return RespostaLLM(texto=self.respostas.pop(0))


# ---------- Busca ----------

def test_busca_tfidf_encontra_assunto():
    indice = IndiceBusca([1, 2, 3], ["a pizza chegou fria", "garçom muito educado", "banheiro sujo"])
    assert indice.metodo == "tfidf"
    assert indice.buscar("pizza fria", n=2)[0][0] == 1
    assert indice.buscar("pizza", ids_permitidos={2, 3}) == []  # filtro respeitado


def test_busca_usa_embeddings_quando_disponivel():
    class ClienteVetores:
        def embeddings(self, textos, tipo="RETRIEVAL_DOCUMENT"):
            return [[1.0, 0.0] if "frio" in t else [0.0, 1.0] for t in textos]

    indice = IndiceBusca([1, 2], ["veio frio", "ótimo atendimento"], ClienteVetores())
    assert indice.metodo == "embeddings"
    assert indice.buscar("lanche frio", n=1)[0][0] == 1


# ---------- Ferramentas ----------

def test_contar_soma_o_total(df, indice):
    f = Ferramentas(df, indice)
    resultado = f.contar("sentimento")
    assert sum(resultado["grupos"].values()) == resultado["total"] == (df["status"] == "ok").sum()


def test_ferramenta_com_argumento_invalido_devolve_erro(df, indice):
    f = Ferramentas(df, indice)
    assert "erro" in f.executar("contar", {"agrupar_por": "cor"})
    assert "erro" in f.executar("contar", {"agrupar_por": "tema", "tema": "inexistente"})
    assert "erro" in f.executar("apagar_tudo", {})
    assert "erro" in f.executar("comparar_periodos", {"inicio_a": "ontem", "fim_a": "x",
                                                      "inicio_b": "2026-01-01", "fim_b": "2026-02-01"})


def test_comparar_periodos(df, indice):
    resultado = Ferramentas(df, indice).comparar_periodos("2026-01-01", "2026-01-31", "2026-02-01", "2026-02-28")
    assert resultado["periodo_a"]["total"] > 0 and resultado["periodo_b"]["total"] > 0


# ---------- Laço do agente ----------

def test_agente_simulado_investiga_e_cita_avaliacoes_reais(df, indice):
    r = perguntar("Quais as reclamações sobre demora?", df, ClienteSimulado(), indice)
    ferramentas = [p.ferramenta for p in r.passos if p.ferramenta]
    assert ferramentas == ["buscar_avaliacoes", "contar"]
    assert r.citacoes and set(r.citacoes) <= set(df["id"].astype(int))
    assert r.chamadas == 3


def test_agente_rejeita_citacao_inventada(df, indice):
    cliente = ClienteRoteiro([
        {"acao": "responder", "resposta": "Os clientes reclamam muito de demora.", "citacoes": [9999]},
        {"acao": "ferramenta", "ferramenta": "buscar_avaliacoes", "argumentos": {"consulta": "demora"}},
        {"acao": "responder", "resposta": "Os clientes reclamam de demora na entrega.", "citacoes": [9999]},
    ])
    r = perguntar("demora?", df, cliente, indice, max_passos=3)
    assert "9999" in cliente.prompts[1]  # o erro foi explicado ao modelo
    assert r.citacoes == [] and r.citacoes_rejeitadas == [9999]  # no último passo, a citação é descartada


def test_agente_se_recupera_de_json_invalido_e_ferramenta_errada(df, indice):
    cliente = ClienteRoteiro([
        {"oi": "sem formato"},
        {"acao": "ferramenta", "ferramenta": "contar", "argumentos": {"agrupar_por": "cor"}},
        {"acao": "ferramenta", "ferramenta": "contar", "argumentos": {"agrupar_por": "tema"}},
        {"acao": "responder", "resposta": "Qualidade do produto é o tema mais citado.", "citacoes": []},
    ])
    r = perguntar("qual o tema mais citado?", df, cliente, indice)
    assert r.resposta.startswith("Qualidade")
    assert "erro" in r.passos[1].resultado and "grupos" in r.passos[2].resultado
