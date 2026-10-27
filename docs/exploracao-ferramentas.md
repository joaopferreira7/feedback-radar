# Exploração de ferramentas de IA generativa

O enunciado pede que o grupo pesquise e teste ferramentas de IA generativa e reflita sobre as vantagens, limitações e impacto de cada uma. Até aqui o projeto usou duas: o Gemini, dentro da aplicação, e o Claude Code, para programar. Este documento organiza os testes com outras ferramentas e registra a crítica das que já foram usadas.

São três atividades independentes. Com seis pessoas, dá para cada dupla ficar com uma. Os resultados entram na seção 2 e na seção 4 do relatório.

## Atividade 1: a mesma tarefa em três chats (ChatGPT, Claude e Gemini)

Pergunta que a atividade responde: precisamos mesmo de código e API, ou um chat comum resolveria o problema do dono do negócio?

1. Depois que o gabarito humano estiver pronto (Etapa 6), gere o prompt com 20 avaliações da amostra real:

   ```bash
   python scripts/comparar_ferramentas.py preparar --amostra data/rotulagem/amostra_validacao.csv --n 20
   ```

2. Abra uma conversa nova em cada ferramenta (chatgpt.com, claude.ai e gemini.google.com, nas versões gratuitas), cole o conteúdo de `data/exploracao/prompt_para_colar.txt` e salve a resposta inteira, sem corrigir nada, em `data/exploracao/respostas/chatgpt.txt`, `claude.txt` e `gemini_web.txt`. Anote o modelo que a ferramenta informar e a data.
3. Compare:

   ```bash
   python scripts/comparar_ferramentas.py comparar --gabarito data/rotulagem/gabarito.xlsx
   ```

   O script mostra, para cada ferramenta, quantas avaliações vieram num formato válido, a acurácia de sentimento, o F1, o Kappa e a concordância de temas.

4. Repita o teste em uma das ferramentas com uma conversa nova e veja quantas classificações mudaram. Isso mede a consistência, que no chat não tem controle de temperatura.

O que observar além dos números: se a ferramenta seguiu o formato ou acrescentou texto, se respeitou a taxonomia, se aceitou as 20 avaliações de uma vez, quanto tempo levou e o que acontece com os dados enviados (cada serviço tem uma política diferente para conversas da versão gratuita; confira e registre).

O resultado esperado, a confirmar, é que os chats classificam bem, mas não escalam: com 500 avaliações seria preciso colar e copiar dezenas de vezes, sem validação nem histórico. Esse é o argumento para a aplicação existir.

## Atividade 2: o mesmo classificador numa ferramenta sem código (Dify ou Flowise)

Pergunta que a atividade responde: uma plataforma visual faria o mesmo que o nosso código em Python com menos esforço?

1. Crie uma conta gratuita no Dify (dify.ai) ou rode o Flowise localmente (exige Node.js).
2. Monte um fluxo simples: entrada de texto, um nó de LLM com o mesmo prompt de `feedback_radar/prompts.py` (conectado ao Gemini, com a chave do grupo, ou ao modelo gratuito que a plataforma oferecer) e a saída em JSON.
3. Classifique as mesmas 20 avaliações e salve as respostas em `data/exploracao/respostas/dify.txt` para entrar na comparação da Atividade 1.
4. Registre quanto tempo levou para montar, o que foi fácil e o que não foi possível fazer sem código. Pontos para verificar: validação do JSON com nova tentativa, processamento de um CSV inteiro, gráficos, cálculo da fórmula de impacto e controle de custo.

Uma boa conclusão para o relatório é dizer em que situação cada caminho vale a pena: a plataforma visual para prototipar o prompt e mostrar a ideia em uma tarde, o código quando são precisos validação, métricas e um produto que outra pessoa usa.

## Atividade 3: crítica das ferramentas que já usamos

### Gemini (API e Google AI Studio)

O AI Studio serviu para criar a chave e é o lugar mais simples para testar variações do prompt antes de mudar o código. A API foi a escolhida para a aplicação pelo plano gratuito e pela opção de pedir a resposta em JSON.

O que aconteceu na prática e deve entrar no relatório:

