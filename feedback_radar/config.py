"""Configurações centrais, lidas dos Secrets do Streamlit ou do arquivo .env.

Deixar tudo aqui evita "números mágicos" espalhados pelo código e permite
mudar modelo, tamanho de lote etc. sem editar o código.

Ordem de leitura de cada valor:
1. st.secrets (Secrets do Streamlit Community Cloud ou .streamlit/secrets.toml),
   só quando o código está rodando dentro do Streamlit;
2. variáveis de ambiente / arquivo .env (uso local, scripts e testes);
3. valor padrão escrito aqui.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _ler(nome: str, padrao: str = "") -> str:
    # Só olhamos st.secrets se o Streamlit já foi importado (app.py). Assim os
    # scripts e os testes continuam funcionando sem Streamlit e sem secrets.toml.
    if "streamlit" in sys.modules:
        try:
            import streamlit as st
            if nome in st.secrets:
                return str(st.secrets[nome])
        except Exception:  # sem arquivo de secrets, TOML inválido etc.
            pass
    return os.getenv(nome, padrao)


PROVEDOR_LLM = _ler("PROVEDOR_LLM", "gemini")  # "gemini" ou "simulado"
GEMINI_API_KEY = _ler("GEMINI_API_KEY", "")
GEMINI_MODELO = _ler("GEMINI_MODELO", "gemini-3.8-flash")
GEMINI_DESATIVAR_RACIOCINIO = _ler("GEMINI_DESATIVAR_RACIOCINIO", "1") == "1"
# Usado quando o modelo principal está sobrecarregado (erro 503) ou passa do tempo limite.
# Deixe vazio para não usar reserva.
GEMINI_MODELO_RESERVA = _ler("GEMINI_MODELO_RESERVA", "gemini-3.5-flash")
# Tempo máximo de espera por resposta, em segundos
GEMINI_TIMEOUT_SEGUNDOS = float(_ler("GEMINI_TIMEOUT_SEGUNDOS", "60"))
# Modelo que transforma textos em vetores (embeddings) para a busca do agente analista
GEMINI_MODELO_EMBEDDING = _ler("GEMINI_MODELO_EMBEDDING", "gemini-embedding-001")

# Quantas avaliações vão em cada chamada ao LLM
TAMANHO_LOTE = int(_ler("TAMANHO_LOTE", "10"))
# Quantas vezes tentamos de novo se o JSON vier inválido ou a API falhar
MAX_TENTATIVAS = int(_ler("MAX_TENTATIVAS", "3"))
# Teto de avaliações por execução (protege contra gastar a cota sem querer)
MAX_AVALIACOES = int(_ler("MAX_AVALIACOES", "500"))
# Pausa entre chamadas, em segundos (o plano gratuito limita requisições/minuto)
PAUSA_ENTRE_CHAMADAS = float(_ler("PAUSA_ENTRE_CHAMADAS", "6"))

# Preços em US$ por 1 milhão de tokens — usados apenas para ESTIMAR custo.
# gemini-3.8-flash, plano pago, até 31/12/2026 (em 2027 sobe para 1.50 / 7.50).
PRECO_ENTRADA_1M = float(_ler("PRECO_ENTRADA_1M", "0.75"))
PRECO_SAIDA_1M = float(_ler("PRECO_SAIDA_1M", "3.75"))

# Avaliações muito longas são cortadas (custo e foco)
MAX_CARACTERES_TEXTO = 1000
# Máximo de passos (chamadas ao LLM) do agente analista por pergunta
AGENTE_MAX_PASSOS = int(_ler("AGENTE_MAX_PASSOS", "6"))

# ---------------- Acesso ao app (ver docs/deploy.md) ----------------
# Senha simples, usada quando o login com Google (seção [auth]) não está configurado
SENHA_APP = _ler("SENHA_APP", "")
# E-mails autorizados no login com Google, separados por vírgula
EMAILS_PERMITIDOS = [e.strip().lower() for e in _ler("EMAILS_PERMITIDOS", "").split(",") if e.strip()]
# "1" libera o app sem login (só para uso local, no seu computador)
LOGIN_DESATIVADO = _ler("LOGIN_DESATIVADO", "0") == "1"
