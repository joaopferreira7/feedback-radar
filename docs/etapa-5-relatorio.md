# Etapa 5 — Relatório de prioridades de melhoria

Código: [`feedback_radar/relatorio.py`](../feedback_radar/relatorio.py), prompt `SISTEMA_RELATORIO` em [`feedback_radar/prompts.py`](../feedback_radar/prompts.py)

## Ideia central: o código calcula, o LLM escreve

| Quem faz | O quê | Por quê |
|---|---|---|
| **Código** | calcula o impacto e ordena os temas | contas feitas por LLM podem estar erradas; aqui são exatas e auditáveis |
| **Código** | escolhe as avaliações de exemplo (as mais intensas de cada tema) | garante que os exemplos são reais |
| **LLM** | escreve diagnóstico, 3 a 5 ações e cita ids dos exemplos | é a parte em que a linguagem natural agrega valor |
| **Código** | confere se os ids citados existem e insere o texto **original** no relatório | o LLM nunca "inventa" uma citação de cliente |

## Fórmula de impacto

```
frequência   = menções do tema / total de avaliações
taxa_negativa = menções negativas do tema / menções do tema
peso         = intensidade média das menções negativas / 5
impacto      = frequência × taxa_negativa × peso
```

Exemplo: "demora" aparece em 20 de 100 avaliações (frequência 0,20); 15 delas são negativas (taxa 0,75) com intensidade média 4 (peso 0,8) → impacto = 0,20 × 0,75 × 0,8 = **0,12**.

Por que essa fórmula? Um tema citado por muita gente e quase sempre de forma negativa e intensa é o que mais afeta a reputação. Com a multiplicação, um tema raro (frequência baixa) ou quase sempre elogiado (taxa negativa baixa) cai no ranking. O peso da intensidade diferencia "achei um pouco demorado" de "nunca mais volto".

**Limitação:** a fórmula não considera custo ou facilidade de implementar a ação, nem a recência (uma reclamação de ontem pesa igual a uma de um ano atrás). Ver sugestões futuras na Etapa 8.

## Validações do relatório

- Pydantic: 3 a 5 ações por tema, 1 a 3 ids, tema dentro da taxonomia.
- Ids citados precisam estar entre os exemplos enviados (senão: retry com o erro).
- Temas precisam estar no ranking enviado.

## Exportação

- **Markdown:** download direto no app ou `--relatorio saidas/relatorio.md` na linha de comando.
- **PDF:** gerado com `fpdf2` a partir do Markdown. A fonte padrão não tem emojis, então eles viram "?".
- **CSV classificado:** aba Dashboard ou `scripts/classificar_cli.py`.

## Registro de uso de IA

O módulo de relatório, a fórmula de impacto e o prompt foram gerados por IA (Claude) e testados no modo simulado (geração de Markdown e PDF). Revisão humana necessária: o grupo deve gerar ao menos um relatório com o Gemini e verificar, ação por ação, se as recomendações são viáveis para um pequeno negócio e se fazem sentido diante das avaliações citadas; discutir se a fórmula de impacto é adequada (os pesos são uma escolha nossa, não um padrão de mercado); e conferir se as ações não são genéricas demais.
