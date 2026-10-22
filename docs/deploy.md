# Publicar o app no Streamlit Community Cloud

Passo a passo da Fase 1 de [aplicacao-pratica.md](aplicacao-pratica.md): deixar o Feedback Radar acessível pela internet para o piloto com negócios reais, **com login**, para que ninguém de fora gaste a cota da chave do Gemini.

## Como o app lê as configurações

`feedback_radar/config.py` procura cada valor nesta ordem:

1. **Secrets do Streamlit** (`st.secrets`): no Cloud, a tela *Settings > Secrets*; no computador, o arquivo opcional `.streamlit/secrets.toml`;
2. **variáveis de ambiente / `.env`** (uso local, scripts e testes, como antes);
3. o valor padrão do código.

O modelo dos Secrets está em [`.streamlit/secrets.toml.example`](../.streamlit/secrets.toml.example). O `.streamlit/secrets.toml` e o `.env` estão no `.gitignore`. **Nunca** coloque a chave em arquivo que vai para o GitHub.

## Como funciona o login

`feedback_radar/login.py` roda antes de qualquer outra parte do app:

| Configuração nos Secrets | O que acontece |
|---|---|
| Seção `[auth]` presente | Botão "Entrar com Google" (`st.login`). Só entram os e-mails de `EMAILS_PERMITIDOS`. Sem essa lista, ninguém entra. |
| Sem `[auth]`, com `SENHA_APP` | Pede uma senha simples, igual para todo mundo. |
| Nenhum dos dois | App **bloqueado**. Só libera com `LOGIN_DESATIVADO=1`, que é para usar no seu computador. |

> Para continuar usando localmente como antes, coloque `LOGIN_DESATIVADO=1` no seu `.env` (já está no `.env.example`). **Não** coloque isso nos Secrets do Cloud.

## Passo 1: preparar o repositório

O app usa o repositório privado `joaopferreira7/feedback-radar`. Confira que a branch que vai ao ar (ex.: `main`) tem este código e que o `requirements.txt` inclui `Authlib` (necessário para o `st.login`).

## Passo 2: criar o app no Streamlit Community Cloud

1. Acesse <https://share.streamlit.io> e entre com a conta GitHub de quem é dono do repositório (`joaopferreira7`).
2. Na primeira vez, autorize o Streamlit a ler **repositórios privados** (o GitHub pede essa permissão; sem ela o repositório não aparece na lista).
3. Clique em **Create app > Deploy a public app from GitHub** (o nome engana: o app pode ter o código privado; quem protege o acesso é o login).
4. Preencha:
   - **Repository:** `joaopferreira7/feedback-radar`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** escolha um nome, ex.: `feedback-radar-piloto` → `https://feedback-radar-piloto.streamlit.app`
5. Em **Advanced settings**, escolha **Python 3.11 ou mais novo** e cole os Secrets (passo 3). Dá para colar depois, em *Settings > Secrets*.
6. Clique em **Deploy**. A primeira instalação leva alguns minutos.

## Passo 3: configurar os Secrets

Copie o conteúdo de `.streamlit/secrets.toml.example` para a caixa de Secrets e troque os valores:

- `GEMINI_API_KEY`: a chave do Google AI Studio. De preferência uma **chave só para o app**, separada da que o grupo usa no dia a dia, para dar para revogar sem afetar ninguém.
- `MAX_AVALIACOES`: deixe baixo no piloto (ex.: `200`).
- `EMAILS_PERMITIDOS`: e-mails Google do grupo e dos donos de negócio do piloto, separados por vírgula.
- A seção `[auth]` (passo 4) **ou** `SENHA_APP`.

Depois de mudar Secrets, use **Reboot app** no menu do app para garantir que os novos valores sejam lidos (o `config.py` lê tudo uma vez, ao iniciar).

