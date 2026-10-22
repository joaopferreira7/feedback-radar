"""Controle de acesso ao app Streamlit (ver docs/deploy.md).

Sem isso, qualquer pessoa com o link do app publicado gastaria a cota da chave.
Três modos, nesta ordem:
1. Login com Google (st.login), quando a seção [auth] existe nos Secrets.
   Só entram os e-mails listados em EMAILS_PERMITIDOS.
2. Senha simples, quando SENHA_APP está definida.
3. Nenhum dos dois: o app fica bloqueado, a não ser que LOGIN_DESATIVADO=1
   (use só no seu computador).
"""
import hmac

import streamlit as st

from . import config


def _oidc_configurado() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:  # sem arquivo de secrets
        return False


def _login_google() -> None:
    if not st.user.is_logged_in:
        st.info("Entre com sua conta Google para usar o Feedback Radar.")
        st.button("Entrar com Google", type="primary", on_click=st.login)
        st.stop()

    email = str(st.user.get("email", "")).lower()
    if not config.EMAILS_PERMITIDOS:
        st.error("Login configurado, mas EMAILS_PERMITIDOS está vazio nos Secrets. "
                 "Sem essa lista qualquer conta Google entraria, então o acesso está bloqueado.")
        st.button("Sair", on_click=st.logout)
        st.stop()
    if email not in config.EMAILS_PERMITIDOS:
        st.error(f"A conta {email} não tem acesso a este app. Peça para o grupo incluir seu e-mail.")
        st.button("Sair", on_click=st.logout)
        st.stop()

    with st.sidebar:
        st.caption(f"Conectado como {email}")
        st.button("Sair", on_click=st.logout)


def _login_senha() -> None:
    if st.session_state.get("senha_ok"):
        return
    with st.form("login"):
        senha = st.text_input("Senha de acesso", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")
    # compare_digest evita descobrir a senha medindo o tempo de resposta
    if entrar and hmac.compare_digest(senha.encode(), config.SENHA_APP.encode()):
        st.session_state["senha_ok"] = True
        st.rerun()
    if entrar:
        st.error("Senha incorreta.")
    st.stop()


def exigir_login() -> None:
    """Para a execução do app (st.stop) até o usuário se autenticar."""
    if _oidc_configurado():
        _login_google()
    elif config.SENHA_APP:
        _login_senha()
    elif not config.LOGIN_DESATIVADO:
        st.error("Acesso bloqueado: nenhum login configurado. Defina a seção [auth] (login com Google) "
                 "ou SENHA_APP nos Secrets. Para uso só no seu computador, coloque "
                 "LOGIN_DESATIVADO=1 no .env. Veja docs/deploy.md.")
        st.stop()