- O modelo planejado no início (`gemini-2.5-flash`) foi descontinuado para contas novas antes de o projeto terminar. A troca para o `gemini-3.8-flash` exigiu mudar a configuração e refazer os testes.
- No primeiro teste real, a classificação de 43 avaliações acertou as ironias e gírias dos dados de exemplo, mas o Google respondeu duas vezes com erro 503 (servidor sobrecarregado), e o pipeline só terminou por causa da nova tentativa automática.
- O plano gratuito permite poucas chamadas por dia ao modelo (20 na conta usada nos testes), o que limitou os testes do agente analista.
- Pela tabela oficial de preços, o conteúdo enviado no plano gratuito é usado pelo Google para melhorar os produtos. Por isso a anonimização vem ligada.
- O preço do plano pago dobra em janeiro de 2027.

### Claude Code (assistente de programação)

O Claude Code, da Anthropic, foi usado para gerar a primeira versão de praticamente todo o código, dos testes e da documentação, a partir do enunciado e dos pedidos do grupo. O relatório precisa dizer isso com clareza (seção 3.4), porque é exigência do professor e porque é a ferramenta que mais influenciou o resultado.

Vantagens observadas: velocidade, código comentado e organizado em módulos, testes automatizados escritos junto com o código, e a capacidade de rodar o próprio código, abrir o app no navegador e corrigir erros.

Limitações observadas neste projeto, todas registradas no histórico:

- Escolheu um modelo do Gemini que já não estava disponível para contas novas e usou preços desatualizados. O erro só apareceu no teste com a chave real.
- Uma substituição automática de texto feita por ele quebrou linhas do `.env` e do `config.py`. Ele percebeu e corrigiu, mas um erro assim poderia passar despercebido.
- Partes do sistema foram entregues sem teste completo com a API real (o agente analista, por falta de cota). A documentação dizia isso, mas cabe ao grupo conferir.
- O código é maior e mais sofisticado do que o grupo escreveria sozinho. Isso cria o risco de o grupo não conseguir explicar ou manter partes dele. A mitigação combinada é cada integrante estudar um módulo a fundo antes da apresentação.

Registrem aqui os casos em que o grupo discordou de uma sugestão do Claude Code ou mudou algo que ele gerou (por exemplo, o pedido de um visual mais sóbrio, sem emojis). Esses casos mostram a participação humana e enriquecem a visão crítica.

## Resultados da Atividade 1 (coletados em 27/10/2026)

As respostas estão em `data/exploracao/respostas/`, com o registro de como foram coletadas em `LEIA-ANTES.md`. A coleta foi feita pelo Claude Code no navegador de um integrante, com autorização dele; isso deve constar no relatório. As 20 avaliações são as primeiras da amostra real do B2W-Reviews01 (avaliações de produtos da Americanas).

Fontes comparadas: ChatGPT (conta gratuita, modelo padrão), ChatGPT de novo numa segunda conversa, Claude (conta Pro, Opus 5.5, que não é a versão gratuita), Gemini web (conta gratuita, modo automático), a nossa aplicação pela API (`gemini-3.5-flash-lite`, ver abaixo) e a linha de base por palavras-chave.

Todas as ferramentas devolveram as 20 classificações em JSON válido e dentro da taxonomia. Nenhuma precisou de correção.

Concordância de sentimento entre as fontes (proporção das 20 avaliações com o mesmo rótulo):

| | ChatGPT | ChatGPT (2ª vez) | Claude | Gemini web | Aplicação | Regras |
|---|---|---|---|---|---|---|
| ChatGPT | 1,00 | 0,95 | 1,00 | 1,00 | 0,95 | 0,75 |
| Claude | 1,00 | 0,95 | 1,00 | 1,00 | 0,95 | 0,75 |
| Gemini web | 1,00 | 0,95 | 1,00 | 1,00 | 0,95 | 0,75 |
| Aplicação | 0,95 | 1,00 | 0,95 | 0,95 | 1,00 | 0,80 |

Nos temas, a concordância entre as IAs ficou entre 0,83 e 0,94 (Jaccard médio); entre qualquer IA e a linha de base, entre 0,25 e 0,31.

O que isso mostra, antes mesmo do gabarito humano:

