"""Comparação entre modelos de IA na mesma tarefa de classificação.

Responde "os modelos chegam ao mesmo resultado?" sem precisar de gabarito:
- concordância de sentimento entre cada par de modelos (% de avaliações com o mesmo rótulo);
- concordância de temas (Jaccard médio);
- avaliações em que os modelos discordam, que costumam ser as ambíguas.

Concordar não é acertar: vários modelos podem errar do mesmo jeito (ironia, por exemplo).
Para medir acerto é preciso o gabarito humano; com ele, acuracia_por_modelo() dá a nota de cada um.
"""
import pandas as pd

from .classificador import classificar_dataframe, lista_temas
from .validacao import calcular_metricas


def classificar_com_modelos(df: pd.DataFrame, clientes: dict, tamanho_lote: int,
                            ao_progredir=None) -> tuple[dict, dict]:
    """Classifica as mesmas avaliações com cada cliente. clientes: {nome: cliente}.

    Retorna ({nome: DataFrame classificado}, {nome: Estatisticas}).
    ao_progredir(nome, fracao) é chamado durante cada modelo.
    """
    resultados, estatisticas = {}, {}
    for nome, cliente in clientes.items():
        progresso = (lambda f, n=nome: ao_progredir(n, f)) if ao_progredir else None
        resultados[nome], estatisticas[nome] = classificar_dataframe(
            df[["id", "texto"]], cliente, tamanho_lote, ao_progredir=progresso)
    return resultados, estatisticas


def _jaccard(a: str, b: str) -> float:
    x, y = set(lista_temas(a)), set(lista_temas(b))
    return len(x & y) / len(x | y) if (x | y) else 1.0


def concordancia(resultados: dict) -> dict:
    """resultados: {nome: DataFrame com id, texto, sentimento, temas, status}."""
    ok = {n: d[d["status"] == "ok"].set_index("id") for n, d in resultados.items()}
    nomes = list(ok)
    sentimento = pd.DataFrame(index=nomes, columns=nomes, dtype=float)
    temas = pd.DataFrame(index=nomes, columns=nomes, dtype=float)
    for a in nomes:
        for b in nomes:
            comuns = ok[a].index.intersection(ok[b].index)
            if len(comuns) == 0:
                continue
            sentimento.loc[a, b] = (ok[a].loc[comuns, "sentimento"] == ok[b].loc[comuns, "sentimento"]).mean()
            temas.loc[a, b] = sum(_jaccard(ok[a].loc[i, "temas"], ok[b].loc[i, "temas"])
                                  for i in comuns) / len(comuns)

    # Uma linha por avaliação, uma coluna por modelo
    tabela = pd.DataFrame({n: d["sentimento"] for n, d in ok.items()}).dropna()
    textos = next(iter(resultados.values())).set_index("id")["texto"]
    divergentes = tabela[tabela.nunique(axis=1) > 1].copy()
    divergentes.insert(0, "texto", textos.reindex(divergentes.index))
    divergentes = divergentes.reset_index().rename(columns={"index": "id"})

    return {
        "sentimento": sentimento,
        "temas": temas,
        "divergentes": divergentes,
        "comparadas": len(tabela),
        "todas_iguais": int((tabela.nunique(axis=1) == 1).sum()),
    }


def acuracia_por_modelo(resultados: dict, gabarito: pd.DataFrame) -> pd.DataFrame:
    """Com o gabarito humano: acurácia, F1, Kappa e Jaccard de temas de cada modelo."""
    linhas = []
    for nome, df in resultados.items():
        m = calcular_metricas(gabarito, df)
        negativo = m["por_classe"].set_index("classe").loc["negativo"]
        linhas.append({"modelo": nome, "avaliacoes": m["n"], "acuracia": m["acuracia"],
                       "f1_macro": m["f1_macro"], "kappa": m["kappa"],
                       "recall_negativo": negativo["recall"], "jaccard_temas": m["jaccard_medio"]})
    return pd.DataFrame(linhas).sort_values("acuracia", ascending=False).reset_index(drop=True)
