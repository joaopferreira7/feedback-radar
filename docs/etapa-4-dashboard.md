# Etapa 4 — Dashboard

Código: [`app.py`](../app.py), [`feedback_radar/graficos.py`](../feedback_radar/graficos.py)

```bash
streamlit run app.py
```

## As 4 abas

| Aba | Conteúdo |
|---|---|
| **1. Dados e classificação** | upload do CSV (ou botão "Usar dados de exemplo"), avisos de validação, prévia, estimativa de custo/tempo, botão "Classificar" com barra de progresso, resumo da execução (chamadas, retries, tokens, custo, erros) |
| **2. Dashboard** | cards (total, % positivas/neutras/negativas, nota média), gráfico de sentimento, temas por sentimento (barras empilhadas), evolução mensal (se houver data), tabela filtrável por sentimento/tema/busca, download do CSV classificado |
| **3. Relatório de prioridades** | ranking de impacto calculado pelo código, botão para gerar o relatório com IA, download em Markdown e PDF |
| **4. Validação** | upload do gabarito, métricas (acurácia, F1, Kappa, Jaccard), matriz de confusão, métricas por tema, tabela de erros com hipóteses |

Barra lateral: provedor (Gemini/simulado), tamanho do lote, anonimização ligada/desligada.

## Decisões de design

- **Cores fixas por sentimento** (verde/cinza/vermelho) em todos os gráficos, para o usuário não precisar reler a legenda.
- **Temas em barras horizontais** ordenadas por total: nomes longos ficam legíveis e o mais citado aparece no topo.
- **Barras empilhadas por sentimento:** mostram de uma vez *quanto* se fala de um tema e *como* se fala dele.
- **Evolução mensal** (e não diária): com poucas avaliações por dia, o gráfico diário fica cheio de ruído.
- **`st.session_state`:** guarda o resultado da classificação. Sem isso, cada clique no Streamlit (que roda o script de novo) refaria as chamadas ao LLM.
- **CSV exportado em `utf-8-sig`:** abre com acentos corretos no Excel.
- **O app não tem regras de negócio:** só chama funções de `feedback_radar/`. Assim o dashboard pode ser trocado (ex.: por Gradio) sem mexer no núcleo.

## Limitações

- O Streamlit roda tudo de novo a cada interação; com milhares de linhas a tabela pode ficar lenta.
- Não há login: se publicado na internet, qualquer pessoa com o link usa sua chave de API. **Não publique com a sua chave** sem proteção.
- Arquivos enviados ficam na memória do servidor durante a sessão.

## Registro de uso de IA

O código do dashboard foi gerado por IA (Claude) e verificado abrindo o app no navegador com o provedor simulado e os dados de exemplo: as abas de dados, dashboard e relatório funcionaram, e a aba de validação foi testada pelo script equivalente. Revisão humana necessária: avaliar a usabilidade com alguém de fora do grupo (de preferência um dono de pequeno negócio), conferir a legibilidade dos gráficos no projetor da apresentação e decidir se os textos da interface estão claros para um usuário não técnico.
