# Etapa 9: Agente analista

Código: `feedback_radar/agente.py` (laço e ferramentas), `feedback_radar/busca.py` (busca semântica), prompt `SISTEMA_AGENTE` em `feedback_radar/prompts.py`, aba Analista em `app.py`. Avaliação: `scripts/avaliar_agente.py`.

## Por que esta etapa existe

Nas etapas anteriores, cada uso da IA é uma chamada só: o código monta o pedido, o modelo devolve um JSON e o código valida. Isso funciona, mas a IA não decide nada sobre como resolver o problema.

O agente analista muda isso. O dono do negócio faz uma pergunta aberta, como "os problemas de entrega pioraram?", e o modelo precisa planejar a investigação: o que buscar, o que contar, que períodos comparar, e quando já tem informação suficiente para responder. O código continua responsável pelas contas e pela verificação, como no relatório.

## Como funciona

O padrão usado é o ReAct (raciocinar e agir, Yao et al., 2023). A cada passo o modelo recebe a pergunta, um resumo dos dados e tudo o que já investigou, e devolve um JSON com uma de duas ações: usar uma ferramenta ou responder.

```
pergunta → [LLM escolhe ferramenta → código executa → resultado volta ao LLM] × N → resposta
```

As ferramentas são funções Python. O modelo só escolhe qual usar e com quais argumentos:

- `buscar_avaliacoes`: busca as avaliações com sentido mais parecido com um assunto, com filtros opcionais de sentimento, tema e período. É a parte de recuperação do RAG (geração aumentada por recuperação): o modelo não recebe todas as avaliações, só as relevantes.
- `contar`: conta avaliações agrupadas por sentimento, tema, mês, fonte ou nota, e calcula a nota média.
- `ranking_impacto`: reaproveita a fórmula de impacto da Etapa 5.
- `comparar_periodos`: compara dois intervalos de datas (sentimento, nota média e negativas por tema).

O limite é de 6 passos por pergunta (`AGENTE_MAX_PASSOS`). No último, o prompt avisa que é hora de responder.

## Busca semântica

Cada avaliação é transformada em um vetor (embedding) pelo modelo `gemini-embedding-001`. A pergunta também vira um vetor, e a busca devolve as avaliações cujos vetores estão mais próximos (similaridade do cosseno). Assim "lugar sujo" encontra "a mesa estava grudenta", mesmo sem nenhuma palavra em comum. Esse exemplo foi conferido com a API real nos dados de exemplo.

Os vetores são calculados uma vez por arquivo classificado: são uma chamada a cada 100 avaliações, e ficam guardados na sessão. No modo simulado, ou se a API de embeddings falhar, a busca usa TF-IDF (scikit-learn), que compara palavras. É pior com sinônimos, mas permite testar tudo sem chave.

## Proteções contra alucinação

- Todo número vem de uma ferramenta. O prompt proíbe contas de cabeça e o código faz todas.
- O código guarda os ids de todas as avaliações que o modelo recebeu nos resultados. Se a resposta citar um id que não está nessa lista, ela é rejeitada e o modelo recebe o erro para corrigir. No último passo, as citações inválidas são descartadas e a tela avisa.
- O texto mostrado como citação é sempre o da avaliação original, nunca uma paráfrase do modelo.
- Argumentos inválidos (tema que não existe, data em formato errado, ferramenta desconhecida) não quebram o programa: viram uma mensagem de erro que o modelo recebe e pode corrigir no passo seguinte.
- Respostas fora do formato JSON passam pelo mesmo validador Pydantic das outras etapas.

Na tela, o expansor "Como a IA chegou nisso" mostra cada passo: o que o modelo pensou, qual ferramenta chamou, com quais argumentos e o resumo do resultado. Isso deixa a investigação auditável pelo dono e pelo grupo.

## Memória da conversa

As três últimas perguntas e respostas entram no prompt. Isso permite perguntas de continuação, como "e no iFood?" depois de "o que mais irrita os clientes?".

## Como avaliar

O script `scripts/avaliar_agente.py` roda 8 perguntas fixas, cada uma exercitando um tipo de investigação, inclusive uma sobre um assunto que não aparece nos dados (o agente deve dizer que não encontrou, e não inventar). Ele mede automaticamente se o agente respondeu, quantas chamadas fez, quais ferramentas usou, quantos erros corrigiu e quantas citações foram rejeitadas, e salva uma planilha com as colunas `correta` e `util` para o grupo preencher.

```bash
python scripts/avaliar_agente.py saidas/avaliacoes_classificadas.csv --provedor gemini
```

Sugestão para o relatório acadêmico: dois integrantes avaliam cada resposta separadamente e calculam a concordância, como foi feito na Etapa 6.

Os testes automatizados (`tests/test_agente.py`) cobrem a busca, as ferramentas, o laço com o cliente simulado, a rejeição de citação inventada e a recuperação depois de JSON inválido e de argumento errado.

## Custo e limites

Cada pergunta usa de 3 a 5 chamadas ao modelo, e o prompt cresce a cada passo porque leva os resultados anteriores. No plano gratuito do Gemini, o limite diário de chamadas ao `gemini-3.8-flash` é baixo (20 por dia na conta usada no teste), o que dá só cerca de 5 perguntas por dia. Quando a cota acaba, o app avisa na hora. Para o piloto com negócios reais, o plano pago é necessário. No plano pago, uma pergunta deve custar por volta de 1 a 2 centavos de dólar (estimativa: 4 chamadas com 2 a 4 mil tokens de entrada cada, aos preços de `config.py`); o app mostra o custo estimado de cada resposta.

## Limitações

- O laço completo com o Gemini real foi testado em 26/10/2026 com duas das oito perguntas, nos dados de exemplo: as duas foram respondidas, com 4 chamadas em média, nenhuma citação rejeitada e custo equivalente a US$ 0,013 no plano pago. Os números citados nas respostas batiam com o ranking calculado pelo código. Falta rodar as oito perguntas na amostra real e preencher a planilha antes de apresentar resultados.
- No mesmo dia, o `gemini-3.8-flash` estava sobrecarregado: uma chamada trivial levou mais de três minutos. Por isso o cliente tem tempo limite por chamada (`GEMINI_TIMEOUT_SEGUNDOS`, 60 s) e um modelo reserva (`GEMINI_MODELO_RESERVA`, `gemini-3.5-flash`) que responde quando o principal falha por sobrecarga ou demora. A resposta do reserva pode ter qualidade um pouco diferente, e o custo estimado continua usando o preço do principal.
- O modelo pode escolher ferramentas ruins ou parar cedo demais. O limite de passos evita laços infinitos, mas não garante a melhor investigação.
- A busca devolve no máximo 15 avaliações por chamada. Perguntas sobre "todas as avaliações" dependem das contagens, não da leitura de cada uma.
- As respostas herdam os erros da classificação: se uma avaliação foi classificada com o tema errado, os filtros por tema também erram.

## Registro de uso de IA

Código, prompt e este texto foram escritos com ajuda de IA (Claude) e precisam de revisão do grupo, principalmente o prompt do agente e as perguntas de avaliação.
