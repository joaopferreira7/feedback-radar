"""Agente analista: responde perguntas do dono sobre as avaliações.

Diferente da classificação e do relatório (uma pergunta, uma resposta), aqui o
LLM conduz uma investigação em vários passos, no padrão ReAct (raciocinar e agir):

  1. recebe a pergunta e uma visão geral dos dados;
  2. decide qual ferramenta usar e com quais argumentos;
  3. o CÓDIGO executa a ferramenta (busca semântica, contagens, ranking,
     comparação de períodos) e devolve o resultado ao LLM;
  4. repete 2 e 3 até ter informação suficiente e então responde.

Divisão de responsabilidades (a mesma ideia do relatório):
- o LLM decide O QUE investigar e escreve a resposta;
- o código faz todas as contas e guarda quais avaliações o LLM realmente viu;
- citações de avaliações que não apareceram nos resultados são rejeitadas, e
  o texto citado ao dono é sempre o ORIGINAL da avaliação.
"""
import json
import time
from dataclasses import dataclass, field

import pandas as pd
from pydantic import ValidationError

from . import config
from .busca import IndiceBusca
from .classificador import ErroAPI, ErroFormato, extrair_json, lista_temas
from .esquemas import AcaoAgente
from .prompts import SISTEMA_AGENTE, montar_prompt_agente
from .relatorio import calcular_impacto
from .taxonomia import SENTIMENTOS, TEMAS_VALIDOS

AGRUPAMENTOS = ["sentimento", "tema", "mes", "fonte", "nota"]
MAX_CARACTERES_RESULTADO = 300  # corta textos longos devolvidos ao LLM (custo)


# ---------------------------------------------------------------------------
# Ferramentas (executadas pelo código, nunca pelo LLM)
# ---------------------------------------------------------------------------

