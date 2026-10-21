"""Comparação da classificação da IA com a rotulagem manual (gabarito do grupo).

Sentimento: acurácia, precisão/recall/F1 por classe, matriz de confusão e
Kappa de Cohen (concordância descontando o acaso).
Temas (multirrótulo): precisão/recall/F1 por tema, Jaccard médio e
"acerto exato" (conjunto de temas idêntico).
"""
import re

import pandas as pd
from sklearn.metrics import (accuracy_score, cohen_kappa_score, confusion_matrix,
                             precision_recall_fscore_support)

from .classificador import lista_temas
from .taxonomia import SENTIMENTOS, TEMAS_VALIDOS


def carregar_gabarito(arquivo) -> pd.DataFrame:
    """Lê a planilha de rotulagem (.xlsx ou .csv) no formato de gerar_planilha_rotulagem.py.

    Retorna colunas: id, texto, sentimento_humano, temas_humano ("a;b").
    """
    nome = getattr(arquivo, "name", str(arquivo))
    if nome.lower().endswith(".xlsx"):
        df = pd.read_excel(arquivo, sheet_name="rotulagem")
    else:
        df = pd.read_csv(arquivo, sep=None, engine="python", encoding="utf-8-sig")

    df = df.dropna(subset=["sentimento"])
    df = df[df["sentimento"].astype(str).str.strip() != ""]
    df["sentimento_humano"] = df["sentimento"].astype(str).str.strip().str.lower()
    invalidos = set(df["sentimento_humano"]) - set(SENTIMENTOS)
    if invalidos:
        raise ValueError(f"Sentimentos inválidos na planilha: {invalidos}")

    def temas_da_linha(linha) -> str:
        marcados = [t for t in TEMAS_VALIDOS
                    if str(linha.get(f"tema_{t}", "")).strip().lower() in ("x", "1", "sim", "s", "1.0")]
        return ";".join(marcados or ["outros"])

    df["temas_humano"] = df.apply(temas_da_linha, axis=1)
    df["id"] = df["id"].astype(int)
    return df[["id", "texto", "sentimento_humano", "temas_humano"]]


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0


def calcular_metricas(gabarito: pd.DataFrame, classificado: pd.DataFrame) -> dict:
    """gabarito: saída de carregar_gabarito; classificado: CSV gerado pelo pipeline."""
    ia = classificado[classificado["status"] == "ok"][["id", "sentimento", "temas"]]
    ia = ia.rename(columns={"sentimento": "sentimento_ia", "temas": "temas_ia"})
    juntos = gabarito.merge(ia, on="id", how="inner")
    if juntos.empty:
        raise ValueError("Nenhum id em comum entre o gabarito e o arquivo classificado.")

    y_h, y_ia = juntos["sentimento_humano"], juntos["sentimento_ia"]
    p, r, f1, suporte = precision_recall_fscore_support(y_h, y_ia, labels=SENTIMENTOS, zero_division=0)
    por_classe = pd.DataFrame({"classe": SENTIMENTOS, "precisao": p, "recall": r, "f1": f1,
                               "suporte": suporte})
    matriz = pd.DataFrame(confusion_matrix(y_h, y_ia, labels=SENTIMENTOS),
                          index=[f"humano: {s}" for s in SENTIMENTOS],
                          columns=[f"IA: {s}" for s in SENTIMENTOS])

    # Temas
    conj_h = juntos["temas_humano"].map(lambda v: set(lista_temas(v)))
    conj_ia = juntos["temas_ia"].map(lambda v: set(lista_temas(v)))
    juntos["jaccard_temas"] = [_jaccard(a, b) for a, b in zip(conj_h, conj_ia)]
    linhas_temas = []
    for tema in TEMAS_VALIDOS:
        h = conj_h.map(lambda s: tema in s)
        i = conj_ia.map(lambda s: tema in s)
        vp, fp, fn = (h & i).sum(), (~h & i).sum(), (h & ~i).sum()
        prec = vp / (vp + fp) if (vp + fp) else 0.0
        rec = vp / (vp + fn) if (vp + fn) else 0.0
        linhas_temas.append({"tema": tema, "precisao": prec, "recall": rec,
                             "f1": 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0,
                             "suporte_humano": int(h.sum()), "marcado_pela_ia": int(i.sum())})

    juntos["acertou_sentimento"] = y_h == y_ia
    return {
        "n": len(juntos),
        "acuracia": accuracy_score(y_h, y_ia),
        "kappa": cohen_kappa_score(y_h, y_ia, labels=SENTIMENTOS),
        "f1_macro": float(f1.mean()),
        "por_classe": por_classe,
        "matriz_confusao": matriz,
        "temas": pd.DataFrame(linhas_temas),
        "jaccard_medio": juntos["jaccard_temas"].mean(),
        "acerto_exato_temas": (conj_h == conj_ia).mean(),
        "comparacao": juntos,
    }


