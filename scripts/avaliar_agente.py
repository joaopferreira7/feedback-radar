"""Roda um conjunto fixo de perguntas no agente analista e gera uma planilha para avaliação.

Mede automaticamente: se o agente respondeu, quantos passos usou, quais ferramentas,
citações válidas e rejeitadas, tokens e custo. A qualidade da resposta é avaliada pelo
grupo, preenchendo as colunas "correta" e "util" na planilha gerada.

Exemplos:
  python scripts/avaliar_agente.py data/exemplos/avaliacoes_exemplo.csv --provedor simulado
  python scripts/avaliar_agente.py saidas/avaliacoes_classificadas.csv --provedor gemini --perguntas 3
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite importar feedback_radar

from feedback_radar.agente import criar_indice, perguntar  # noqa: E402
from feedback_radar.classificador import ErroAPI, classificar_dataframe  # noqa: E402
from feedback_radar.leitura_csv import ler_csv  # noqa: E402
from feedback_radar.llm import criar_cliente  # noqa: E402

# Cada pergunta exercita um tipo de investigação diferente
PERGUNTAS = [
    "O que mais irrita os clientes?",
    "O que os clientes mais elogiam?",
    "Os problemas de entrega pioraram ao longo dos meses?",
    "Compare janeiro com março: o que mudou?",
    "O que eu devo melhorar primeiro?",
    "Os clientes do iFood estão mais insatisfeitos que os do Google?",
    "O que dizem sobre o banheiro?",
    "Qual a opinião dos clientes sobre o estacionamento com manobrista?",  # assunto que não aparece
]


def main():
    sys.stdout.reconfigure(line_buffering=True)
    p = argparse.ArgumentParser(description="Avalia o agente analista com perguntas fixas.")
    p.add_argument("entrada", help="CSV de avaliações (classificado ou não)")
    p.add_argument("--provedor", default="simulado", choices=["gemini", "simulado"])
    p.add_argument("--perguntas", type=int, default=len(PERGUNTAS), help="quantas perguntas rodar")
    p.add_argument("--saida", default="saidas/avaliacao_agente.csv")
    args = p.parse_args()

    cliente = criar_cliente(args.provedor)
    df, _ = ler_csv(args.entrada)
    if not {"sentimento", "temas", "status"}.issubset(df.columns):
        print("Classificando as avaliações primeiro...")
        df, _ = classificar_dataframe(df, cliente)
    else:
        df["intensidade"] = pd.to_numeric(df["intensidade"], errors="coerce")
    indice = criar_indice(df, cliente)
    print(f"Busca: {indice.metodo}" + (f" ({indice.aviso})" if indice.aviso else ""))

    linhas = []
    for pergunta in PERGUNTAS[:args.perguntas]:
        print(f"\n> {pergunta}")
        try:
            r = perguntar(pergunta, df, cliente, indice)
        except ErroAPI as erro:
            print(f"  Interrompido: {erro}")
            break
        ferramentas = [p.ferramenta for p in r.passos if p.ferramenta]
        erros = sum(1 for p in r.passos if p.erro or (p.resultado and "erro" in p.resultado))
        print(f"  ferramentas: {' -> '.join(ferramentas) or 'nenhuma'} | citações: {r.citacoes} | "
              f"rejeitadas: {r.citacoes_rejeitadas} | {r.tokens_entrada + r.tokens_saida} tokens")
        print(f"  {r.resposta}")
        linhas.append({
            "pergunta": pergunta, "resposta": r.resposta,
            "respondeu": not r.resposta.startswith("Não consegui chegar"),
            "chamadas": r.chamadas, "ferramentas": " -> ".join(ferramentas), "erros_corrigidos": erros,
            "citacoes": len(r.citacoes), "citacoes_rejeitadas": len(r.citacoes_rejeitadas),
            "tokens": r.tokens_entrada + r.tokens_saida, "custo_usd": round(r.custo_estimado_usd, 5),
            "correta": "", "util": "",  # preenchidas pelo grupo (sim/parcial/não)
        })

    if not linhas:
        return
    resultado = pd.DataFrame(linhas)
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(args.saida, index=False, encoding="utf-8-sig")
    print(f"\nRespondidas: {resultado['respondeu'].mean():.0%} · média de {resultado['chamadas'].mean():.1f} "
          f"chamadas · {resultado['citacoes_rejeitadas'].sum()} citações rejeitadas · "
          f"custo total US$ {resultado['custo_usd'].sum():.4f}")
    print(f"Planilha salva em {args.saida}: preencha as colunas 'correta' e 'util'.")


if __name__ == "__main__":
    main()