class Ferramentas:
    def __init__(self, df: pd.DataFrame, indice: IndiceBusca):
        df = df[df["status"] == "ok"].copy()
        df["id"] = df["id"].astype(int)
        df["lista_temas"] = df["temas"].map(lista_temas)
        if "data" in df:
            df["data"] = pd.to_datetime(df["data"], errors="coerce")
        self.df = df
        self.indice = indice
        self.col_texto = "texto_enviado" if "texto_enviado" in df else "texto"
        self.ids_vistos: set[int] = set()  # avaliações que o LLM recebeu (só estas podem ser citadas)

    def executar(self, nome: str, argumentos: dict) -> dict:
        funcoes = {"buscar_avaliacoes": self.buscar_avaliacoes, "contar": self.contar,
                   "ranking_impacto": self.ranking_impacto, "comparar_periodos": self.comparar_periodos}
        if nome not in funcoes:
            return {"erro": f"ferramenta desconhecida '{nome}'. Use uma de: {', '.join(funcoes)}"}
        try:
            return funcoes[nome](**argumentos)
        except TypeError as erro:  # argumento com nome errado
            return {"erro": f"argumentos inválidos para {nome}: {erro}"}
        except ValueError as erro:
            return {"erro": str(erro)}

    def visao_geral(self) -> dict:
        df = self.df
        visao = {"total_avaliacoes": len(df),
                 "sentimento": df["sentimento"].value_counts().to_dict(),
                 "colunas_disponiveis": [c for c in ["data", "nota", "fonte"] if c in df and df[c].notna().any()]}
        if "data" in df and df["data"].notna().any():
            visao["periodo"] = f"{df['data'].min():%Y-%m-%d} a {df['data'].max():%Y-%m-%d}"
        if "fonte" in df:
            visao["fontes"] = sorted(df["fonte"].dropna().astype(str).unique().tolist())
        return visao

    # ----- filtros comuns -----

    def _filtrar(self, sentimento=None, tema=None, data_inicio=None, data_fim=None) -> pd.DataFrame:
        df = self.df
        if sentimento:
            if sentimento not in SENTIMENTOS:
                raise ValueError(f"sentimento inválido '{sentimento}'. Use: {SENTIMENTOS}")
            df = df[df["sentimento"] == sentimento]
        if tema:
            if tema not in TEMAS_VALIDOS:
                raise ValueError(f"tema inválido '{tema}'. Use: {TEMAS_VALIDOS}")
            df = df[df["lista_temas"].map(lambda temas: tema in temas)]
        if data_inicio or data_fim:
            if "data" not in df or df["data"].isna().all():
                raise ValueError("estas avaliações não têm data; não é possível filtrar por período")
            if data_inicio:
                df = df[df["data"] >= _data(data_inicio)]
            if data_fim:
                df = df[df["data"] <= _data(data_fim)]
        return df

    def _resumo_sentimento(self, df: pd.DataFrame) -> dict:
        total = len(df)
        resumo = {"total": total}
        for s in SENTIMENTOS:
            resumo[f"pct_{s}"] = round(100 * float((df["sentimento"] == s).mean()), 1) if total else 0
        if "nota" in df and df["nota"].notna().any():
            resumo["nota_media"] = round(float(pd.to_numeric(df["nota"], errors="coerce").mean()), 2)
        return resumo

    # ----- as ferramentas -----

    def buscar_avaliacoes(self, consulta: str, sentimento=None, tema=None, data_inicio=None,
                          data_fim=None, n: int = 8) -> dict:
        if not consulta or not str(consulta).strip():
            raise ValueError("informe uma 'consulta' com o assunto a buscar")
        n = max(1, min(15, int(n)))
        candidatos = self._filtrar(sentimento, tema, data_inicio, data_fim)
        achados = self.indice.buscar(str(consulta), n, ids_permitidos=set(candidatos["id"]))
        linhas = self.df.set_index("id")
        resultado = []
        for id_, similaridade in achados:
            r = linhas.loc[id_]
            item = {"id": id_, "texto": str(r[self.col_texto])[:MAX_CARACTERES_RESULTADO],
                    "sentimento": r["sentimento"], "temas": r["lista_temas"], "similaridade": similaridade}
            if "nota" in linhas and pd.notna(r["nota"]):
                item["nota"] = int(r["nota"])
            if "data" in linhas and pd.notna(r["data"]):
                item["data"] = f"{r['data']:%Y-%m-%d}"
            resultado.append(item)
            self.ids_vistos.add(id_)
        return {"encontradas": len(resultado), "total_no_filtro": len(candidatos), "avaliacoes": resultado}

    def contar(self, agrupar_por: str, sentimento=None, tema=None, data_inicio=None, data_fim=None) -> dict:
        if agrupar_por not in AGRUPAMENTOS:
            raise ValueError(f"agrupar_por inválido '{agrupar_por}'. Use: {AGRUPAMENTOS}")
        df = self._filtrar(sentimento, tema, data_inicio, data_fim)
        if agrupar_por == "tema":
            contagem = df.explode("lista_temas")["lista_temas"].value_counts()
        elif agrupar_por == "mes":
            if "data" not in df or df["data"].isna().all():
                raise ValueError("estas avaliações não têm data")
            contagem = df["data"].dt.strftime("%Y-%m").value_counts().sort_index()
        else:
            if agrupar_por not in df:
                raise ValueError(f"os dados não têm a coluna '{agrupar_por}'")
            contagem = df[agrupar_por].value_counts()
        grupos = {str(k).replace(".0", ""): int(v) for k, v in contagem.items()}
        return {**self._resumo_sentimento(df), "agrupado_por": agrupar_por, "grupos": grupos}

    def ranking_impacto(self, data_inicio=None, data_fim=None) -> dict:
        df = self._filtrar(data_inicio=data_inicio, data_fim=data_fim)
        if df.empty:
            return {"total": 0, "ranking": []}
        tabela = calcular_impacto(df.assign(temas=df["lista_temas"].map(";".join)))
        ranking = [{"tema": r.tema, "mencoes": int(r.mencoes), "negativas": int(r.negativas),
                    "pct_negativas": round(r.pct_negativas, 1), "impacto": round(r.impacto, 3)}
                   for r in tabela.head(6).itertuples()]
        return {"total": len(df), "ranking": ranking}

    def comparar_periodos(self, inicio_a: str, fim_a: str, inicio_b: str, fim_b: str) -> dict:
        resultado = {}
        for rotulo, inicio, fim in [("periodo_a", inicio_a, fim_a), ("periodo_b", inicio_b, fim_b)]:
            df = self._filtrar(data_inicio=inicio, data_fim=fim)
            negativas = df[df["sentimento"] == "negativo"].explode("lista_temas")["lista_temas"]
            resultado[rotulo] = {"de": inicio, "ate": fim, **self._resumo_sentimento(df),
                                 "negativas_por_tema": {k: int(v) for k, v in negativas.value_counts().items()}}
        return resultado


