# Parte 2: roteiro do vídeo tutorial

O enunciado pede um vídeo de cerca de 10 minutos sobre uma ferramenta de IA generativa, com demonstração prática, explicação das funcionalidades e casos de uso, gravado e editado pelo grupo.

## Ferramenta sugerida: Google AI Studio

Motivos: é gratuito, roda no navegador sem instalar nada, o grupo já o usou para criar a chave do projeto e ele mostra de forma visual conceitos que o público de IA generativa precisa entender (prompt de sistema, temperatura, saída estruturada, tokens). Também liga o vídeo ao projeto sem repeti-lo.

Alternativas, se o grupo preferir: NotebookLM (pesquisa em documentos próprios, gera resumos e áudios), Dify (montar aplicações de IA sem código; aproveita a Atividade 2 de `exploracao-ferramentas.md`) ou Cursor (editor de código com IA). Antes de gravar, confiram a interface atual da ferramenta escolhida: os nomes de botões e menus mudam com frequência, e o roteiro abaixo descreve o que mostrar, não onde clicar.

## Roteiro (cerca de 10 minutos)

### 0:00 a 0:45 — Abertura

Quem são vocês, qual ferramenta o vídeo ensina e o que o espectador vai saber fazer no final: testar um modelo de linguagem, controlar o comportamento dele e pegar uma resposta pronta para usar num programa. Mostrar rapidamente o resultado final que será construído.

### 0:45 a 2:00 — O que é o AI Studio

Conceito: um ambiente do Google para experimentar os modelos Gemini antes de usá-los em código. Diferença para o chat do Gemini: aqui se controla o modelo, as instruções e os parâmetros, e se vê quanto cada pedido consome. Casos de uso: testar prompts, prototipar aplicações, gerar a chave de API.

### 2:00 a 4:00 — Primeiro prompt e escolha do modelo

Demonstração: escolher um modelo, escrever um pedido simples e comparar a resposta de dois modelos diferentes (um mais rápido e barato, outro mais capaz). Explicar o que são tokens, mostrando o contador.

### 4:00 a 6:00 — Instruções de sistema e temperatura

Demonstração: pedir a mesma coisa com e sem uma instrução de sistema ("você é um atendente de uma pizzaria, responda em até duas frases"). Depois mudar a temperatura e gerar a mesma resposta três vezes, mostrando que com temperatura alta ela varia e com temperatura zero fica estável. Explicar quando cada opção é útil.

### 6:00 a 8:00 — Saída estruturada (JSON)

Demonstração: pedir a classificação de três avaliações de restaurante (escritas pelo grupo) com sentimento e tema, ativando a saída em JSON. Mostrar que a resposta vira dados que um programa consegue ler. Gancho para o projeto: "foi assim que começamos o Feedback Radar". Mostrar 15 segundos do app.

### 8:00 a 9:15 — Do teste ao código

Demonstração: o botão que gera o código equivalente em Python e a criação de uma chave de API. Avisos obrigatórios: nunca publicar a chave (cobrir a tela ou usar uma chave que será apagada depois da gravação) e, no plano gratuito, o Google pode usar o conteúdo enviado, então não colocar dados pessoais.

### 9:15 a 10:00 — Limitações e encerramento

Limites de uso do plano gratuito, respostas que podem estar erradas (mostrar um erro real, se aparecer na gravação), modelos que mudam ou são descontinuados (aconteceu no projeto). Recapitular os passos e encerrar.

## Produção

Divisão sugerida para seis pessoas: duas no roteiro e nos exemplos, duas na gravação da tela e da narração, duas na edição e na revisão final.

Ferramentas gratuitas: OBS Studio para gravar a tela, DaVinci Resolve, Shotcut ou CapCut para editar. Gravar em 1080p, aumentar o zoom do navegador para o texto ficar legível e gravar a narração em ambiente silencioso, com o microfone de um fone de ouvido se não houver outro.

Para cumprir a exigência de produção própria, a narração deve ser feita pelo grupo e não por voz sintética. Se usarem IA em alguma etapa do vídeo (roteiro, legendas, trilha), digam isso nos créditos finais e no relatório.

## Registro de uso de IA

Este roteiro foi rascunhado pelo Claude Code. A escolha da ferramenta, os exemplos, a gravação e a edição são do grupo.
