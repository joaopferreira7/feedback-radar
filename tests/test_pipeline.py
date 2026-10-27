"""Testes automatizados (não chamam a API real). Rodar com:  pytest"""
import json

import pandas as pd
import pytest

from feedback_radar import config
from feedback_radar.anonimizacao import anonimizar
from feedback_radar.classificador import (Estatisticas, ErroFormato, classificar_dataframe,
                                          classificar_lote, extrair_json)
from feedback_radar.leitura_csv import ErroValidacaoCSV, ler_csv
from feedback_radar.llm import ClienteSimulado, RespostaLLM
from feedback_radar.relatorio import gerar_relatorio, markdown_para_pdf, relatorio_markdown
from feedback_radar.validacao import calcular_metricas, tabela_de_erros


# ---------- Leitura do CSV ----------

def test_csv_ponto_e_virgula_cp1252_e_sinonimos():
    conteudo = "Comentário;Estrelas\nÓtimo atendimento;5\n;3\nPéssimo;9\n".encode("cp1252")
    df, avisos = ler_csv(conteudo)
    assert list(df["texto"]) == ["Ótimo atendimento", "Péssimo"]
    assert df["nota"].isna().iloc[1]  # nota 9 é inválida
    assert any("sem texto" in a for a in avisos)


def test_datas_iso_e_brasileiras():
    iso, _ = ler_csv(b"texto,data\nbom,2018-04-12\nruim,2018-01-05 10:30:00\n")
    assert list(iso["data"].dt.month) == [4, 1] and list(iso["data"].dt.day) == [12, 5]
    br, _ = ler_csv(b"texto,data\nbom,12/04/2018\nruim,05/01/2018\n")
    assert list(br["data"].dt.month) == [4, 1] and list(br["data"].dt.day) == [12, 5]


def test_csv_sem_coluna_texto():
    with pytest.raises(ErroValidacaoCSV, match="texto"):
        ler_csv(b"nome,nota\nAna,5\n")


def test_csv_vazio():
    with pytest.raises(ErroValidacaoCSV):
        ler_csv(b"   ")


# ---------- Anonimização ----------

def test_anonimizacao():
    texto = "O garçom João foi ótimo, liga (11) 98765-4321 ou ana@email.com @perfil_x"
    resultado = anonimizar(texto)
    assert "João" not in resultado and "98765" not in resultado and "ana@" not in resultado
    assert "[NOME]" in resultado and "[TELEFONE]" in resultado and "[EMAIL]" in resultado
    assert anonimizar("o garçom muito educado") == "o garçom muito educado"


# ---------- JSON e retry ----------

def test_extrair_json_com_markdown():
    assert extrair_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ErroFormato):
        extrair_json("desculpe, não consigo")


class ClienteFalhaUmaVez:
    """Primeiro devolve lixo, depois um JSON válido: o retry deve resolver."""

    def __init__(self):
        self.chamadas = 0

    def gerar(self, sistema, usuario, dados_simulacao=None):
        self.chamadas += 1
        if self.chamadas == 1:
            return RespostaLLM('{"classificacoes": [{"id": 1, "sentimento": "feliz"}]}')
        assert "rejeitada" in usuario  # o erro foi explicado ao modelo
        itens = [{"id": i["id"], "sentimento": "positivo", "temas": ["atendimento"],
                  "intensidade": 3, "resumo_curto": "ok ok"} for i in dados_simulacao]
        return RespostaLLM(json.dumps({"classificacoes": itens}))


def test_retry_corrige_json_invalido():
    stats = Estatisticas()
    cliente = ClienteFalhaUmaVez()
    resultado = classificar_lote(cliente, [{"id": 1, "texto": "bom"}], stats)
    assert resultado[1].sentimento == "positivo"
    assert stats.retries == 1 and cliente.chamadas == 2


class ClienteTemaInvalido:
    def gerar(self, sistema, usuario, dados_simulacao=None):
        itens = [{"id": i["id"], "sentimento": "negativo", "temas": ["estacionamento_inventado"],
                  "intensidade": 2, "resumo_curto": "xx xx"} for i in dados_simulacao]
        return RespostaLLM(json.dumps({"classificacoes": itens}))


def test_falha_permanente_marca_erro_sem_travar(monkeypatch):
    monkeypatch.setattr(config, "MAX_TENTATIVAS", 2)
    df = pd.DataFrame({"id": [1, 2, 3], "texto": ["a", "b", "c"]})
    resultado, stats = classificar_dataframe(df, ClienteTemaInvalido(), tamanho_lote=3)
    assert (resultado["status"] == "erro").all()
    assert stats.falhas == 3  # o lote foi dividido até isolar cada avaliação


class ClienteCotaAcaba:
    """Responde o primeiro lote e depois simula a cota diária esgotada."""

    def __init__(self):
        self.chamadas = 0

    def gerar(self, sistema, usuario, dados_simulacao=None):
        self.chamadas += 1
        if self.chamadas > 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED. You exceeded your current quota "
                               "(GenerateRequestsPerDayPerProjectPerModel-FreeTier)")
        return ClienteSimulado().gerar(sistema, usuario, dados_simulacao)


def test_cota_diaria_para_e_preserva_o_que_ja_foi_feito():
    df = pd.DataFrame({"id": [1, 2, 3, 4], "texto": ["ótimo", "péssimo", "bom", "ruim"]})
    cliente = ClienteCotaAcaba()
    resultado, stats = classificar_dataframe(df, cliente, tamanho_lote=2)
    assert list(resultado["status"]) == ["ok", "ok", "erro", "erro"]
    assert "cota" in stats.interrompido
    assert cliente.chamadas == 2  # não ficou insistindo depois da cota esgotada


# ---------- Pipeline completo no modo simulado ----------

def test_pipeline_simulado_e_relatorio():
    df, _ = ler_csv("data/exemplos/avaliacoes_exemplo.csv")
    cliente = ClienteSimulado()
    resultado, _ = classificar_dataframe(df, cliente, tamanho_lote=10)
    assert (resultado["status"] == "ok").all()
    assert set(resultado["sentimento"]) <= {"positivo", "neutro", "negativo"}

    relatorio, dados = gerar_relatorio(resultado, cliente)
    md = relatorio_markdown(relatorio, dados, resultado)
    assert "Prioridades" in md
    assert markdown_para_pdf(md)[:4] == b"%PDF"


# ---------- Métricas ----------

def test_metricas_validacao():
    gabarito = pd.DataFrame({
        "id": [1, 2, 3, 4], "texto": ["Parabéns, esperei 2h", "bom", "ruim", "ok mas caro"],
        "sentimento_humano": ["negativo", "positivo", "negativo", "neutro"],
        "temas_humano": ["demora", "outros", "qualidade_produto", "preco"],
    })
    ia = pd.DataFrame({
        "id": [1, 2, 3, 4], "status": ["ok"] * 4,
        "sentimento": ["positivo", "positivo", "negativo", "neutro"],
        "temas": ["demora", "outros", "qualidade_produto;atendimento", "preco"],
    })
    m = calcular_metricas(gabarito, ia)
    assert m["acuracia"] == pytest.approx(0.75)
    assert m["matriz_confusao"].loc["humano: negativo", "IA: positivo"] == 1
    erros = tabela_de_erros(m)
    assert list(erros["id"]) == [1]
    assert "ironia" in erros.iloc[0]["hipotese_automatica"]
