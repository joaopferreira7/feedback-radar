# Datasets, coleta de dados reais e LGPD

## Datasets abertos em português

| Dataset | Conteúdo | Tamanho | Licença | Onde |
|---|---|---|---|---|
| **Olist – Brazilian E-Commerce** | avaliações de pedidos (nota 1–5 + comentário, `order_reviews`) | ~100 mil avaliações, ~40 mil com texto | CC BY-NC-SA 4.0 | Kaggle: "Brazilian E-Commerce Public Dataset by Olist" |
| **B2W-Reviews01** (Americanas) | avaliações de produtos com título, texto, nota e data | ~130 mil | CC BY-NC-SA 4.0 | github.com/americanas-tech/b2w-reviews01 |

Ambos são de **e-commerce**, não de restaurantes: os temas `demora` (atraso na entrega), `pedido_entrega` (produto errado/faltando), `qualidade_produto` e `preco` funcionam bem; `limpeza_ambiente` quase não aparece. Datasets abertos de restaurantes em português são raros, e é aí que a coleta local agrega valor ao projeto.

Licença NC (não comercial) permite uso acadêmico; cite a fonte no relatório. **Não suba o dataset inteiro para o GitHub** (é grande e tem licença própria): baixe para `data/brutos/` (ignorada pelo git) e converta uma amostra:

```bash
python scripts/converter_dataset.py olist data/brutos/olist_order_reviews_dataset.csv --saida data/olist_500.csv --amostra 500
python scripts/converter_dataset.py b2w data/brutos/B2W-Reviews01.csv --saida data/b2w_500.csv --amostra 500
```

## Coletando avaliações reais de um estabelecimento local

### 1. Autorização
- Converse com o dono/gerente e explique o projeto, quais dados serão usados e o que ele recebe em troca (o relatório de prioridades).
- Peça uma **autorização por escrito** (um termo simples de uma página): finalidade acadêmica, quais dados, prazo de guarda, compromisso de anonimização e de não publicar os dados brutos, e o nome do estabelecimento só aparece no relatório se ele permitir.

### 2. Coleta (sem scraping)
- **Google:** o dono pode ver e exportar as avaliações pelo Perfil da Empresa no Google (inclusive via Google Takeout da conta do negócio).
- **iFood:** o Portal do Parceiro mostra as avaliações; o dono pode copiá-las ou exportá-las.
- **Instagram:** comentários públicos copiados manualmente, com autorização do dono do perfil.
- **Não use robôs de scraping:** violam os termos de uso das plataformas e coletam mais dados pessoais do que o necessário.

### 3. Minimização e anonimização (LGPD)
- Colete **só** texto, data, nota e plataforma. **Não** colete nome, foto ou link do perfil de quem avaliou.
- Substitua nomes de clientes e funcionários por `[NOME]`, além de telefones, e-mails e endereços. O sistema faz parte disso automaticamente (`anonimizacao.py`), mas **revise manualmente** antes, porque a anonimização automática é incompleta.
- Atenção a dados sensíveis (LGPD art. 5º, II), como menções a saúde ("passei mal", "sou celíaco"), religião etc. Avalie removê-los ou generalizá-los.
- Guarde os dados reais em `data/privado/` (ignorada pelo git) e **apague-os ao fim do projeto**, como combinado no termo.
- No relatório e nos slides, use apenas trechos anonimizados.

### 4. Base legal e envio ao provedor de IA
- Avaliações públicas continuam sendo dados pessoais quando identificam alguém; por isso minimizamos e anonimizamos antes de qualquer processamento.
- O envio à API do Gemini é uma transferência para um terceiro (com servidores fora do Brasil). No plano gratuito, os termos permitem o uso do conteúdo para melhorar os produtos. Por isso: **anonimizar sempre** e citar isso no termo de autorização. Para dados de clientes reais em uso comercial, o certo seria usar o plano pago (sem uso para treino) ou um modelo local (Ollama).

## Registro de uso de IA

A lista de datasets, o procedimento de coleta e as orientações de LGPD foram gerados por IA (Claude). Revisão humana necessária: conferir os links, os tamanhos e as licenças dos datasets nas páginas oficiais, verificar o caminho atual de exportação de avaliações no Google e no iFood (as interfaces mudam) e, se possível, validar o termo de autorização com o professor. Este texto não é orientação jurídica.