def concordancia_entre_humanos(rotulador_a: pd.DataFrame, rotulador_b: pd.DataFrame) -> dict:
    """Kappa entre dois rotuladores humanos: mostra o 'teto' realista para a IA."""
    juntos = rotulador_a.merge(rotulador_b, on="id", suffixes=("_a", "_b"))
    return {
        "n": len(juntos),
        "concordancia": (juntos["sentimento_humano_a"] == juntos["sentimento_humano_b"]).mean(),
        "kappa": cohen_kappa_score(juntos["sentimento_humano_a"], juntos["sentimento_humano_b"]),
        "divergencias": juntos[juntos["sentimento_humano_a"] != juntos["sentimento_humano_b"]],
    }


# ---------- Análise de erros ----------

_IRONIA = re.compile(r"só que não|parab[eé]ns|que maravilha|ótimo,|otimo,|adorei esperar|"
                     r"show de bola|nossa,|uau|obrigad[oa] por nada|\"\w+\"", re.IGNORECASE)
_GIRIAS = re.compile(r"\b(mó|mo|top|brabo|braba|zica|zuado|zoado|paia|rlx|dms|mt|vlw|tmj|"
                     r"kkk+|rs|pqp|lixo|sinistr[oa]|da hora|monstro|brisa|tankar)\b", re.IGNORECASE)
_MISTA = re.compile(r"\b(mas|porém|porem|entretanto|só que|apesar)\b", re.IGNORECASE)


def hipoteses_de_erro(texto: str) -> str:
    """Pistas AUTOMÁTICAS do motivo do erro. São hipóteses: o grupo deve revisar."""
    pistas = []
    if _IRONIA.search(texto):
        pistas.append("possível ironia/sarcasmo")
    if _GIRIAS.search(texto):
        pistas.append("gíria/abreviação")
    if _MISTA.search(texto):
        pistas.append("avaliação mista (elogio + crítica)")
    if len(texto.split()) <= 4:
        pistas.append("texto muito curto/pouco contexto")
    if re.search(r"[\U0001F300-\U0001FAFF]", texto):
        pistas.append("emoji carrega o sentido")
    return "; ".join(pistas) or "ambígua ou outro motivo (analisar manualmente)"


def tabela_de_erros(metricas: dict) -> pd.DataFrame:
    comp = metricas["comparacao"]
    erros = comp[(~comp["acertou_sentimento"]) | (comp["jaccard_temas"] < 0.5)].copy()
    erros["tipo_erro"] = erros.apply(
        lambda r: "sentimento" + (" + temas" if r["jaccard_temas"] < 0.5 else "")
        if not r["acertou_sentimento"] else "temas", axis=1)
    erros["hipotese_automatica"] = erros["texto"].map(hipoteses_de_erro)
    return erros[["id", "texto", "sentimento_humano", "sentimento_ia", "temas_humano", "temas_ia",
                  "tipo_erro", "hipotese_automatica"]]
