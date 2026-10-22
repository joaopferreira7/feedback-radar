# Etapa 8 — Rascunho do relatório acadêmico

> **Rascunho.** Trechos entre [colchetes] devem ser preenchidos com os resultados reais do grupo. Não entregue números que vocês não mediram.

---

# Feedback Radar: classificação de avaliações de clientes com IA Generativa para apoio à decisão em pequenos negócios

**Integrantes:** [nomes] · **Disciplina:** [nome] · **Professor(a):** [nome] · **Data:** [data]

## 1. Descrição da aplicação

Pequenos negócios recebem dezenas de avaliações por semana em plataformas como Google, iFood e Instagram, mas raramente têm tempo ou método para transformá-las em decisões. O Feedback Radar é uma aplicação web que recebe um arquivo CSV de avaliações e usa um modelo de linguagem de grande porte (LLM) para classificar cada uma quanto ao **sentimento** (positivo, neutro ou negativo), aos **temas** citados (atendimento, preço, demora, qualidade do produto, limpeza e ambiente, pedido e entrega, outros) e à **intensidade** da emoção (1 a 5), além de gerar um resumo de uma frase.

A partir dessa classificação, a aplicação apresenta um dashboard com indicadores, distribuição de sentimento, temas mais citados por sentimento e evolução temporal, e gera um **relatório de prioridades de melhoria**: os temas são ordenados por um índice de impacto (frequência × negatividade × intensidade), e o LLM propõe de 3 a 5 ações concretas para cada um, sustentadas por avaliações reais.

Como diferencial, o projeto inclui uma **validação quantitativa**: o grupo rotulou manualmente [100] avaliações e comparou os resultados da IA com esse gabarito usando acurácia, precisão, recall, F1, matriz de confusão e Kappa de Cohen.

As técnicas de IA empregadas são classificação de texto, análise de sentimento e categorização temática multirrótulo, implementadas com *prompting few-shot* e saída estruturada em JSON.

## 2. Ferramentas utilizadas

| Ferramenta | Uso | Justificativa |
|---|---|---|
| Python 3 | linguagem principal | conhecida pelo grupo, ecossistema de dados |
| pandas | leitura e manipulação dos dados | padrão para dados tabulares |
| Google Gemini 3.8 Flash (API) | classificação e geração do relatório | plano gratuito, bom desempenho em português, saída JSON |
| Pydantic | validação do JSON gerado pelo LLM | garante formato e valores permitidos |
| Streamlit | dashboard web | componentes prontos para dashboards de dados |
| Plotly | gráficos interativos | integração direta com Streamlit |
| scikit-learn | métricas de validação | implementações confiáveis de F1, Kappa e matriz de confusão |
| openpyxl | planilha de rotulagem | listas suspensas que reduzem erros de digitação |
| fpdf2 | exportação em PDF | leve e sem dependências externas |
| pytest | testes automatizados | verificação do pipeline sem custo de API |
| Git/GitHub | versionamento e colaboração | trabalho em grupo |
| Claude (Anthropic) | assistente de programação | geração inicial de código e documentação (ver seção 3.4) |

## 3. Processo de desenvolvimento

### 3.1 Etapas
O desenvolvimento seguiu 8 etapas: (1) arquitetura, (2) taxonomia e prompt, (3) pipeline de classificação, (4) dashboard, (5) relatório de prioridades, (6) validação, (7) testes e (8) relatório. [Descrever cronograma real e divisão de tarefas.]

### 3.2 Decisões principais
- **Taxonomia fechada** de 7 temas, para permitir contagem, comparação e validação automática.
- **Prompt few-shot** com 7 exemplos cobrindo ironia, gírias, avaliações mistas e relatos sem opinião.
- **Processamento em lotes** de 10 avaliações por chamada, equilibrando custo, limite de requisições e qualidade.
- **Validação e retry:** respostas fora do esquema são rejeitadas e reenviadas ao modelo junto com a mensagem de erro; após 3 falhas, o lote é dividido para isolar a avaliação problemática.
- **Separação entre cálculo e redação:** o ranking de impacto e a escolha dos exemplos são feitos por código; o LLM apenas redige diagnóstico e ações, e o código confere os ids citados. Isso reduz o risco de alucinação nas partes numéricas e nas citações.
- **Anonimização** de dados pessoais antes do envio à API, em atenção à LGPD.

### 3.3 Dados
[Descrever os dados usados: dataset público (ex.: Olist/B2W, quantidade, licença) e/ou avaliações de estabelecimento local (autorização, período, quantidade, como foram anonimizadas).]

