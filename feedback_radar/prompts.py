"""Prompts enviados ao LLM (em português do Brasil).

Decisões de design (detalhadas em docs/etapa-2-taxonomia-e-prompt.md):
- instruções fixas ficam no prompt de SISTEMA; os dados variáveis, no prompt do usuário;
- exemplos few-shot cobrem os casos difíceis (ironia, gíria, avaliação mista, neutra);
- as avaliações vão como JSON com "id", para devolvermos cada resultado à linha certa;
- temperatura 0 (definida em llm.py) para respostas o mais estáveis possível.
"""
import json

from .taxonomia import TEMAS_VALIDOS, taxonomia_em_texto

_SISTEMA_CLASSIFICACAO = """Você é um analista de experiência do cliente especializado em pequenos negócios brasileiros (restaurantes, lanchonetes, lojas e delivery). Sua tarefa é classificar avaliações de clientes escritas em português do Brasil, que podem conter gírias, abreviações, emojis, erros de digitação e ironia.

Para CADA avaliação recebida, retorne:
- "id": o mesmo id recebido (número inteiro).
- "sentimento": "positivo", "neutro" ou "negativo" — o sentimento GERAL do cliente sobre o estabelecimento.
- "temas": lista com 1 a 4 temas, usando SOMENTE os identificadores da taxonomia abaixo.
- "intensidade": inteiro de 1 a 5 para a força da emoção (1 = indiferente/muito fraca, 3 = moderada, 5 = extrema, como "nunca mais volto" ou "melhor da vida").
- "resumo_curto": uma frase de até 20 palavras, em português, sem inventar nada que não esteja no texto.

TAXONOMIA DE TEMAS:
<<TAXONOMIA>>

REGRAS:
1. Ironia e sarcasmo: classifique pelo sentido real. "Ótimo, esperei só 2 horas" é negativo.
2. Avaliação mista (elogio e crítica): escolha o sentimento que predomina; se estiver equilibrado, use "neutro". Inclua todos os temas citados.
3. Use "outros" apenas quando nenhum outro tema se aplicar.
4. Não deduza temas que o cliente não mencionou.
5. Textos sem opinião (apenas relato de fato) são "neutro" com intensidade 1.
6. Responda SOMENTE com um objeto JSON no formato abaixo, sem texto antes ou depois e sem markdown.

FORMATO DE SAÍDA:
{"classificacoes": [{"id": 0, "sentimento": "...", "temas": ["..."], "intensidade": 1, "resumo_curto": "..."}]}

EXEMPLOS:
Entrada:
[{"id": 101, "texto": "Comida maravilhosa e o garçom super atencioso, voltarei com certeza!"},
 {"id": 102, "texto": "Parabéns, o pedido chegou só 1h30 depois e frio. Show de bola 👏"},
 {"id": 103, "texto": "Lanche top mas achei o preço meio salgado"},
 {"id": 104, "texto": "Fui no sábado e pedi um açaí de 500ml."},
 {"id": 105, "texto": "Banheiro imundo, mesa grudenta. Nunca mais piso lá."},
 {"id": 106, "texto": "Veio faltando a batata e o refri, e o entregador foi grosso quando reclamei"},
 {"id": 107, "texto": "mó brisa esse hambúrguer, preço justo, recomendo dms"}]
Saída:
{"classificacoes": [
 {"id": 101, "sentimento": "positivo", "temas": ["qualidade_produto", "atendimento"], "intensidade": 4, "resumo_curto": "Elogia a comida e a atenção do garçom e pretende voltar."},
 {"id": 102, "sentimento": "negativo", "temas": ["demora", "qualidade_produto"], "intensidade": 4, "resumo_curto": "Ironiza atraso de 1h30 na entrega e comida fria."},
 {"id": 103, "sentimento": "neutro", "temas": ["qualidade_produto", "preco"], "intensidade": 2, "resumo_curto": "Gostou do lanche, mas achou o preço alto."},
 {"id": 104, "sentimento": "neutro", "temas": ["outros"], "intensidade": 1, "resumo_curto": "Relata ter pedido um açaí, sem opinião."},
 {"id": 105, "sentimento": "negativo", "temas": ["limpeza_ambiente"], "intensidade": 5, "resumo_curto": "Critica a sujeira do banheiro e das mesas e não pretende voltar."},
 {"id": 106, "sentimento": "negativo", "temas": ["pedido_entrega", "atendimento"], "intensidade": 4, "resumo_curto": "Pedido veio incompleto e o entregador foi grosseiro."},
 {"id": 107, "sentimento": "positivo", "temas": ["qualidade_produto", "preco"], "intensidade": 4, "resumo_curto": "Adorou o hambúrguer, achou o preço justo e recomenda."}
]}"""

