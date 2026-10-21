"""Calcula as métricas IA × gabarito humano e salva a análise de erros.

Exemplo:
  python scripts/avaliar_validacao.py --gabarito data/rotulagem/gabarito.xlsx \
      --ia saidas/amostra_classificada.csv
  # concordância entre dois rotuladores (antes do consenso):
  python scripts/avaliar_validacao.py --gabarito data/rotulagem/rotulador_A.xlsx \
      --rotulador-b data/rotulagem/rotulador_B.xlsx
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from feedback_radar.validacao import (calcular_metricas, carregar_gabarito,  # noqa: E402
                                      concordancia_entre_humanos, tabela_de_erros)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gabarito", required=True, help="planilha rotulada (.xlsx ou .csv)")
    p.add_argument("--ia", help="CSV classificado pelo Feedback Radar")
    p.add_argument("--rotulador-b", help="segunda planilha, para medir concordância entre humanos")
    p.add_argument("--saida", default="saidas/validacao")
    args = p.parse_args()

    gabarito = carregar_gabarito(args.gabarito)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    if args.rotulador_b:
        h = concordancia_entre_humanos(gabarito, carregar_gabarito(args.rotulador_b))
        print(f"Humanos: {h['n']} avaliações · concordância {h['concordancia']:.1%} · Kappa {h['kappa']:.2f}")
        h["divergencias"].to_csv(saida / "divergencias_humanos.csv", index=False, encoding="utf-8-sig")
        print(f"Divergências para discutir em reunião: {saida / 'divergencias_humanos.csv'}")

    if args.ia:
        m = calcular_metricas(gabarito, pd.read_csv(args.ia, encoding="utf-8-sig"))
        print(f"\nIA × gabarito ({m['n']} avaliações)")
        print(f"  Acurácia: {m['acuracia']:.1%} · F1 macro: {m['f1_macro']:.2f} · Kappa: {m['kappa']:.2f}")
        print("\nPor classe:\n", m["por_classe"].round(2).to_string(index=False))
        print("\nMatriz de confusão:\n", m["matriz_confusao"].to_string())
        print(f"\nTemas · Jaccard médio: {m['jaccard_medio']:.2f} · acerto exato: {m['acerto_exato_temas']:.1%}")
        print(m["temas"].round(2).to_string(index=False))

        erros = tabela_de_erros(m)
        erros["hipotese_do_grupo"] = ""  # coluna para o grupo preencher na análise qualitativa
        erros.to_csv(saida / "analise_de_erros.csv", index=False, encoding="utf-8-sig")
        m["por_classe"].to_csv(saida / "metricas_por_classe.csv", index=False, encoding="utf-8-sig")
        m["temas"].to_csv(saida / "metricas_temas.csv", index=False, encoding="utf-8-sig")
        m["matriz_confusao"].to_csv(saida / "matriz_confusao.csv", encoding="utf-8-sig")
        print(f"\n{len(erros)} casos de erro salvos em {saida / 'analise_de_erros.csv'}")


if __name__ == "__main__":
    main()
