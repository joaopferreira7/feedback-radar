"""Relatório de prioridades de melhoria.

Divisão de responsabilidades (para reduzir alucinação):
- O CÓDIGO calcula o ranking (frequência × negatividade) e escolhe os exemplos reais.
- O LLM só escreve diagnóstico e ações, citando ids dos exemplos recebidos.
- O CÓDIGO valida os ids citados e coloca no relatório o texto ORIGINAL das
  avaliações — o LLM nunca "cita" um cliente com as próprias palavras.
"""
import time
from datetime import datetime

import pandas as pd
from pydantic import ValidationError

from . import config
from .classificador import ErroFormato, extrair_json, lista_temas
from .esquemas import RespostaRelatorio
from .prompts import SISTEMA_RELATORIO, montar_prompt_relatorio
from .taxonomia import NOMES_TEMAS


def calcular_impacto(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por tema com frequência, negatividade e impacto.

    frequencia    = menções do tema / total de avaliações
    negatividade  = % de menções negativas, ponderada pela intensidade média (÷5)
    impacto       = frequencia × negatividade  (0 a 1; maior = mais urgente)
    """
    ok = df[df["status"] == "ok"]
    total = len(ok)
    linhas = []
    explodido = ok.assign(tema=ok["temas"].map(lista_temas)).explode("tema")
    for tema, grupo in explodido.groupby("tema"):
        negativas = grupo[grupo["sentimento"] == "negativo"]
        taxa_neg = len(negativas) / len(grupo)
        intensidade_neg = negativas["intensidade"].mean() if len(negativas) else 0
        frequencia = len(grupo) / total if total else 0
        linhas.append({
            "tema": tema,
            "nome": NOMES_TEMAS.get(tema, tema),
            "mencoes": len(grupo),
            "positivas": int((grupo["sentimento"] == "positivo").sum()),
            "neutras": int((grupo["sentimento"] == "neutro").sum()),
            "negativas": len(negativas),
            "frequencia": frequencia,
            "pct_negativas": 100 * taxa_neg,
            "intensidade_media_neg": intensidade_neg,
            "impacto": frequencia * taxa_neg * (intensidade_neg / 5),
        })
    if not linhas:
        return pd.DataFrame(columns=["tema", "nome", "mencoes", "negativas", "impacto"])
    return pd.DataFrame(linhas).sort_values("impacto", ascending=False).reset_index(drop=True)


def _exemplos(df: pd.DataFrame, tema: str, sentimento: str, n: int = 3) -> list[dict]:
    """Escolhe as avaliações mais intensas daquele tema/sentimento."""
    filtro = (df["status"] == "ok") & (df["sentimento"] == sentimento) & \
             df["temas"].map(lambda v: tema in lista_temas(v))
    escolhidas = df[filtro].sort_values("intensidade", ascending=False).head(n)
    return [{"id": int(r.id), "texto": r.texto_enviado if "texto_enviado" in df else r.texto}
            for r in escolhidas.itertuples()]


def montar_dados_relatorio(df: pd.DataFrame, max_temas: int = 5) -> dict:
    impacto = calcular_impacto(df)
    ranking = impacto[(impacto["negativas"] > 0)].head(max_temas)
    ok = df[df["status"] == "ok"]
    return {
        "total_avaliacoes": int(len(ok)),
        "pct_negativas_geral": round(100 * (ok["sentimento"] == "negativo").mean(), 1) if len(ok) else 0,
        "ranking": [
            {"posicao": i + 1, "tema": r.tema, "mencoes": int(r.mencoes), "negativas": int(r.negativas),
             "pct_negativas": round(r.pct_negativas, 1), "impacto": round(r.impacto, 3)}
            for i, r in enumerate(ranking.itertuples())
        ],
        "exemplos_negativos": {r.tema: _exemplos(df, r.tema, "negativo") for r in ranking.itertuples()},
        "exemplos_positivos": _exemplos_positivos_gerais(df),
    }


def _exemplos_positivos_gerais(df: pd.DataFrame, n: int = 5) -> list[dict]:
    pos = df[(df["status"] == "ok") & (df["sentimento"] == "positivo")]
    pos = pos.sort_values("intensidade", ascending=False).head(n)
    col = "texto_enviado" if "texto_enviado" in df else "texto"
    return [{"id": int(r["id"]), "texto": r[col]} for _, r in pos.iterrows()]


def gerar_relatorio(df: pd.DataFrame, cliente) -> tuple[RespostaRelatorio, dict]:
    """Chama o LLM com retry e valida se os ids citados existem nos exemplos."""
    dados = montar_dados_relatorio(df)
    if not dados["ranking"]:
        raise ValueError("Não há avaliações negativas suficientes para gerar prioridades.")

    ids_validos = {e["id"] for lista in dados["exemplos_negativos"].values() for e in lista}
    temas_ranking = [r["tema"] for r in dados["ranking"]]
    erro_anterior = None
    for tentativa in range(1, config.MAX_TENTATIVAS + 1):
        try:
            resposta = cliente.gerar(SISTEMA_RELATORIO, montar_prompt_relatorio(dados, erro_anterior),
                                     dados_simulacao=dados)
            relatorio = RespostaRelatorio.model_validate(extrair_json(resposta.texto))
            inventados = {i for p in relatorio.prioridades for i in p.ids_exemplos} - ids_validos
            if inventados:
                raise ErroFormato(f"ids citados que não existem nos exemplos: {sorted(inventados)}")
            fora = [p.tema for p in relatorio.prioridades if p.tema not in temas_ranking]
            if fora:
                raise ErroFormato(f"temas fora do ranking: {fora}")
            return relatorio, dados
        except (ErroFormato, ValidationError) as erro:
            erro_anterior = str(erro)
        except Exception:
            time.sleep(5 * 2 ** (tentativa - 1))
    raise RuntimeError(f"Não foi possível gerar o relatório após {config.MAX_TENTATIVAS} tentativas. "
                       f"Último erro: {erro_anterior}")


def relatorio_markdown(relatorio: RespostaRelatorio, dados: dict, df: pd.DataFrame,
                       nome_modelo: str = "") -> str:
    """Monta o Markdown final com os textos ORIGINAIS das avaliações citadas."""
    col = "texto_enviado" if "texto_enviado" in df else "texto"
    textos = dict(zip(df["id"].astype(int), df[col]))
    impacto = {r["tema"]: r for r in dados["ranking"]}

    linhas = [
        "# Feedback Radar — Relatório de prioridades de melhoria",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · {dados['total_avaliacoes']} avaliações analisadas · "
        f"{dados['pct_negativas_geral']}% negativas" + (f" · modelo: {nome_modelo}" if nome_modelo else ""),
        "",
        "> Relatório gerado com apoio de IA. Revise antes de tomar decisões: o modelo pode errar "
        "a classificação, e os exemplos citados são avaliações reais (anonimizadas).",
        "",
        "## Resumo geral",
        "",
        relatorio.resumo_geral,
        "",
        "## Prioridades (ordenadas por impacto = frequência × negatividade)",
        "",
        "| # | Tema | Menções | Negativas | % negativas | Impacto |",
        "|---|------|---------|-----------|-------------|---------|",
    ]
    for r in dados["ranking"]:
        linhas.append(f"| {r['posicao']} | {NOMES_TEMAS.get(r['tema'], r['tema'])} | {r['mencoes']} | "
                      f"{r['negativas']} | {r['pct_negativas']}% | {r['impacto']} |")
    linhas.append("")

    for n, p in enumerate(relatorio.prioridades, start=1):
        r = impacto.get(p.tema, {})
        linhas += [f"### {n}. {NOMES_TEMAS.get(p.tema, p.tema)}",
                   "",
                   f"**Diagnóstico:** {p.diagnostico}",
                   "",
                   f"*{r.get('negativas', '?')} avaliações negativas de {r.get('mencoes', '?')} menções.*",
                   "",
                   "**Ações recomendadas:**",
                   ""]
        linhas += [f"{i}. {acao}" for i, acao in enumerate(p.acoes, start=1)]
        linhas += ["", "**Avaliações que sustentam a recomendação:**", ""]
        linhas += [f"> \"{textos.get(i, '?')}\" (avaliação #{i})" + "\n" for i in p.ids_exemplos]
        linhas.append("")

    if relatorio.pontos_fortes:
        linhas += ["## Pontos fortes (manter)", ""]
        linhas += [f"- {ponto}" for ponto in relatorio.pontos_fortes]
        linhas.append("")
    return "\n".join(linhas)


def markdown_para_pdf(markdown: str) -> bytes:
    """Converte o Markdown simples do relatório em PDF (fpdf2).

    A fonte padrão do PDF só tem caracteres latinos (acentos ok, emojis não),
    por isso trocamos caracteres especiais.
    """
    from fpdf import FPDF

    def limpar(texto: str) -> str:
        trocas = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "·": "-", "…": "..."}
        for antigo, novo in trocas.items():
            texto = texto.replace(antigo, novo)
        texto = texto.replace("**", "").replace("*", "")
        return texto.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    for linha in markdown.splitlines():
        texto = limpar(linha)
        if linha.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            texto = texto[2:]
        elif linha.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            texto = texto[3:]
        elif linha.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            texto = texto[4:]
        elif linha.startswith(">"):
            pdf.set_font("Helvetica", "I", 10)
            texto = texto.lstrip("> ")
        elif linha.startswith("|---"):
            continue
        else:
            pdf.set_font("Helvetica", "", 10)
        if not texto.strip():
            pdf.ln(3)
            continue
        if linha.startswith("|"):
            texto = "   ".join(c.strip() for c in texto.strip("|").split("|"))
        pdf.multi_cell(0, 5.5, texto, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