def _data(valor) -> pd.Timestamp:
    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        raise ValueError(f"data inválida '{valor}'. Use o formato AAAA-MM-DD")
    return data


# ---------------------------------------------------------------------------
# Laço do agente
# ---------------------------------------------------------------------------

@dataclass
class Passo:
    """Um passo da investigação, mostrado ao usuário em "como a IA chegou nisso"."""
    pensamento: str
    ferramenta: str | None = None
    argumentos: dict = field(default_factory=dict)
    resultado: dict | None = None
    erro: str | None = None


@dataclass
class RespostaAgente:
    resposta: str
    citacoes: list[int]
    passos: list[Passo]
    citacoes_rejeitadas: list[int] = field(default_factory=list)
    chamadas: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0

    @property
    def custo_estimado_usd(self) -> float:
        return (self.tokens_entrada * config.PRECO_ENTRADA_1M
                + self.tokens_saida * config.PRECO_SAIDA_1M) / 1_000_000


def criar_indice(df: pd.DataFrame, cliente) -> IndiceBusca:
    ok = df[df["status"] == "ok"]
    col = "texto_enviado" if "texto_enviado" in ok else "texto"
    return IndiceBusca(ok["id"].tolist(), ok[col].astype(str).tolist(), cliente)


def perguntar(pergunta: str, df: pd.DataFrame, cliente, indice: IndiceBusca,
              historico: list[dict] | None = None, max_passos: int | None = None,
              ao_passo=None) -> RespostaAgente:
    """Conduz a investigação e devolve a resposta validada.

    historico: [{"pergunta", "resposta"}] da conversa (só as últimas entram no prompt).
    ao_passo: função opcional f(Passo) chamada a cada passo (para mostrar progresso).
    """
    max_passos = max_passos or config.AGENTE_MAX_PASSOS
    ferramentas = Ferramentas(df, indice)
    visao = ferramentas.visao_geral()
    historico = (historico or [])[-3:]
    passos: list[Passo] = []
    saida = RespostaAgente(resposta="", citacoes=[], passos=passos)
    erro_anterior = None

    for numero in range(max_passos):
        restantes = max_passos - numero
        passos_prompt = [_passo_para_prompt(p) for p in passos]
        resposta = _chamar(cliente, montar_prompt_agente(pergunta, visao, passos_prompt, historico,
                                                         restantes, erro_anterior),
                           {"tipo": "agente", "pergunta": pergunta, "passos": passos_prompt,
                            "restantes": restantes})
        saida.chamadas += 1
        saida.tokens_entrada += resposta.tokens_entrada
        saida.tokens_saida += resposta.tokens_saida

        try:
            acao = _validar_acao(resposta.texto)
        except ErroFormato as erro:
            erro_anterior = str(erro)
            passos.append(Passo(pensamento="(resposta fora do formato)", erro=erro_anterior))
            continue
        erro_anterior = None

        if acao.acao == "ferramenta" and restantes > 1:
            passo = Passo(acao.pensamento, acao.ferramenta, acao.argumentos)
            passo.resultado = ferramentas.executar(acao.ferramenta, acao.argumentos)
            passos.append(passo)
            if ao_passo:
                ao_passo(passo)
            continue
        if acao.acao == "ferramenta":  # pediu ferramenta no último passo: não há mais tempo
            erro_anterior = "não há mais passos para ferramentas; responda com acao \"responder\""
            continue

        # Resposta final: só valem citações de avaliações que o LLM realmente recebeu
        rejeitadas = [i for i in acao.citacoes if i not in ferramentas.ids_vistos]
        if rejeitadas and restantes > 1:
            erro_anterior = (f"as citações {rejeitadas} não apareceram em nenhum resultado de ferramenta. "
                             "Cite apenas ids recebidos ou busque as avaliações antes.")
            passos.append(Passo(pensamento=acao.pensamento, erro=erro_anterior))
            continue
        saida.resposta = acao.resposta
        saida.citacoes = list(dict.fromkeys(i for i in acao.citacoes if i in ferramentas.ids_vistos))[:5]
        saida.citacoes_rejeitadas = rejeitadas
        passos.append(Passo(pensamento=acao.pensamento))
        return saida

    saida.resposta = ("Não consegui chegar a uma resposta confiável dentro do limite de passos. "
                      "Tente reformular a pergunta de forma mais específica.")
    return saida


