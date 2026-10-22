# Do protótipo à aplicação prática

O protótipo já resolve o problema central (CSV → classificação → prioridades). Para virar algo que um pequeno negócio use de verdade, faltam quatro coisas: **acesso pela internet**, **histórico**, **entrada de dados mais fácil** e **adequação legal**. Abaixo, em ordem de prioridade.

## Fase 1 — Piloto com 2 ou 3 negócios reais (recomendado começar aqui)

Objetivo: provar que o relatório gera **ações de verdade**, antes de investir em tecnologia.

1. **Publicar o app** no Streamlit Community Cloud (gratuito, faz deploy direto do GitHub).
   - A chave vai em *Secrets* do Streamlit, nunca no código.
   - **Exigir login** (`st.login`, com conta Google) ou ao menos uma senha. Sem isso, qualquer pessoa com o link gasta a sua cota.
2. **Ciclo mensal com cada negócio:** o dono exporta as avaliações, vocês geram o relatório, conversam 20 minutos sobre as ações e, no mês seguinte, comparam os números.
3. **Medir o valor:** quantas ações foram implementadas? O % de negativas sobre aquele tema caiu? Isso vira um ótimo resultado para o relatório acadêmico.

## Fase 2 — Produto mínimo

| Recurso | Como | Por quê |
|---|---|---|
| Histórico por negócio | banco de dados (SQLite no início; Supabase/PostgreSQL depois) | comparar meses e mostrar se as ações funcionaram |
| Contas de usuário | um login por negócio; cada um vê só os próprios dados | privacidade e uso por vários clientes |
| Não reclassificar | guardar a classificação de cada avaliação (hash do texto) | custo: só as avaliações novas vão para a IA |
| Relatório por e-mail | envio mensal automático | o dono não precisa abrir o app |
| Sugestão de resposta | o LLM rascunha uma resposta educada para cada avaliação negativa; o dono revisa e publica | responder avaliações melhora a reputação, e é o recurso que o dono mais sente no dia a dia |

## Fase 3 — Coleta automática

- **Google:** a *Google Business Profile API* permite ler as avaliações de um perfil **com autorização do dono** (OAuth). Exige pedir acesso à API ao Google, o que pode levar algumas semanas.
- **iFood e Instagram:** sem API pública simples para avaliações; continuar com a exportação/cópia manual pelo dono.
- **Nunca usar scraping:** viola os termos das plataformas.

## Adequação legal e de custo (obrigatório antes de cobrar de alguém)

- **Plano pago da API**: no gratuito, o Google usa o conteúdo para melhorar os produtos (tabela oficial de preços). Para dados de clientes de terceiros, use o pago, ou um modelo local (Ollama).
- **LGPD**: política de privacidade, contrato com o negócio definindo vocês como *operadores* dos dados, prazo de exclusão e anonimização mantida.
- **Custo de IA**: ~US$ 0,30 a 0,40 por 1.000 avaliações hoje (o dobro a partir de 2027). Um negócio com 200 avaliações/mês custa centavos. O modo *Batch* corta pela metade.
- **Hospedagem**: grátis no Streamlit Community Cloud para o piloto; ~US$ 5 a 20/mês num servidor simples depois.

## Riscos de produto (honestos)

- O dono pode tomar decisões ruins com base num erro da IA: manter o aviso no relatório e mostrar as avaliações originais.
- **Não usar para punir funcionários**: a taxa de erro medida na validação não permite isso.
- Dependência do Google: o modelo já mudou uma vez durante o projeto. Manter o provedor configurável (`llm.py`) e refazer a validação a cada troca de modelo.

## Registro de uso de IA

Este roteiro foi gerado por IA (Claude), com os preços conferidos na página oficial do Gemini em 21/10/2026. Revisão humana necessária: confirmar com donos de negócio reais se esses recursos são os que eles querem (principalmente a sugestão de resposta), verificar as regras atuais de acesso à Google Business Profile API e consultar o professor ou um especialista antes de qualquer uso comercial (este texto não é orientação jurídica).