## Passo 4: configurar o login com Google

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto (ex.: `feedback-radar`).
2. **APIs e serviços > Tela de consentimento OAuth** (ou *Google Auth Platform*):
   - Tipo de usuário: **Externo**.
   - Nome do app, e-mail de suporte e e-mail do desenvolvedor.
   - Escopos: só os básicos (`openid`, `email`, `profile`).
   - Deixe em modo **Teste** e adicione como *usuários de teste* os mesmos e-mails de `EMAILS_PERMITIDOS` (no modo Teste, só eles conseguem entrar, o que é uma segunda proteção).
3. **APIs e serviços > Credenciais > Criar credenciais > ID do cliente OAuth**:
   - Tipo: **Aplicativo da Web**.
   - **URIs de redirecionamento autorizados:**
     - `https://SEU-APP.streamlit.app/oauth2callback`
     - (opcional, para testar no computador) `http://localhost:8501/oauth2callback`
4. Copie o **ID do cliente** e a **chave secreta do cliente** para `client_id` e `client_secret` na seção `[auth]` dos Secrets.
5. Preencha `redirect_uri` com o mesmo endereço do item 3 e gere um `cookie_secret` aleatório:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

6. Salve os Secrets, reinicie o app e teste: entre com um e-mail da lista (deve funcionar) e com um de fora (deve aparecer "não tem acesso").

**Alternativa rápida (sem Google):** apague a seção `[auth]` e defina `SENHA_APP` com uma senha longa. É mais simples, mas a senha é compartilhada: se vazar, troque nos Secrets e reinicie o app.

## Passo 5: conferir antes de mandar o link

- [ ] Abrir o link numa janela anônima: deve pedir login, sem mostrar nada do app.
- [ ] Entrar com um e-mail fora da lista: acesso negado.
- [ ] Classificar os dados de exemplo com o provedor **simulado** (sem custo) e depois com **gemini**.
- [ ] Conferir no [Google AI Studio](https://aistudio.google.com/) o uso da chave depois do teste.

## Riscos e cuidados

**Cota e custo da chave**
- Todo mundo que entra usa a **mesma chave**. Um usuário autorizado pode, sem querer, esgotar a cota diária do plano gratuito para todos. Mantenha `MAX_AVALIACOES` baixo e a lista de e-mails curta.
- No plano pago, defina um **limite de gastos** no Google Cloud (orçamento com alerta).
- Se a chave vazar (print, commit, mensagem), **revogue no AI Studio na hora** e crie outra.

**Privacidade (LGPD)**
- No plano **gratuito** do Gemini, o Google pode usar o conteúdo enviado para melhorar os produtos. Para avaliações reais de clientes de terceiros, prefira o plano pago (ver [aplicacao-pratica.md](aplicacao-pratica.md) e [dados-e-privacidade.md](dados-e-privacidade.md)).
- Mantenha **"Anonimizar dados pessoais"** ligado. Ele não é perfeito: revise os dados antes.
- O app **não guarda** os arquivos: eles ficam na memória da sessão e somem quando ela fecha. Mas o servidor é do Streamlit (fora do Brasil). Informe isso aos donos de negócio.
- O login Google faz o Streamlit receber nome e e-mail de quem entra. Use só para controle de acesso.
- O código do repositório continua privado, mas qualquer pessoa da lista vê os dados que **ela mesma** enviou. Não existe separação por negócio ainda (isso é da Fase 2): não use a mesma sessão para dois negócios diferentes.

**Disponibilidade**
- No plano gratuito, o app "dorme" depois de alguns dias sem uso; o primeiro acesso depois disso demora para acordar.
- Os recursos do servidor são limitados: arquivos muito grandes podem deixar o app lento.

## Registro de uso de IA

Este guia e as mudanças de login/Secrets foram feitos com IA (Claude). Revisão humana necessária: os nomes de menus do Streamlit Cloud e do Google Cloud Console mudam com frequência, então confira na hora do deploy. O login com Google foi testado localmente só até a tela "Entrar com Google" (sem credenciais reais); o fluxo completo precisa ser testado no app publicado.
