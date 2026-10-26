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

## Tabela para o relatório

Preencham depois das atividades. Os números vêm de `saidas/exploracao_ferramentas.csv`.

| Ferramenta | Papel no projeto | Acurácia (20 avaliações) | Formato correto? | Ponto forte | Limitação principal |
|---|---|---|---|---|---|
| Gemini 3.8 Flash (API) | classificação, relatório e agente na aplicação | | | | |
| ChatGPT (web) | comparação | | | | |
| Claude (web) | comparação | | | | |
| Gemini (web) | comparação | | | | |
| Dify ou Flowise | protótipo sem código | | | | |
| Claude Code | desenvolvimento | não se aplica | não se aplica | | |
| Google AI Studio | chave de API e teste de prompts | não se aplica | não se aplica | | |

## Registro de uso de IA

O roteiro das atividades, o script `scripts/comparar_ferramentas.py` e o texto da crítica foram escritos pelo Claude Code. Os fatos listados na crítica (modelo descontinuado, erros 503, cota, edição que quebrou o `.env`) aconteceram durante o desenvolvimento e estão no histórico do projeto. Os testes com as outras ferramentas e as conclusões da tabela têm que ser feitos pelo grupo.
