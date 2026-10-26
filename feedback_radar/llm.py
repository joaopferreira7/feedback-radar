"""Clientes de LLM.

Há dois "provedores" com a mesma interface (método gerar):
- ClienteGemini: chama a API do Google Gemini (IA de verdade).
- ClienteSimulado: regras simples por palavras-chave, SEM IA. Serve para
  testar o pipeline sem chave/sem custo e como linha de base (baseline) na
  validação: se a IA não for muito melhor que isso, algo está errado.

Trocar de provedor (ex.: Groq, Ollama) exige só criar outra classe com gerar().
"""
import json
import unicodedata
from dataclasses import dataclass

from . import config


class ErroConfiguracao(Exception):
    """Erro de configuração (ex.: chave de API ausente)."""


@dataclass
class RespostaLLM:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


def _sobrecarga(erro: Exception) -> bool:
    """Erro temporário do lado do Google: servidor sobrecarregado (503) ou tempo limite estourado (504)."""
    texto = f"{type(erro).__name__} {erro}".lower()
    return getattr(erro, "code", None) in (503, 504) or "unavailable" in texto \
        or "deadline" in texto or "timeout" in texto or "timed out" in texto


class ClienteGemini:
    def __init__(self, api_key: str | None = None, modelo: str | None = None):
        api_key = api_key or config.GEMINI_API_KEY
        if not api_key or api_key == "cole-sua-chave-aqui":
            raise ErroConfiguracao(
                "GEMINI_API_KEY não definida. Copie .env.example para .env (ou defina nos Secrets do "
                "Streamlit) e cole sua chave "
                "(https://aistudio.google.com/apikey), ou use o provedor 'simulado'."
            )
        # Import aqui dentro para o modo simulado funcionar mesmo sem a biblioteca
        from google import genai
        from google.genai import types

        # Tempo limite por chamada: sem ele, um servidor sobrecarregado deixa a tela parada por minutos
        self._cliente = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(config.GEMINI_TIMEOUT_SEGUNDOS * 1000)),
        )
        self.modelo = modelo or config.GEMINI_MODELO
        self.modelo_reserva = config.GEMINI_MODELO_RESERVA
        self.chamadas_reserva = 0  # quantas respostas vieram do modelo reserva
        self.nome = f"Gemini ({self.modelo})"

    def gerar(self, sistema: str, usuario: str, dados_simulacao=None) -> RespostaLLM:
        """Chama o modelo principal; se ele estiver sobrecarregado ou lento, tenta o reserva."""
        try:
            return self._gerar(self.modelo, sistema, usuario)
        except Exception as erro:
            if not self.modelo_reserva or not _sobrecarga(erro):
                raise
            self.chamadas_reserva += 1
            return self._gerar(self.modelo_reserva, sistema, usuario)

    def _gerar(self, modelo: str, sistema: str, usuario: str) -> RespostaLLM:
        from google.genai import types

        opcoes = dict(
            system_instruction=sistema,
            temperature=0.0,  # respostas mais estáveis/reprodutíveis
            response_mime_type="application/json",  # pede JSON puro
        )
        if config.GEMINI_DESATIVAR_RACIOCINIO:
            opcoes["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        resposta = self._cliente.models.generate_content(
            model=modelo,
            contents=usuario,
            config=types.GenerateContentConfig(**opcoes),
        )
        uso = resposta.usage_metadata
        saida = (getattr(uso, "candidates_token_count", 0) or 0) + (
            getattr(uso, "thoughts_token_count", 0) or 0
        )
        return RespostaLLM(
            texto=resposta.text or "",
            tokens_entrada=getattr(uso, "prompt_token_count", 0) or 0,
            tokens_saida=saida,
        )

    def embeddings(self, textos: list[str], tipo: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Transforma textos em vetores. tipo: RETRIEVAL_DOCUMENT (avaliações) ou RETRIEVAL_QUERY (pergunta)."""
        from google.genai import types

        vetores = []
        for i in range(0, len(textos), 100):  # a API aceita até 100 textos por chamada
            resposta = self._cliente.models.embed_content(
                model=config.GEMINI_MODELO_EMBEDDING,
                contents=textos[i:i + 100],
                config=types.EmbedContentConfig(task_type=tipo),
            )
            vetores += [e.values for e in resposta.embeddings]
        return vetores


# ---------------------------------------------------------------------------
# Provedor simulado (sem IA)
# ---------------------------------------------------------------------------

def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


_POSITIVAS = ["otimo", "excelente", "maravilh", "delicios", "gostos", "adorei", "amei", "recomendo",
              "perfeito", "top", "bom", "boa", "show", "atencios", "educad", "rapido", "limpo",
              "justo", "voltarei", "nota 10", "melhor"]
_NEGATIVAS = ["ruim", "pessim", "horrivel", "demor", "atras", "frio", "fria", "sujo", "suja", "imund",
              "grosso", "grossa", "caro", "cara ", "faltando", "errado", "nunca mais", "decepcion",
              "nojo", "lento", "mal ", "pior", "salgado", "esperei", "cru", "queimad"]
_PALAVRAS_TEMA = {
    "atendimento": ["atend", "garcom", "garconete", "funcionari", "educad", "grosso", "grossa", "simpatic",
                    "atencios", "entregador", "caixa", "dono"],
    "preco": ["preco", "caro", "barato", "valor", "custo", "taxa", "cobra", "justo", "r$"],
    "demora": ["demor", "atras", "espera", "esperei", "fila", "lento", "rapido", "hora", "minutos"],
    "qualidade_produto": ["comida", "sabor", "gostos", "delicios", "frio", "fria", "lanche", "pizza",
                          "hamburguer", "acai", "prato", "bebida", "cru", "queimad", "fresco", "produto"],
    "limpeza_ambiente": ["limp", "sujo", "suja", "imund", "banheiro", "ambiente", "barulho", "mesa",
                         "lugar", "espaco", "estacionamento", "ar condicionado"],
    "pedido_entrega": ["faltando", "faltou", "errado", "embalagem", "trocado", "veio sem", "app", "ifood"],
}


def classificar_por_regras(texto: str) -> dict:
    """Classificação ingênua por contagem de palavras. Não entende ironia!"""
    t = _sem_acento(texto) + " "
    pos = sum(t.count(p) for p in _POSITIVAS)
    neg = sum(t.count(p) for p in _NEGATIVAS)
    if neg > pos:
        sentimento = "negativo"
    elif pos > neg:
        sentimento = "positivo"
    else:
        sentimento = "neutro"
    temas = [tema for tema, palavras in _PALAVRAS_TEMA.items() if any(p in t for p in palavras)]
    intensidade = min(5, 1 + abs(pos - neg) + t.count("!"))
    return {
        "sentimento": sentimento,
        "temas": temas[:4] or ["outros"],
        "intensidade": intensidade if sentimento != "neutro" else 1,
        "resumo_curto": (texto[:80] + "...") if len(texto) > 80 else texto,
    }


_ACOES_PADRAO = {
    "atendimento": ["Fazer um treinamento rápido de atendimento com a equipe",
                    "Criar um roteiro padrão para responder reclamações",
                    "Responder publicamente às avaliações negativas em até 48h"],
    "preco": ["Revisar o preço dos itens mais criticados", "Criar combos com melhor custo-benefício",
              "Deixar taxas e preços claros no cardápio e no app"],
    "demora": ["Medir o tempo médio de preparo nos horários de pico",
               "Informar ao cliente uma estimativa de tempo realista",
               "Reforçar a equipe nos dias de maior movimento"],
    "qualidade_produto": ["Padronizar receitas e porções com fichas técnicas",
                          "Checar a temperatura e a apresentação antes de despachar",
                          "Revisar fornecedores dos itens mais criticados"],
    "limpeza_ambiente": ["Criar um checklist de limpeza por turno",
                         "Verificar banheiros a cada hora nos horários de pico",
                         "Designar um responsável fixo pela limpeza do salão"],
    "pedido_entrega": ["Conferir o pedido com checklist antes de lacrar a embalagem",
                       "Usar embalagens térmicas e lacres", "Revisar o cardápio cadastrado no app"],
    "outros": ["Ler as avaliações deste grupo para identificar novos temas",
               "Avaliar se a taxonomia precisa de um novo tema",
               "Conversar com a equipe sobre os pontos levantados"],
}


_PALAVRAS_PROBLEMA = ["reclam", "problema", "ruim", "negativ", "pior", "critic", "melhorar", "insatisf",
                      "irrit"]


def _passo_agente_simulado(dados: dict) -> dict:
    """Roteiro fixo do agente sem IA: busca, conta e responde com os números encontrados."""
    pergunta = _sem_acento(dados["pergunta"])
    passos = dados["passos"]
    feitos = [p.get("ferramenta") for p in passos]
    sentimento = "negativo" if any(p in pergunta for p in _PALAVRAS_PROBLEMA) else None
    tema = next((t for t, palavras in _PALAVRAS_TEMA.items() if any(p in pergunta for p in palavras)), None)
    filtros = {k: v for k, v in {"sentimento": sentimento, "tema": tema}.items() if v}

    if "buscar_avaliacoes" not in feitos and dados["restantes"] > 1:
        return {"pensamento": "Ler avaliações sobre o assunto da pergunta.", "acao": "ferramenta",
                "ferramenta": "buscar_avaliacoes", "argumentos": {"consulta": dados["pergunta"], **filtros, "n": 5}}
    if "contar" not in feitos and dados["restantes"] > 1:
        argumentos = {"agrupar_por": "sentimento", "tema": tema} if tema else {"agrupar_por": "tema", **filtros}
        return {"pensamento": "Contar para saber o tamanho do problema.", "acao": "ferramenta",
                "ferramenta": "contar", "argumentos": argumentos}

    resultados = {p.get("ferramenta"): p.get("resultado") or {} for p in passos}
    busca, contagem = resultados.get("buscar_avaliacoes", {}), resultados.get("contar", {})
    grupos = ", ".join(f"{k}: {v}" for k, v in list(contagem.get("grupos", {}).items())[:5])
    resposta = (f"Modo simulado (sem IA): encontrei {busca.get('encontradas', 0)} avaliações ligadas à "
                f"pergunta, num filtro de {contagem.get('total', 0)} avaliações."
                + (f" Contagem: {grupos}." if grupos else ""))
    return {"pensamento": "Já tenho exemplos e números.", "acao": "responder", "resposta": resposta,
            "citacoes": [a["id"] for a in busca.get("avaliacoes", [])][:3]}


class ClienteSimulado:
    """Imita a interface do ClienteGemini sem chamar nenhuma API."""

    nome = "Simulado (regras, sem IA)"

    def gerar(self, sistema: str, usuario: str, dados_simulacao=None) -> RespostaLLM:
        if isinstance(dados_simulacao, list):  # lote de classificação
            saida = {"classificacoes": [
                {"id": item["id"], **classificar_por_regras(item["texto"])} for item in dados_simulacao
            ]}
        elif isinstance(dados_simulacao, dict) and dados_simulacao.get("tipo") == "agente":
            saida = _passo_agente_simulado(dados_simulacao)
        else:  # relatório
            dados = dados_simulacao or {}
            prioridades = []
            for linha in dados.get("ranking", []):
                exemplos = [e["id"] for e in dados.get("exemplos_negativos", {}).get(linha["tema"], [])]
                prioridades.append({
                    "tema": linha["tema"],
                    "diagnostico": f"O tema aparece em {linha['mencoes']} avaliações, "
                                   f"{linha['pct_negativas']:.0f}% delas negativas.",
                    "acoes": _ACOES_PADRAO.get(linha["tema"], _ACOES_PADRAO["outros"]),
                    "ids_exemplos": exemplos[:2] or [0],
                })
            saida = {
                "resumo_geral": "Relatório gerado em modo SIMULADO (sem IA): as ações são genéricas "
                                "e servem apenas para testar o fluxo.",
                "prioridades": prioridades,
                "pontos_fortes": [],
            }
        return RespostaLLM(texto=json.dumps(saida, ensure_ascii=False))


def criar_cliente(provedor: str | None = None):
    provedor = (provedor or config.PROVEDOR_LLM).lower()
    if provedor == "simulado":
        return ClienteSimulado()
    if provedor == "gemini":
        return ClienteGemini()
    raise ErroConfiguracao(f"Provedor desconhecido: {provedor}. Use 'gemini' ou 'simulado'.")