### 3.4 Uso de IA no desenvolvimento
[Consolidar os parágrafos "Registro de uso de IA" de cada etapa (docs/etapa-1 a 7). Resumo: a primeira versão do código, dos prompts e da documentação foi gerada por um assistente de IA a partir do enunciado do grupo. O grupo revisou ..., alterou ..., corrigiu ... Descrever pelo menos 2 ou 3 casos concretos em que a revisão humana mudou algo.]

### 3.5 Resultados da validação

| Métrica | IA (Gemini) | Linha de base (regras) | Humano × humano |
|---|---|---|---|
| Acurácia (sentimento) | [ ] | [ ] | [ ] |
| F1 macro | [ ] | [ ] | — |
| Kappa de Cohen | [ ] | [ ] | [ ] |
| Recall da classe negativa | [ ] | [ ] | — |
| Jaccard médio (temas) | [ ] | [ ] | — |

[Inserir matriz de confusão e tabela de F1 por tema. Comentar onde a IA mais errou.]

**Análise de erros:** [tabela com tipo de erro (ironia, gíria, mista, curta, ambígua) × quantidade, e 3 a 5 exemplos comentados com a hipótese do grupo.]

## 4. Visão crítica

**Pontos fortes.** [Ex.: a IA lida bem com ironia explícita, coisa que a linha de base por palavras-chave não consegue; o custo por avaliação é desprezível; o relatório só cita avaliações reais.]

**Limitações.**
- *Alucinação:* resumos e diagnósticos podem conter afirmações sem base no texto. Mitigamos, mas não eliminamos.
- *Viés:* o desempenho pode ser pior com gírias regionais e escrita informal, o que significa entender pior alguns perfis de cliente. O gabarito também reflete o olhar de [6] universitários.
- *Privacidade:* os textos são processados por um serviço externo; no plano gratuito, o conteúdo pode ser usado pelo provedor. A anonimização por expressões regulares é incompleta.
- *Dependência de fornecedor:* modelos são atualizados ou descontinuados; os resultados valem para o modelo e a data testados.
- *Validade da métrica:* [100] avaliações dão uma estimativa com margem de erro considerável (para uma acurácia de ~85%, o intervalo de confiança de 95% fica em torno de ±7 pontos percentuais).
- *Fórmula de impacto:* é uma escolha do grupo, não um padrão validado, e não considera custo ou viabilidade das ações.

**Questões éticas.** A ferramenta apoia, mas não substitui, a leitura das avaliações pelo dono do negócio. Usar a classificação para punir funcionários citados seria um uso inadequado, especialmente considerando a taxa de erro medida.

## 5. Conclusões

[Responder diretamente: a IA generativa é útil para o problema proposto? Com que confiabilidade (citar Kappa/acurácia)? Para quais tipos de avaliação ela é confiável e para quais não é? Quanto custa? O que o grupo aprendeu sobre engenharia de prompt, validação e limitações de LLMs?]

## 6. Sugestões futuras

- Modelo local (Ollama) para que os dados não saiam do computador do estabelecimento.
- Comparação entre modelos (Gemini, Llama, GPT, Claude) com o mesmo gabarito.
- Ajuste fino de um modelo menor (ex.: BERTimbau) com as avaliações rotuladas, comparando custo e qualidade.
- Ponderar o impacto pela recência e incluir esforço/custo estimado das ações.
- Detecção de temas emergentes fora da taxonomia (agrupar avaliações classificadas como "outros").
- Importação direta das plataformas por APIs oficiais (ex.: Google Business Profile), com autorização do dono.
- Respostas sugeridas para as avaliações negativas.
- Acompanhamento mensal: comparar relatórios antes e depois das ações implementadas.

## Referências

- LANDIS, J. R.; KOCH, G. G. The measurement of observer agreement for categorical data. *Biometrics*, v. 33, n. 1, p. 159–174, 1977.
- BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD).
- OLIST. Brazilian E-Commerce Public Dataset by Olist. Kaggle, 2018.
- REAL, L.; OSHIRO, M.; MAFRA, A. B2W-Reviews01: an open product reviews corpus. In: *STIL*, 2019.
- Google. Gemini API documentation. https://ai.google.dev
- [Demais referências usadas pelo grupo.]

---

## Registro de uso de IA

A estrutura e o texto-base deste rascunho foram gerados por IA (Claude) a partir das etapas anteriores. As seções de resultados, dados, processo real e conclusões estão marcadas com [colchetes] porque **dependem de medições e experiências que só o grupo tem**; preenchê-las com números inventados seria fraude acadêmica. Revisão humana necessária: reescrever com a voz do grupo, conferir as referências (autores, anos e títulos) no original e adequar ao modelo de formatação exigido pelo professor (ABNT ou outro).
