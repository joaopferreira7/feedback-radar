# Publicar o app no Streamlit Community Cloud

Este guia cobre a Fase 1 de [aplicacao-pratica.md](aplicacao-pratica.md): colocar o Feedback Radar na internet para o piloto, com login, para que ninguém de fora use a cota da chave do Gemini.

## Configurações e login

O `feedback_radar/config.py` procura cada valor primeiro nos Secrets do Streamlit (no Cloud, em Settings > Secrets; no computador, no arquivo opcional `.streamlit/secrets.toml`) e depois no `.env`. Scripts e testes continuam usando só o `.env`.

O modelo dos Secrets está em `.streamlit/secrets.toml.example`. O `secrets.toml` e o `.env` estão no `.gitignore`; a chave nunca deve ir para o GitHub.

O `feedback_radar/login.py` roda antes do resto do app. Se os Secrets tiverem a seção `[auth]`, o app pede login com Google e só aceita os e-mails de `EMAILS_PERMITIDOS` (com a lista vazia, ninguém entra). Sem `[auth]`, ele pede a senha de `SENHA_APP`. Sem nenhum dos dois, o app fica bloqueado.

No computador, para usar sem login como antes, coloque `LOGIN_DESATIVADO=1` no `.env`. Não coloque essa opção nos Secrets do Cloud.

## 1. Criar o app

1. Entre em https://share.streamlit.io com a conta GitHub dona do repositório (`joaopferreira7`).
2. Se o repositório voltar a ser privado, autorize o acesso a repositórios privados na primeira vez; sem isso o `feedback-radar` não aparece na lista.
3. Crie um app a partir do GitHub com o repositório `joaopferreira7/feedback-radar`, branch `main` e arquivo `app.py`. Escolha o endereço, por exemplo `feedback-radar-piloto.streamlit.app`.
4. Em Advanced settings, escolha Python 3.11 ou mais novo e cole os Secrets (passo 2).
5. Faça o deploy. A primeira instalação demora alguns minutos.

O `requirements.txt` já inclui o `Authlib`, que o login com Google precisa.

## 2. Preencher os Secrets

Copie o conteúdo de `.streamlit/secrets.toml.example` e troque os valores:

- `GEMINI_API_KEY`: de preferência uma chave criada só para o app, para poder revogá-la sem atrapalhar o resto do grupo.
- `MAX_AVALIACOES`: um valor baixo no piloto, como 200.
- `EMAILS_PERMITIDOS`: os e-mails do grupo e dos donos de negócio, separados por vírgula.
- A seção `[auth]` (passo 3) ou `SENHA_APP`.

As configurações são lidas quando o app inicia. Depois de alterar os Secrets, use Reboot app no menu do app.

O app publicado roda da branch `deploy-streamlit`, e o Streamlit não permite trocar a branch de um app existente. Por isso a GitHub Action `.github/workflows/sincronizar-deploy.yml` copia a `main` para a `deploy-streamlit` a cada push: trabalhe sempre na `main`, sem commitar direto na `deploy-streamlit`.

Cada push atualiza o código do app sozinho, mas o Streamlit mantém na memória os módulos de `feedback_radar` já carregados. Se depois de um push aparecer um `ImportError`, use Reboot app.

Desde 27/10/2026 o repositório é público (para o professor e a turma verem o código). O app continua protegido pela senha ou pelo login Google. Quando o repositório era privado, o Streamlit criava o app como privado e só convidados em Share conseguiam abrir o link.

## 3. Login com Google

1. No Google Cloud Console (https://console.cloud.google.com), crie um projeto.
2. Configure a tela de consentimento OAuth como Externo, com os escopos básicos (openid, email, profile). Deixe em modo Teste e cadastre como usuários de teste os mesmos e-mails de `EMAILS_PERMITIDOS`. No modo Teste só eles conseguem entrar.
3. Em Credenciais, crie um ID do cliente OAuth do tipo Aplicativo da Web, com o URI de redirecionamento `https://SEU-APP.streamlit.app/oauth2callback`. Para testar no computador, adicione também `http://localhost:8501/oauth2callback`.
4. Copie o ID e a chave secreta do cliente para `client_id` e `client_secret` na seção `[auth]`. Use o mesmo endereço do item 3 em `redirect_uri`.
5. Gere o `cookie_secret` com `python -c "import secrets; print(secrets.token_hex(32))"`.
6. Salve, reinicie o app e teste com um e-mail da lista e com um de fora.

Se não quiser configurar o Google agora, apague a seção `[auth]` e use `SENHA_APP` com uma senha longa. A senha é a mesma para todos; se vazar, troque nos Secrets e reinicie o app.

## 4. Antes de mandar o link

Abra o endereço numa janela anônima e confira se o app pede login antes de mostrar qualquer coisa. Tente entrar com um e-mail fora da lista. Classifique os dados de exemplo primeiro com o provedor simulado e depois com o Gemini, e confira no Google AI Studio se o consumo da chave bate com o esperado.

## Riscos

Cota da chave. Todos os usuários usam a mesma chave, então um usuário autorizado pode esgotar a cota diária do plano gratuito para todo mundo. Mantenha `MAX_AVALIACOES` baixo e a lista de e-mails curta. A aba Analista usa de 3 a 5 chamadas por pergunta; no plano gratuito, isso esgota a cota diária depois de poucas perguntas. No plano pago, configure um orçamento com alerta no Google Cloud. Se a chave vazar, revogue no AI Studio e gere outra.

Privacidade. No plano gratuito do Gemini, o Google pode usar o conteúdo enviado para melhorar seus produtos; para avaliações reais de clientes, prefira o plano pago (ver [dados-e-privacidade.md](dados-e-privacidade.md)). Deixe a anonimização ligada, sabendo que ela não pega tudo. O app não grava os arquivos enviados, que ficam só na memória da sessão, mas o servidor é do Streamlit e fica fora do Brasil; os donos de negócio precisam saber disso. Com o login Google, o Streamlit recebe o nome e o e-mail de quem entra. Ainda não há separação de dados por negócio (isso é da Fase 2), então cada sessão deve ser usada para um negócio só.

Disponibilidade. No plano gratuito, o app hiberna depois de alguns dias sem uso e o primeiro acesso seguinte demora. Arquivos muito grandes podem deixar o app lento.

## Registro de uso de IA

Guia e código de login escritos com ajuda de IA; precisam de revisão do grupo. Os nomes dos menus do Streamlit Cloud e do Google Cloud mudam com frequência; confira na hora do deploy. O login com Google foi testado localmente só até a tela de entrada, sem credenciais reais.
