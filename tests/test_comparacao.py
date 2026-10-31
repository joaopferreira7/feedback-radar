"""Testes da comparação entre modelos e do cliente Groq/NVIDIA (sem chamar a internet)."""
import json

import httpx
import pandas as pd
import pytest

from feedback_radar.comparacao import acuracia_por_modelo, classificar_com_modelos, concordancia
from feedback_radar.leitura_csv import ler_csv
from feedback_radar.llm import ClienteOpenAICompativel, ClienteSimulado, ErroConfiguracao, ErroHTTP


def _api_falsa(respostas: list, pedidos: list):
    """Transporte HTTP que devolve as respostas na ordem e guarda os pedidos recebidos."""
    def tratar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(json.loads(pedido.content))
        status, corpo = respostas.pop(0)
        return httpx.Response(status, json=corpo) if isinstance(corpo, dict) else httpx.Response(status, text=corpo)
    return httpx.MockTransport(tratar)


def _cliente(respostas, pedidos):
    return ClienteOpenAICompativel("Groq", "https://api.groq.com/openai/v1", "chave-de-teste",
                                   "modelo-x", "https://console.groq.com/keys",
                                   transporte=_api_falsa(respostas, pedidos))


def test_cliente_openai_compativel_le_resposta_e_tokens():
    conteudo = '<think>pensando {em chaves}</think>{"classificacoes": []}'
    pedidos = []
    c = _cliente([(200, {"choices": [{"message": {"content": conteudo}}],
                         "usage": {"prompt_tokens": 120, "completion_tokens": 30}})], pedidos)
    r = c.gerar("sistema", "usuario")
    assert r.texto == '{"classificacoes": []}'  # o bloco <think> foi removido
    assert (r.tokens_entrada, r.tokens_saida) == (120, 30)
    assert pedidos[0]["temperature"] == 0.0 and pedidos[0]["response_format"] == {"type": "json_object"}


def test_cliente_repete_sem_modo_json_quando_o_modelo_nao_aceita():
    pedidos = []
    c = _cliente([(400, "response_format is not supported by this model"),
                  (200, {"choices": [{"message": {"content": "{}"}}]})], pedidos)
    assert c.gerar("s", "u").texto == "{}"
    assert "response_format" in pedidos[0] and "response_format" not in pedidos[1]


def test_json_invalido_do_groq_vira_erro_de_formato_e_nao_erro_de_api():
    corpo = {"error": {"code": "json_validate_failed", "failed_generation": "isto não é json"}}
    c = _cliente([(400, corpo)], [])
    assert c.gerar("s", "u").texto == "isto não é json"  # o validador rejeita e o pipeline repete


def test_cliente_erro_http_tem_codigo_para_o_retry():
    c = _cliente([(429, "Rate limit reached")], [])
    with pytest.raises(ErroHTTP) as erro:
        c.gerar("s", "u")
    assert erro.value.code == 429


def test_cliente_sem_chave():
    with pytest.raises(ErroConfiguracao, match="console.groq.com"):
        ClienteOpenAICompativel("Groq", "https://x", "", "m", "https://console.groq.com/keys")


class ClienteDiscorda:
    """Classifica tudo como negativo, para gerar discordância com o simulado."""

    def gerar(self, sistema, usuario, dados_simulacao=None):
        from feedback_radar.llm import RespostaLLM
        itens = [{"id": i["id"], "sentimento": "negativo", "temas": ["outros"], "intensidade": 3,
                  "resumo_curto": "resumo"} for i in dados_simulacao]
        return RespostaLLM(json.dumps({"classificacoes": itens}))


def test_comparacao_entre_modelos():
    df, _ = ler_csv("data/exemplos/avaliacoes_exemplo.csv")
    resultados, stats = classificar_com_modelos(
        df.head(20), {"regras": ClienteSimulado(), "pessimista": ClienteDiscorda(), "regras2": ClienteSimulado()},
        tamanho_lote=10)
    k = concordancia(resultados)
    assert k["comparadas"] == 20
    assert k["sentimento"].loc["regras", "regras2"] == 1.0  # o mesmo modelo concorda consigo
    negativas = (resultados["regras"]["sentimento"] == "negativo").mean()
    assert k["sentimento"].loc["regras", "pessimista"] == pytest.approx(negativas)
    assert len(k["divergentes"]) == 20 - k["todas_iguais"]
    assert {"id", "texto", "regras", "pessimista"} <= set(k["divergentes"].columns)

    gabarito = pd.DataFrame({"id": resultados["regras"]["id"], "texto": resultados["regras"]["texto"],
                             "sentimento_humano": "negativo", "temas_humano": "outros"})
    notas = acuracia_por_modelo(resultados, gabarito).set_index("modelo")
    assert notas.loc["pessimista", "acuracia"] == 1.0  # no gabarito tudo é negativo
