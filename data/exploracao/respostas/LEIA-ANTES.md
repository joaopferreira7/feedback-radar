# Não abra estes arquivos antes de terminar a rotulagem

Esta pasta guarda as respostas que ChatGPT, Claude e Gemini deram para as primeiras 20 avaliações de `data/rotulagem/amostra_validacao.csv`. Quem ainda vai rotular a planilha não deve ler essas respostas: ver a classificação de uma IA antes de rotular puxa o julgamento humano para ela (viés de ancoragem) e invalida a validação.

Como as respostas foram coletadas, em 27/10/2026:

- O prompt foi o de `data/exploracao/prompt_para_colar.txt`, colado sem alterações numa conversa nova de cada ferramenta.
- ChatGPT: chatgpt.com, conta gratuita, modelo padrão (a página não informou qual). Repetido numa segunda conversa nova (`chatgpt_repeticao.txt`) para medir consistência.
- Claude: claude.ai, conta Pro, modelo Opus 5.5 com esforço médio, que era o selecionado na conta. Não é a versão gratuita, e isso deve constar no relatório.
- Gemini: gemini.google.com, modo "Gemini Auto" da conta gratuita.
- As respostas foram copiadas pelo botão "Copiar" de cada ferramenta. Na cópia do ChatGPT, o texto veio com escapes de Markdown (barra invertida no fim das linhas e `&#x20;` no lugar de espaços), que foram removidos sem alterar o conteúdo.
- A coleta foi feita pelo Claude Code, operando o navegador do integrante com autorização dele. Isso também deve ser declarado no relatório.

Depois que o gabarito existir:

```bash
python scripts/comparar_ferramentas.py comparar --gabarito data/rotulagem/gabarito.xlsx
```