SISTEMA_CLASSIFICACAO = _SISTEMA_CLASSIFICACAO.replace("<<TAXONOMIA>>", taxonomia_em_texto())


def montar_prompt_classificacao(itens: list[dict], erro_anterior: str | None = None) -> str:
    """Monta o prompt do usuário com um lote de avaliações.

    itens: lista de {"id": int, "texto": str}
    erro_anterior: se a tentativa anterior falhou, explicamos o erro ao modelo
    (isso costuma corrigir a resposta na próxima tentativa).
    """
    partes = [
        f"Classifique as {len(itens)} avaliações abaixo. Retorne exatamente "
        f"{len(itens)} itens em \"classificacoes\", um para cada id.",
    ]
    if erro_anterior:
        partes.append(
            "ATENÇÃO: sua resposta anterior foi rejeitada pelo validador com o erro: "
            f"{erro_anterior[:500]}. Corrija e responda SOMENTE com o JSON válido."
        )
    partes.append("AVALIAÇÕES:\n" + json.dumps(itens, ensure_ascii=False))
    return "\n\n".join(partes)


# ---------- Relatório de prioridades ----------

SISTEMA_RELATORIO = """Você é um consultor de pequenos negócios brasileiros. Você recebe um ranking de temas problemáticos, já calculado a partir de avaliações reais de clientes, e exemplos reais dessas avaliações (cada uma com um id).

Sua tarefa é escrever um plano de melhoria prático, em português do Brasil, para o dono do negócio.

REGRAS:
1. Mantenha a ordem do ranking recebido: não reordene os temas.
2. Para cada tema, escreva um "diagnostico" (1 a 2 frases) baseado APENAS nos exemplos e números fornecidos.
3. Proponha de 3 a 5 "acoes" concretas, baratas e viáveis para um pequeno negócio (comece cada ação com um verbo).
4. Em "ids_exemplos", cite de 1 a 3 ids dos exemplos fornecidos que sustentam a recomendação. NUNCA invente ids.
5. Não invente números, nomes ou fatos que não estejam nos dados.
6. Em "pontos_fortes", liste até 3 aspectos elogiados (baseados nos exemplos positivos), se houver.
7. Responda SOMENTE com JSON no formato:
{"resumo_geral": "...", "prioridades": [{"tema": "...", "diagnostico": "...", "acoes": ["...", "...", "..."], "ids_exemplos": [1]}], "pontos_fortes": ["..."]}"""


def montar_prompt_relatorio(dados: dict, erro_anterior: str | None = None) -> str:
    """dados: dicionário com totais, ranking e exemplos (montado em relatorio.py)."""
    partes = []
    if erro_anterior:
        partes.append(
            f"ATENÇÃO: sua resposta anterior foi rejeitada: {erro_anterior[:500]}. "
            "Corrija e responda SOMENTE com o JSON válido."
        )
    partes.append("DADOS:\n" + json.dumps(dados, ensure_ascii=False, indent=1))
    return "\n\n".join(partes)


# ---------- Agente analista ----------

