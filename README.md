# Feedback Radar

Projeto acadêmico de IA Generativa: o usuário envia um CSV de avaliações de clientes (Google, iFood, Instagram...), um LLM classifica **sentimento**, **temas** e **intensidade** de cada uma, e o sistema gera um **dashboard**, um **relatório de prioridades de melhoria** com exemplos reais e um **agente analista** que responde perguntas sobre as avaliações investigando os dados em vários passos (busca semântica e ferramentas de contagem). O diferencial é a **validação**: comparamos a IA com a rotulagem manual do grupo em 100 avaliações.

## Como rodar localmente

Pré-requisito: Python 3.11 ou mais novo.

```bash
# 1. Criar e ativar um ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar a chave de API
copy .env.example .env        # Windows (no Linux/macOS: cp .env.example .env)
# edite o .env e cole sua chave em GEMINI_API_KEY
# (chave gratuita em https://aistudio.google.com/apikey)

# 4. Abrir o dashboard
streamlit run app.py
```

O app exige login. No seu computador, deixe `LOGIN_DESATIVADO=1` no `.env` (já vem assim no `.env.example`). Para publicar na internet com login Google ou senha, veja [docs/deploy.md](docs/deploy.md).

Sem chave? Escolha o provedor **simulado** na barra lateral (ou `PROVEDOR_LLM=simulado` no `.env`): ele usa regras por palavras-chave, sem IA e sem custo, só para testar o fluxo.

### Outros comandos

```bash
# Testes automatizados (não chamam a API)
pytest

# Classificar pela linha de comando e gerar relatório (.md + .pdf)
python scripts/classificar_cli.py data/exemplos/avaliacoes_exemplo.csv --relatorio saidas/relatorio.md

# Converter um dataset público (ex.: Olist) para o formato do projeto
python scripts/converter_dataset.py olist data/brutos/olist_order_reviews_dataset.csv --saida data/olist_500.csv

# Sortear 100 avaliações e gerar a planilha de rotulagem manual
python scripts/gerar_planilha_rotulagem.py data/olist_500.csv --n 100

# Comparar IA × gabarito humano
python scripts/avaliar_validacao.py --gabarito data/rotulagem/gabarito.xlsx --ia saidas/amostra_classificada.csv

# Rodar as perguntas de avaliação do agente analista
python scripts/avaliar_agente.py saidas/avaliacoes_classificadas.csv --provedor gemini
```

## Formato do CSV

| coluna  | obrigatória | exemplo                              |
|---------|-------------|--------------------------------------|
| `texto` | sim         | "Demorou 1h e veio frio"             |
| `data`  | não         | 21/10/2026                           |
| `nota`  | não         | 1 a 5                                |
| `fonte` | não         | Google, iFood, Instagram             |

Aceita vírgula ou ponto e vírgula, UTF-8 ou Windows-1252, e nomes alternativos de coluna (`comentario`, `review`, `estrelas`...).

## Estrutura

```
feedback-radar/
├── app.py                      # dashboard Streamlit (5 abas)
├── feedback_radar/             # lógica do sistema
│   ├── config.py               # configurações lidas dos Secrets ou do .env
│   ├── login.py                # login (Google ou senha) do app publicado
│   ├── taxonomia.py            # temas fixos e definições
│   ├── prompts.py              # prompts com few-shot
│   ├── esquemas.py             # validação do JSON (Pydantic)
│   ├── llm.py                  # cliente Gemini + modo simulado
│   ├── leitura_csv.py          # leitura/validação do CSV
│   ├── anonimizacao.py         # remoção de dados pessoais (LGPD)
│   ├── classificador.py        # lotes, retry, custo
│   ├── relatorio.py            # ranking de impacto + relatório MD/PDF
│   ├── agente.py               # agente analista (laço ReAct e ferramentas)
│   ├── busca.py                # busca semântica (embeddings ou TF-IDF)
│   ├── validacao.py            # métricas IA × humano
│   └── graficos.py             # gráficos Plotly
├── scripts/                    # linha de comando
├── tests/                      # pytest
├── data/exemplos/              # CSV fictício para demonstração
├── data/rotulagem/             # modelo da planilha de rotulagem
└── docs/                       # etapas 1 a 9 + dados e privacidade
```

## Documentação por etapa

1. [Arquitetura e estrutura de pastas](docs/etapa-1-arquitetura.md)
2. [Taxonomia de temas e prompt](docs/etapa-2-taxonomia-e-prompt.md)
3. [Pipeline de classificação](docs/etapa-3-pipeline.md)
4. [Dashboard](docs/etapa-4-dashboard.md)
5. [Relatório de prioridades](docs/etapa-5-relatorio.md)
6. [Validação contra rotulagem manual](docs/etapa-6-validacao.md)
7. [Roteiro de testes e limitações](docs/etapa-7-testes-e-limitacoes.md)
8. [Rascunho do relatório acadêmico](docs/etapa-8-relatorio-academico.md) e [apêndice dos prompts](docs/apendice-prompts.md)
9. [Agente analista](docs/etapa-9-agente-analista.md)

Extras: [Datasets, coleta de dados reais e LGPD](docs/dados-e-privacidade.md) · [Do protótipo à aplicação prática](docs/aplicacao-pratica.md) · [Publicação](docs/deploy.md)

## Entregas do trabalho

- Aplicação publicada: https://feedback-radar-jpf.streamlit.app (acesso com senha)
- Relatório: [rascunho](docs/etapa-8-relatorio-academico.md), com o [apêndice dos prompts](docs/apendice-prompts.md) (regenerar com `python scripts/exportar_prompts.py`)
- Exploração e crítica das ferramentas de IA: [docs/exploracao-ferramentas.md](docs/exploracao-ferramentas.md) e `scripts/comparar_ferramentas.py`
- Parte 2, vídeo tutorial: [roteiro](docs/parte-2-video-tutorial.md)

- Dados reais: amostra de 100 avaliações do B2W-Reviews01 em `data/rotulagem/` ([licença](data/LICENCA-DADOS.md))
- Resultados já medidos (comparação entre ferramentas, classificação da amostra, avaliação do agente): [resultados/](resultados/LEIA-ANTES.md). Não abra antes de rotular.

O que ainda depende do grupo:

1. Rotular as 100 avaliações em `data/rotulagem/planilha_rotulagem.xlsx`, em duplas, sem olhar `resultados/` nem `data/exploracao/respostas/`, e montar o `gabarito.xlsx` de consenso.
2. Rodar as métricas (`avaliar_validacao.py` e `comparar_ferramentas.py comparar`) e preencher os colchetes do relatório e dos slides.
3. Classificar a amostra com o `gemini-3.8-flash` quando a cota diária voltar (comando em `docs/exploracao-ferramentas.md`).
4. Montar o classificador no Dify ou no Flowise (Atividade 2; exige criar conta, então é com vocês).
5. Avaliar as respostas do agente (colunas `correta` e `util`).
6. Gravar o vídeo da Parte 2 e adicionar o professor como colaborador do repositório.

## Avisos importantes

- **Não faça commit do `.env`** (está no `.gitignore`).
- **Não suba dados reais de clientes** para o GitHub. Use `data/privado/` (ignorada pelo git).
- No plano gratuito, o Google pode usar o conteúdo enviado para melhorar seus produtos. Anonimize antes de enviar (a opção já vem ligada).
- Os dados em `data/exemplos/` são **fictícios**, escritos para demonstração.
