"""Configurações centrais, lidas de variáveis de ambiente (arquivo .env).

Deixar tudo aqui evita "números mágicos" espalhados pelo código e permite
mudar modelo, tamanho de lote etc. sem editar o código.
"""
import os

from dotenv import load_dotenv

load_dotenv()

PROVEDOR_LLM = os.getenv("PROVEDOR_LLM", "gemini")  # "gemini" ou "simulado"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELO = os.getenv("GEMINI_MODELO", "gemini-3.8-flash")
GEMINI_DESATIVAR_RACIOCINIO = os.getenv("GEMINI_DESATIVAR_RACIOCINIO", "1") == "1"

# Quantas avaliações vão em cada chamada ao LLM
TAMANHO_LOTE = int(os.getenv("TAMANHO_LOTE", "10"))
# Quantas vezes tentamos de novo se o JSON vier inválido ou a API falhar
MAX_TENTATIVAS = int(os.getenv("MAX_TENTATIVAS", "3"))
# Teto de avaliações por execução (protege contra gastar a cota sem querer)
MAX_AVALIACOES = int(os.getenv("MAX_AVALIACOES", "500"))
# Pausa entre chamadas, em segundos (o plano gratuito limita requisições/minuto)
PAUSA_ENTRE_CHAMADAS = float(os.getenv("PAUSA_ENTRE_CHAMADAS", "6"))

# Preços em US$ por 1 milhão de tokens — usados apenas para ESTIMAR custo
PRECO_ENTRADA_1M = float(os.getenv("PRECO_ENTRADA_1M", "0.30"))
PRECO_SAIDA_1M = float(os.getenv("PRECO_SAIDA_1M", "2.50"))

# Avaliações muito longas são cortadas (custo e foco)
MAX_CARACTERES_TEXTO = 1000