- Nesta tarefa, os modelos de linguagem são quase intercambiáveis: concordam entre si em 19 ou 20 das 20 avaliações. A linha de base por palavras-chave discorda deles em um quarto dos casos, sobretudo em avaliações sem palavras de emoção explícitas, como "Fiz a compra há quase 2 meses e ainda não foi entregue".
- A única avaliação que dividiu as IAs foi a mista: "Entrega rápida, produto compatível com o preço, mas uma panela veio riscada". ChatGPT, Claude e Gemini web disseram neutro; a aplicação e a segunda conversa do ChatGPT disseram negativo. É exatamente o tipo de caso que a regra 2 do prompt tenta resolver e que continua ambíguo.
- O mesmo ChatGPT, em duas conversas novas, mudou o sentimento de 1 avaliação e os temas de 3. Sem controle de temperatura, o chat não é reprodutível; a aplicação usa temperatura zero.
- Concordar não é acertar: todas podem errar do mesmo jeito. A acurácia só pode ser medida com o gabarito do grupo (`comparar_ferramentas.py comparar`).
- As 20 primeiras avaliações são relativamente fáceis (opiniões claras sobre produto e entrega). A amostra completa de 100 deve ter mais casos difíceis.

Conclusão provisória para a pergunta da atividade: um chat classifica tão bem quanto a aplicação, mas só funciona colando e copiando lotes pequenos à mão, sem validação automática, sem repetibilidade e sem painel ou histórico. O valor da aplicação está no processo em volta do modelo, não no modelo.

### Episódio com o modelo principal

Na mesma noite, o `gemini-3.8-flash` (o modelo principal da aplicação) ficou sobrecarregado: chamadas triviais levavam até três minutos, e a classificação das 100 avaliações não terminou em 40 minutos. Depois, a cota diária gratuita do `gemini-3.5-flash` acabou. A amostra foi classificada com o `gemini-3.5-flash-lite`, que tem cota própria, em 88 segundos (10 chamadas, nenhuma nova tentativa). Por isso:

- o `gemini-3.5-flash-lite` passou a ser o modelo padrão da aplicação (mais rápido e mais barato: US$ 0,30 e US$ 2,50 por milhão de tokens), com o `gemini-3.1-flash-lite` de reserva;
- a classificação agora para na hora quando a cota diária acaba, guarda o que já foi feito e pode ser retomada com `--continuar`;
- opcional: classificar a amostra também com o `gemini-3.8-flash` quando a cota voltar, para comparar os dois modelos com o gabarito (no PowerShell, defina antes `$env:GEMINI_MODELO="gemini-3.8-flash"`):

  ```bash
  GEMINI_MODELO=gemini-3.8-flash python scripts/classificar_cli.py data/rotulagem/amostra_validacao.csv --sim --saida saidas/amostra_classificada_flash.csv
  ```

## Tabela para o relatório

Preencham depois das atividades. Os números vêm de `saidas/exploracao_ferramentas.csv`.

| Ferramenta | Papel no projeto | Acurácia (20 avaliações) | Formato correto? | Ponto forte | Limitação principal |
|---|---|---|---|---|---|
| Gemini 3.8 Flash (API) | modelo padrão até 27/10/2026 | | sim (validado pelo código) | | sobrecarga e cota baixa no plano gratuito |
| Gemini 3.5 Flash-Lite (API) | modelo padrão atual; classificou a amostra | | sim | rápido, barato, cota própria | |
| ChatGPT (web) | comparação | | sim | | mudou 1 sentimento e 3 temas numa segunda conversa |
| Claude (web, Opus 5.5) | comparação | | sim | | versão paga, não comparável às gratuitas |
| Gemini (web) | comparação | | sim | | |
| Dify ou Flowise | protótipo sem código | | | | |
| Claude Code | desenvolvimento | não se aplica | não se aplica | | |
| Google AI Studio | chave de API e teste de prompts | não se aplica | não se aplica | | |

## Registro de uso de IA

O roteiro das atividades, o script `scripts/comparar_ferramentas.py` e o texto da crítica foram escritos pelo Claude Code. Os fatos listados na crítica (modelo descontinuado, erros 503, cota, edição que quebrou o `.env`) aconteceram durante o desenvolvimento e estão no histórico do projeto. Os testes com as outras ferramentas e as conclusões da tabela têm que ser feitos pelo grupo.
