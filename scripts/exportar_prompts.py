"""Gera docs/apendice-prompts.md com o texto exato dos prompts de sistema.

Assim o apêndice do relatório nunca fica diferente do que a aplicação envia ao modelo.

  python scripts/exportar_prompts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feedback_radar import prompts  # noqa: E402

CERCA = "````"  # quatro crases: os prompts têm exemplos com três

PROMPTS = [
    ("A.1 Classificação de avaliações", prompts.SISTEMA_CLASSIFICACAO),
    ("A.2 Relatório de prioridades", prompts.SISTEMA_RELATORIO),
    ("A.3 Agente analista", prompts.SISTEMA_AGENTE),
]


def main():
    linhas = [
        "# Apêndice A: prompts usados na aplicação",
        "",
        "Texto exato dos prompts de sistema enviados ao Gemini, gerado a partir de "
        "`feedback_radar/prompts.py` pelo script `scripts/exportar_prompts.py`. Os prompts do usuário "
        "(as avaliações, os dados do relatório e a pergunta do agente) são montados pelo código a cada "
        "chamada, nas funções `montar_prompt_*` do mesmo arquivo.",
        "",
    ]
    for titulo, texto in PROMPTS:
        linhas += [f"## {titulo}", "", f"{CERCA}text", texto, CERCA, ""]
    destino = Path(__file__).resolve().parents[1] / "docs" / "apendice-prompts.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Prompts exportados para {destino}")


if __name__ == "__main__":
    main()
