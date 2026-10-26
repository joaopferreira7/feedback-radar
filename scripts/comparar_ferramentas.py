"""Compara ferramentas de IA (ChatGPT, Claude, Gemini web etc.) na mesma tarefa.

Passo 1, preparar: gera um prompt único com N avaliações da amostra de validação,
para colar em cada ferramenta.

  python scripts/comparar_ferramentas.py preparar --amostra data/rotulagem/amostra_validacao.csv --n 20

Passo 2: cole o prompt em cada ferramenta e salve a resposta inteira, sem editar,
em data/exploracao/respostas/<ferramenta>.txt (ex.: chatgpt.txt, claude.txt, gemini_web.txt).

Passo 3, comparar: valida o formato de cada resposta e mede o acerto contra o gabarito.

  python scripts/comparar_ferramentas.py comparar --gabarito data/rotulagem/gabarito.xlsx
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from feedback_radar.classificador import ErroFormato, extrair_json  # noqa: E402
from feedback_radar.esquemas import Classificacao  # noqa: E402
from feedback_radar.leitura_csv import ler_csv  # noqa: E402
from feedback_radar.prompts import SISTEMA_CLASSIFICACAO, montar_prompt_classificacao  # noqa: E402
from feedback_radar.validacao import calcular_metricas, carregar_gabarito  # noqa: E402

PASTA = Path("data/exploracao")


def preparar(args):
    df, _ = ler_csv(args.amostra)
    amostra = df.sort_values("id").head(args.n)
    itens = [{"id": int(i), "texto": t} for i, t in zip(amostra["id"], amostra["texto"])]
    # Ferramentas web não têm "prompt de sistema" separado: juntamos tudo num texto só
    prompt = SISTEMA_CLASSIFICACAO + "\n\n---\n\n" + montar_prompt_classificacao(itens)
    (PASTA / "respostas").mkdir(parents=True, exist_ok=True)
    destino = PASTA / "prompt_para_colar.txt"
    destino.write_text(prompt, encoding="utf-8")
    print(f"Prompt com {len(itens)} avaliações salvo em {destino}.")
    print(f"Salve cada resposta em {PASTA / 'respostas'}/<ferramenta>.txt")


def _ler_resposta(caminho: Path) -> tuple[pd.DataFrame, str]:
    """Converte a resposta de uma ferramenta no formato do CSV classificado.

    Valida item por item: uma avaliação com tema inventado não invalida as outras.
    Retorna (DataFrame, observação sobre o formato).
    """
    texto = caminho.read_text(encoding="utf-8")
    try:
        dados = extrair_json(texto)
    except ErroFormato as erro:
        return pd.DataFrame(columns=["id", "status", "sentimento", "temas"]), f"JSON ilegível ({erro})"

    linhas, invalidos = [], 0
    for item in dados.get("classificacoes", []):
        try:
            c = Classificacao.model_validate(item)
            linhas.append({"id": c.id, "status": "ok", "sentimento": c.sentimento, "temas": ";".join(c.temas)})
        except ValidationError:
            invalidos += 1
    fora_do_json = texto.strip()[:1] != "{" and not texto.strip().startswith("```")
    obs = []
    if fora_do_json:
        obs.append("texto extra além do JSON")
    if invalidos:
        obs.append(f"{invalidos} item(ns) fora do esquema")
    return pd.DataFrame(linhas), "; ".join(obs) or "formato correto"


def comparar(args):
    gabarito = carregar_gabarito(args.gabarito)
    arquivos = sorted((PASTA / "respostas").glob("*.txt"))
    if not arquivos:
        sys.exit(f"Nenhuma resposta encontrada em {PASTA / 'respostas'}.")

    linhas = []
    for caminho in arquivos:
        respostas, obs = _ler_resposta(caminho)
        if respostas.empty:
            linhas.append({"ferramenta": caminho.stem, "avaliacoes_validas": 0, "formato": obs})
            continue
        ids = set(respostas["id"])
        m = calcular_metricas(gabarito[gabarito["id"].isin(ids)], respostas)
        linhas.append({
            "ferramenta": caminho.stem,
            "avaliacoes_validas": m["n"],
            "acuracia_sentimento": round(m["acuracia"], 3),
            "f1_macro": round(m["f1_macro"], 3),
            "kappa": round(m["kappa"], 3),
            "jaccard_temas": round(m["jaccard_medio"], 3),
            "formato": obs,
        })

    tabela = pd.DataFrame(linhas)
    print(tabela.to_string(index=False))
    saida = Path("saidas/exploracao_ferramentas.csv")
    saida.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\nTabela salva em {saida}. Complete as colunas qualitativas em docs/exploracao-ferramentas.md.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    pp = sub.add_parser("preparar")
    pp.add_argument("--amostra", default="data/rotulagem/amostra_validacao.csv")
    pp.add_argument("--n", type=int, default=20)
    pc = sub.add_parser("comparar")
    pc.add_argument("--gabarito", required=True)
    args = p.parse_args()
    preparar(args) if args.comando == "preparar" else comparar(args)


if __name__ == "__main__":
    main()
