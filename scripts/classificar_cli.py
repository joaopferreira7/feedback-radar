"""Classifica um CSV pela linha de comando (sem abrir o dashboard).

Exemplos:
  python scripts/classificar_cli.py data/exemplos/avaliacoes_exemplo.csv
  python scripts/classificar_cli.py entrada.csv --saida saidas/classificado.csv --provedor simulado
  python scripts/classificar_cli.py entrada.csv --relatorio saidas/relatorio.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite importar feedback_radar

from feedback_radar import config  # noqa: E402
from feedback_radar.classificador import classificar_dataframe, estimar_custo  # noqa: E402
from feedback_radar.leitura_csv import ler_csv  # noqa: E402
from feedback_radar.llm import criar_cliente  # noqa: E402
from feedback_radar.relatorio import gerar_relatorio, markdown_para_pdf, relatorio_markdown  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Classifica avaliações com o Feedback Radar.")
    p.add_argument("entrada", help="CSV com a coluna 'texto'")
    p.add_argument("--saida", default="saidas/avaliacoes_classificadas.csv")
    p.add_argument("--provedor", default=config.PROVEDOR_LLM, choices=["gemini", "simulado"])
    p.add_argument("--lote", type=int, default=config.TAMANHO_LOTE)
    p.add_argument("--sem-anonimizar", action="store_true")
    p.add_argument("--relatorio", help="gera também o relatório (.md; cria um .pdf ao lado)")
    p.add_argument("--sim", action="store_true", help="não pedir confirmação do custo")
    args = p.parse_args()

    df, avisos = ler_csv(args.entrada)
    for aviso in avisos:
        print("AVISO:", aviso)
    if len(df) > config.MAX_AVALIACOES:
        print(f"AVISO: usando só as primeiras {config.MAX_AVALIACOES} avaliações.")
        df = df.head(config.MAX_AVALIACOES)

    est = estimar_custo(df["texto"].tolist(), args.lote)
    print(f"{len(df)} avaliações · {est['lotes']} chamadas · ~{est['tokens_entrada'] + est['tokens_saida']} "
          f"tokens · custo se pago ~US$ {est['custo_usd']:.4f}")
    if args.provedor == "gemini" and not args.sim and input("Continuar? [s/N] ").lower() != "s":
        return

    cliente = criar_cliente(args.provedor)
    resultado, stats = classificar_dataframe(
        df, cliente, args.lote, anonimizar_textos=not args.sem_anonimizar,
        ao_progredir=lambda f: print(f"\r{f:.0%}", end="", flush=True))
    print()

    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(args.saida, index=False, encoding="utf-8-sig")
    falhas = (resultado["status"] == "erro").sum()
    print(f"Salvo em {args.saida} · {len(resultado) - falhas} ok, {falhas} com erro · "
          f"{stats.chamadas} chamadas, {stats.retries} retries · US$ {stats.custo_estimado_usd:.4f}")
    for erro in stats.erros:
        print("  -", erro)

    if args.relatorio:
        relatorio, dados = gerar_relatorio(resultado, cliente)
        md = relatorio_markdown(relatorio, dados, resultado, cliente.nome)
        caminho = Path(args.relatorio)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(md, encoding="utf-8")
        caminho.with_suffix(".pdf").write_bytes(markdown_para_pdf(md))
        print(f"Relatório salvo em {caminho} e {caminho.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
