# Comparação de modelos (Gemini, Groq e NVIDIA)

A aba "Comparação de modelos" classifica as mesmas avaliações com vários modelos de IA e mostra se eles chegam ao mesmo resultado. Ela substituiu a antiga aba "Validação", que só funcionava com o gabarito do grupo; a comparação com o gabarito continua lá, como etapa opcional no fim da página.

## Por que comparar modelos

- Mostra se o resultado depende do modelo escolhido. Se três modelos de empresas diferentes concordam, a classificação é mais confiável do que a de um modelo só.
- Encontra as avaliações ambíguas: quando os modelos discordam, normalmente é uma avaliação com ironia, elogio misturado com crítica ou pouco texto.
- Ajuda a escolher o modelo padrão por custo, velocidade e limite gratuito, e não só pela marca.

O limite importante: concordância não é acerto. Modelos diferentes podem cometer o mesmo erro, por exemplo levar uma ironia ao pé da letra. Só o gabarito humano mede acerto; com ele, a aba mostra a acurácia, o F1, o Kappa e o recall de negativos de cada modelo lado a lado.

## Os provedores

| Provedor | Modelo padrão | Como a chave é obtida | Observação |
|---|---|---|---|
| Google Gemini | `gemini-3.5-flash-lite` | https://aistudio.google.com/apikey | modelo principal da aplicação |
| Groq | `openai/gpt-oss-120b` (modelo aberto da OpenAI) | https://console.groq.com/keys | plano gratuito com limite por minuto e por dia; muito rápido |
| NVIDIA | `minimaxai/minimax-m3.1-flash` (MiniMax) | https://build.nvidia.com, botão "Get API Key" | créditos gratuitos para testes; o mais lento dos três |
| Linha de base | regras por palavras-chave | não precisa | sem IA, serve de referência mínima |

Groq e NVIDIA usam o mesmo formato de API da OpenAI (`/chat/completions`), então um único cliente (`ClienteOpenAICompativel`, em `feedback_radar/llm.py`) atende os dois. Os modelos podem ser trocados no `.env` (`GROQ_MODELO`, `NVIDIA_MODELO`); os nomes disponíveis mudam com o tempo e aparecem nos sites de cada provedor. Os limites gratuitos também mudam: confiram nas páginas dos provedores antes de citar números no relatório.

Os três modelos são de empresas diferentes (Google, OpenAI e MiniMax), o que torna a comparação mais informativa do que comparar versões de um mesmo modelo. O padrão inicial do Groq era o `llama-3.3-70b-versatile`, que já não estava disponível quando a chave foi criada (31/10/2026); entre os modelos de texto oferecidos, o `openai/gpt-oss-120b` e o `qwen/qwen3.8-27b` classificaram 10 de 10 avaliações de teste corretamente, e o primeiro foi escolhido para trazer uma terceira família.

## Resultado com as 100 avaliações reais (31/10/2026)

Amostra: as 100 avaliações do B2W-Reviews01 em `data/rotulagem/amostra_validacao.csv`, lotes de 10. Arquivos em `resultados/comparacao_*`.

| Modelo | Classificadas | Chamadas | Novas tentativas | Tempo de API |
|---|---|---|---|---|
| Gemini `gemini-3.5-flash-lite` | 100 | 10 | 0 | 73 s |
| Groq `openai/gpt-oss-120b` | 100 | 10 | 3 | 22 s |
| NVIDIA `minimaxai/minimax-m3.1-flash` | 100 | 10 | 0 | 198 s |
| Linha de base (regras) | 100 | 10 | 0 | 0 s |

Concordância de sentimento (proporção das 100 avaliações com o mesmo rótulo):

| | Gemini | Groq | NVIDIA | Regras |
|---|---|---|---|---|
| Gemini | 1,00 | 0,96 | 0,96 | 0,75 |
| Groq | 0,96 | 1,00 | 0,93 | 0,71 |
| NVIDIA | 0,96 | 0,93 | 1,00 | 0,73 |

Concordância de temas (Jaccard médio): 0,79 a 0,82 entre as IAs; 0,37 entre qualquer IA e as regras.

O que os números mostram:

- Os três modelos, de três empresas diferentes, deram o mesmo sentimento em 93 das 100 avaliações. As regras por palavras-chave ficaram bem atrás (71% a 75%).
- As 7 avaliações em que as IAs discordaram são todas mistas, com elogio e crítica juntos, como "Ótimo celular, os pontos negativos são que a câmera às vezes borra a foto..." ou "Ótima qualidade... só veio com o pistão quebrado". É a mesma fraqueza encontrada na comparação com os chats (Atividade 1 de `exploracao-ferramentas.md`) e tratada na regra 2 do prompt, que continua ambígua na prática.
- O MiniMax (NVIDIA) tende a chamar essas avaliações mistas de "neutro", enquanto o Gemini e o GPT-OSS escolhem um lado. Qual comportamento está certo só o gabarito humano pode dizer.
- Nos temas a concordância é menor que no sentimento: os modelos concordam no que o cliente sente, mas variam mais em quais temas marcar.
- Em velocidade, o Groq foi o mais rápido (22 s, mas precisou de 3 novas tentativas por JSON inválido) e a NVIDIA a mais lenta (198 s). O Gemini ficou no meio, sem nenhuma falha.
## Agente analista com outros modelos

Os provedores também podem ser usados no agente analista, mas o resultado depende muito do modelo. No teste com o `openai/gpt-oss-120b` (Groq), o agente não conseguiu responder às perguntas sobre os dados: o modelo tentou responder sem consultar as ferramentas, citou avaliações que não tinha lido e devolveu respostas vazias. As travas do código rejeitaram tudo isso, então nada inventado chegou ao usuário, mas também não houve resposta. As perguntas fora do escopo foram recusadas corretamente. Recomendação: usar o Gemini no agente e os outros modelos na comparação de classificação.

## Configuração

No `.env` (ou nos Secrets do Streamlit, para o app publicado):

```
GROQ_API_KEY=...
NVIDIA_API_KEY=...
```

Os provedores só aparecem no app quando a chave está preenchida. Os mesmos provedores também ficam disponíveis na barra lateral, para classificar e usar o agente com eles. Como Groq e NVIDIA não oferecem embeddings neste projeto, a busca do agente usa TF-IDF quando um deles está selecionado.

## Privacidade

Cada provedor tem seus próprios termos para o conteúdo enviado no plano gratuito. A anonimização continua valendo para todos, mas enviar as mesmas avaliações a três empresas triplica a exposição: com dados reais de clientes, comparem só com avaliações já anonimizadas ou com o dataset público.

## Registro de uso de IA

O cliente, a comparação, a aba e este texto foram escritos pelo Claude Code a pedido do grupo, que escolheu os provedores (Groq e NVIDIA). Os resultados de comparação devem ser gerados e interpretados pelo grupo.