def _validar_acao(texto: str) -> AcaoAgente:
    try:
        acao = AcaoAgente.model_validate(extrair_json(texto))
    except ValidationError as erro:
        raise ErroFormato(str(erro)) from erro
    if acao.acao == "ferramenta" and not acao.ferramenta:
        raise ErroFormato("acao 'ferramenta' sem o campo 'ferramenta'")
    if acao.acao == "responder" and not acao.resposta:
        raise ErroFormato("acao 'responder' sem o campo 'resposta'")
    return acao


def _passo_para_prompt(passo: Passo) -> dict:
    if passo.erro:
        return {"pensamento": passo.pensamento, "erro_de_validacao": passo.erro}
    return {"pensamento": passo.pensamento, "ferramenta": passo.ferramenta,
            "argumentos": passo.argumentos, "resultado": passo.resultado}


def _chamar(cliente, prompt: str, dados_simulacao: dict):
    """Chama o LLM repetindo em caso de erro temporário (rede, limite de uso)."""
    for tentativa in range(1, config.MAX_TENTATIVAS + 1):
        try:
            return cliente.gerar(SISTEMA_AGENTE, prompt, dados_simulacao=dados_simulacao)
        except Exception as erro:
            if "PerDay" in str(erro):  # cota diária esgotada: só volta no dia seguinte
                raise ErroAPI("A cota diária da API do Gemini acabou (no plano gratuito são poucas "
                              "chamadas por dia, e cada pergunta usa de 3 a 5). Tente amanhã, use o "
                              "provedor 'simulado' ou ative o plano pago.") from erro
            if getattr(erro, "code", None) in (400, 401, 403, 404) or tentativa == config.MAX_TENTATIVAS:
                raise ErroAPI(f"Erro da API: {erro}") from erro
            if "429" in str(erro) or "RESOURCE_EXHAUSTED" in str(erro):
                espera = 30
            elif "503" in str(erro) or "UNAVAILABLE" in str(erro):  # sobrecarga: costuma levar mais
                espera = 15 * 2 ** (tentativa - 1)
            else:
                espera = 5 * tentativa
            time.sleep(espera)


def resumo_resultado(resultado: dict | None) -> str:
    """Versão curta do resultado de uma ferramenta, para mostrar na tela."""
    if not resultado:
        return ""
    if "erro" in resultado:
        return f"Erro: {resultado['erro']}"
    if "avaliacoes" in resultado:
        return f"{resultado['encontradas']} avaliações encontradas (de {resultado['total_no_filtro']} no filtro)"
    if "grupos" in resultado:
        return f"{resultado['total']} avaliações: " + ", ".join(f"{k} {v}" for k, v in list(resultado["grupos"].items())[:8])
    if "ranking" in resultado:
        return "Ranking: " + ", ".join(f"{r['tema']} ({r['impacto']})" for r in resultado["ranking"])
    return json.dumps(resultado, ensure_ascii=False)[:300]
