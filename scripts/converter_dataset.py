"""Converte datasets públicos para o formato do Feedback Radar (texto, data, nota, fonte).

Suportados:
  olist -> olist_order_reviews_dataset.csv (Kaggle: "Brazilian E-Commerce Public Dataset by Olist")
  b2w   -> B2W-Reviews01.csv (github.com/americanas-tech/b2w-reviews01)

Exemplo:
  python scripts/converter_dataset.py olist data/brutos/olist_order_reviews_dataset.csv \
      --saida data/olist_500.csv --amostra 500
"""
import argparse
from pathlib import Path

import pandas as pd

MAPAS = {
    "olist": {"texto": "review_comment_message", "data": "review_creation_date", "nota": "review_score"},
    "b2w": {"texto": "review_text", "data": "submission_date", "nota": "overall_rating"},
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dataset", choices=MAPAS)
    p.add_argument("arquivo")
    p.add_argument("--saida", required=True)
    p.add_argument("--amostra", type=int, default=500, help="quantas avaliações sortear")
    p.add_argument("--semente", type=int, default=42, help="semente fixa = amostra reprodutível")
    args = p.parse_args()

    mapa = MAPAS[args.dataset]
    df = pd.read_csv(args.arquivo, usecols=list(mapa.values()), low_memory=False)
    df = df.rename(columns={v: k for k, v in mapa.items()})
    df = df.dropna(subset=["texto"])
    df = df[df["texto"].str.strip().str.len() > 3]
    df["fonte"] = args.dataset
    df = df.sample(n=min(args.amostra, len(df)), random_state=args.semente)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%d/%m/%Y")

    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    df[["texto", "data", "nota", "fonte"]].to_csv(args.saida, index=False, encoding="utf-8-sig")
    print(f"{len(df)} avaliações salvas em {args.saida}")


if __name__ == "__main__":
    main()
