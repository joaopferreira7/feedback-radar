"""Gráficos do dashboard (Plotly). Cores fixas por sentimento em todos os gráficos."""
import pandas as pd
import plotly.express as px

from .classificador import lista_temas
from .taxonomia import NOMES_TEMAS, SENTIMENTOS

# Mesma paleta do tema em .streamlit/config.toml
CORES = {"positivo": "#4f7a5a", "neutro": "#b9b1a4", "negativo": "#b0493b"}


def grafico_sentimento(df: pd.DataFrame):
    contagem = df["sentimento"].value_counts().reindex(SENTIMENTOS, fill_value=0).reset_index()
    contagem.columns = ["sentimento", "avaliacoes"]
    fig = px.bar(contagem, x="sentimento", y="avaliacoes", color="sentimento", text="avaliacoes",
                 color_discrete_map=CORES, title="Distribuição de sentimento")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Avaliações")
    return fig


def grafico_temas(df: pd.DataFrame):
    explodido = df.assign(tema=df["temas"].map(lista_temas)).explode("tema").dropna(subset=["tema"])
    explodido["tema"] = explodido["tema"].map(NOMES_TEMAS)
    contagem = explodido.groupby(["tema", "sentimento"]).size().reset_index(name="mencoes")
    ordem = contagem.groupby("tema")["mencoes"].sum().sort_values().index.tolist()
    fig = px.bar(contagem, y="tema", x="mencoes", color="sentimento", orientation="h",
                 color_discrete_map=CORES, category_orders={"tema": ordem, "sentimento": SENTIMENTOS},
                 title="Temas mais citados, por sentimento")
    fig.update_layout(yaxis_title="", xaxis_title="Menções", legend_title="")
    return fig


def grafico_evolucao(df: pd.DataFrame):
    """Avaliações por mês e sentimento (só se houver coluna de data)."""
    com_data = df.dropna(subset=["data"]).copy()
    com_data["mes"] = pd.to_datetime(com_data["data"]).dt.to_period("M").dt.to_timestamp()
    serie = com_data.groupby(["mes", "sentimento"]).size().reset_index(name="avaliacoes")
    fig = px.line(serie, x="mes", y="avaliacoes", color="sentimento", markers=True,
                  color_discrete_map=CORES, category_orders={"sentimento": SENTIMENTOS},
                  title="Evolução mensal das avaliações")
    fig.update_layout(xaxis_title="", yaxis_title="Avaliações", legend_title="")
    return fig


def grafico_matriz_confusao(matriz: pd.DataFrame):
    fig = px.imshow(matriz, text_auto=True, color_continuous_scale=["#f4f1ea", "#2f4858"],
                    title="Matriz de confusão do sentimento (linhas = humano, colunas = IA)")
    fig.update_layout(coloraxis_showscale=False)
    return fig
