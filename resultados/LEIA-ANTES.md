# Resultados medidos

Não abra os arquivos desta pasta antes de terminar a rotulagem manual: eles mostram como as IAs classificaram a amostra, e vê-los antes puxa o julgamento humano (viés de ancoragem).

Todos foram gerados em 27/10/2026 sobre a amostra real de 100 avaliações do B2W-Reviews01 (`data/rotulagem/amostra_validacao.csv`; licença em `data/LICENCA-DADOS.md`).

- `amostra_classificada_flash_lite.csv`: classificação pela aplicação com o `gemini-3.5-flash-lite` (88 s, 10 chamadas). O `gemini-3.8-flash`, modelo principal, estava sobrecarregado e depois sem cota; falta rodá-lo e salvar como `saidas/amostra_classificada_flash.csv`.
- `amostra_classificada_regras.csv`: linha de base por palavras-chave (modo simulado, sem IA).
- `concordancia_sentimento.csv`, `concordancia_temas.csv`, `divergencias_ferramentas.csv`: concordância entre ChatGPT, Claude, Gemini web, a aplicação e a linha de base nas 20 primeiras avaliações (`scripts/comparar_ferramentas.py concordancia`).
- `avaliacao_agente_b2w.csv` e `.log`: as oito perguntas do agente analista. Preencham as colunas `correta` e `util`, de preferência com dois avaliadores.

Para usar os arquivos classificados nas métricas, copie-os para `saidas/` (onde os scripts procuram) depois da rotulagem:

```bash
python scripts/avaliar_validacao.py --gabarito data/rotulagem/gabarito.xlsx --ia resultados/amostra_classificada_flash_lite.csv
```