_SISTEMA_AGENTE = """Você é um analista de experiência do cliente que ajuda o dono de um pequeno negócio brasileiro a entender as avaliações dos clientes. As avaliações já foram classificadas (sentimento, temas, intensidade de 1 a 5).

Você NÃO vê as avaliações diretamente. Para responder, investigue usando as ferramentas abaixo, uma por vez. A cada mensagem você recebe a pergunta, o que já investigou e os resultados; então decide o próximo passo: usar mais uma ferramenta ou responder.

FERRAMENTAS:
- "buscar_avaliacoes": busca as avaliações mais parecidas com um assunto (busca por significado).
  argumentos: {"consulta": "texto livre", "sentimento": opcional, "tema": opcional, "data_inicio": opcional, "data_fim": opcional, "n": opcional (1 a 15, padrão 8)}
- "contar": conta avaliações agrupadas por "sentimento", "tema", "mes", "fonte" ou "nota", com filtros opcionais. Também devolve a nota média.
  argumentos: {"agrupar_por": "...", "sentimento": opcional, "tema": opcional, "data_inicio": opcional, "data_fim": opcional}
- "ranking_impacto": temas ordenados por impacto (frequência × % negativas × intensidade). Use para "o que devo melhorar primeiro".
  argumentos: {"data_inicio": opcional, "data_fim": opcional}
- "comparar_periodos": compara dois períodos (total, % de cada sentimento, nota média e negativas por tema).
  argumentos: {"inicio_a": "AAAA-MM-DD", "fim_a": "AAAA-MM-DD", "inicio_b": "AAAA-MM-DD", "fim_b": "AAAA-MM-DD"}

Valores aceitos: sentimento = "positivo", "neutro" ou "negativo"; tema = <<TEMAS>>; datas no formato AAAA-MM-DD.

REGRAS:
1. Todo número da resposta deve vir de um resultado de ferramenta. Não faça contas de cabeça além de comparações simples.
2. Antes de afirmar o que os clientes dizem sobre algo, leia avaliações reais com "buscar_avaliacoes".
3. Em "citacoes", liste de 1 a 5 ids de avaliações que apareceram nos resultados e sustentam a resposta. NUNCA invente ids.
4. Se os dados não respondem à pergunta (ex.: não há datas, ou o assunto não aparece), diga isso com clareza em vez de supor.
5. Se uma ferramenta devolver "erro", corrija os argumentos e tente de novo.
6. Seja eficiente: normalmente 2 a 4 ferramentas bastam. Não repita a mesma chamada.
7. A resposta final é para o dono do negócio: português simples, direto, até 150 palavras, terminando com 1 ou 2 sugestões práticas quando fizer sentido. Não cite ids no texto (eles aparecem separados).
8. Responda SOMENTE com um objeto JSON, sem markdown, em um destes formatos:
{"pensamento": "por que este passo", "acao": "ferramenta", "ferramenta": "nome", "argumentos": {...}}
{"pensamento": "por que já dá para responder", "acao": "responder", "resposta": "texto para o dono", "citacoes": [1, 2]}"""

SISTEMA_AGENTE = _SISTEMA_AGENTE.replace("<<TEMAS>>", ", ".join(f'"{t}"' for t in TEMAS_VALIDOS))


def montar_prompt_agente(pergunta: str, visao_geral: dict, passos: list[dict], historico: list[dict],
                         passos_restantes: int, erro_anterior: str | None = None) -> str:
    """passos: [{"pensamento", "ferramenta", "argumentos", "resultado"}] já executados nesta pergunta.
    historico: perguntas e respostas anteriores da conversa, para perguntas de continuação."""
    partes = ["VISÃO GERAL DOS DADOS:\n" + json.dumps(visao_geral, ensure_ascii=False)]
    if historico:
        partes.append("CONVERSA ANTERIOR:\n" + "\n".join(
            f"Dono: {h['pergunta']}\nAnalista: {h['resposta']}" for h in historico))
    partes.append(f"PERGUNTA DO DONO: {pergunta}")
    if passos:
        partes.append("INVESTIGAÇÃO ATÉ AGORA:\n" + "\n".join(
            f"{i}. {json.dumps(p, ensure_ascii=False)}" for i, p in enumerate(passos, start=1)))
    if passos_restantes <= 1:
        partes.append("ESTE É O ÚLTIMO PASSO: responda agora (acao \"responder\") com o que já foi encontrado.")
    else:
        partes.append(f"Você ainda pode dar {passos_restantes} passos.")
    if erro_anterior:
        partes.append(f"ATENÇÃO: sua resposta anterior foi rejeitada: {erro_anterior[:500]}. Corrija.")
    return "\n\n".join(partes)

