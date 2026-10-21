"""Pipeline de classificação em lote, com validação e retry.

Fluxo para cada lote de N avaliações:
  1. monta o prompt e chama o LLM;
  2. extrai o JSON da resposta e valida com Pydantic;
  3. confere se voltou exatamente um resultado para cada id enviado;
  4. se falhar, tenta de novo (explicando o erro ao modelo), com espera crescente;
  5. se esgotar as tentativas, divide o lote ao meio e tenta cada metade —
     assim uma avaliação "problemática" não derruba as outras 9.
"""
import json
import re
import time
from dataclasses import dataclass, field

import pandas as pd
from pydantic import ValidationError

from . import config
from .anonimizacao import anonimizar
from .esquemas import Classificacao, RespostaLote
from .prompts import SISTEMA_CLASSIFICACAO, montar_prompt_classificacao


class ErroFormato(Exception):
    """A resposta do LLM não está no formato esperado."""


@dataclass
class Estatisticas:
    """Contadores para controle de custo e tempo (mostrados no dashboard)."""
    chamadas: int = 0
    retries: int = 0
    falhas: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    segundos: float = 0.0
    erros: list[str] = field(default_factory=list)

    @property
    def custo_estimado_usd(self) -> float:
        return (self.tokens_entrada * config.PRECO_ENTRADA_1M
                + self.tokens_saida * config.PRECO_SAIDA_1M) / 1_000_000


def extrair_json(texto: str) -> dict:
    """Extrai o objeto JSON da resposta, mesmo que venha dentro de ```json ... ```."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ErroFormato("resposta não contém um objeto JSON")
    try:
        return json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError as erro:
        raise ErroFormato(f"JSON inválido: {erro}") from erro


def _validar_lote(texto: str, ids_esperados: set[int]) -> list[Classificacao]:
    try:
        lote = RespostaLote.model_validate(extrair_json(texto))
    except ValidationError as erro:
        raise ErroFormato(str(erro)) from erro
    ids_recebidos = [c.id for c in lote.classificacoes]
    if set(ids_recebidos) != ids_esperados or len(ids_recebidos) != len(ids_esperados):
        faltando = ids_esperados - set(ids_recebidos)
        sobrando = set(ids_recebidos) - ids_esperados
        raise ErroFormato(f"ids não conferem (faltando: {sorted(faltando)}, "
                          f"inesperados: {sorted(sobrando)}, recebidos: {len(ids_recebidos)})")
    return lote.classificacoes


def classificar_lote(cliente, itens: list[dict], stats: Estatisticas,
                     pausa: float = 0.0) -> dict[int, Classificacao]:
    """Classifica um lote. Retorna {id: Classificacao}; ids que falharam ficam de fora."""
    ids = {item["id"] for item in itens}
    erro_anterior = None

    for tentativa in range(1, config.MAX_TENTATIVAS + 1):
        if tentativa > 1:
            stats.retries += 1
        try:
            inicio = time.time()
            resposta = cliente.gerar(
                SISTEMA_CLASSIFICACAO,
                montar_prompt_classificacao(itens, erro_anterior),
                dados_simulacao=itens,
            )
            stats.segundos += time.time() - inicio
            stats.chamadas += 1
            stats.tokens_entrada += resposta.tokens_entrada
            stats.tokens_saida += resposta.tokens_saida
            if pausa:
                time.sleep(pausa)  # respeita o limite de requisições por minuto
            return {c.id: c for c in _validar_lote(resposta.texto, ids)}

        except ErroFormato as erro:
            erro_anterior = str(erro)
            stats.erros.append(f"Formato (tentativa {tentativa}): {erro_anterior[:200]}")
        except Exception as erro:  # erro de rede/API (ex.: 429 limite de uso)
            erro_anterior = None
            stats.erros.append(f"API (tentativa {tentativa}): {str(erro)[:200]}")
            # Espera exponencial: 5s, 10s, 20s... (mais longa se for limite de uso)
            espera = 5 * 2 ** (tentativa - 1)
            if "429" in str(erro) or "RESOURCE_EXHAUSTED" in str(erro):
                espera = max(espera, 30)
            time.sleep(espera)

    # Esgotou as tentativas: divide o lote para isolar a avaliação problemática
    if len(itens) > 1:
        meio = len(itens) // 2
        resultado = classificar_lote(cliente, itens[:meio], stats, pausa)
        resultado.update(classificar_lote(cliente, itens[meio:], stats, pausa))
        return resultado

    stats.falhas += 1
    return {}


def estimar_custo(textos: list[str], tamanho_lote: int = config.TAMANHO_LOTE) -> dict:
    """Estimativa ANTES de rodar: ~4 caracteres por token em português (aproximação)."""
    n_lotes = max(1, -(-len(textos) // tamanho_lote))  # divisão arredondando para cima
    tokens_sistema = len(SISTEMA_CLASSIFICACAO) // 4
    tokens_entrada = n_lotes * tokens_sistema + sum(len(t) for t in textos) // 4 + 15 * len(textos)
    tokens_saida = 45 * len(textos)  # ~45 tokens por classificação em JSON
    custo = (tokens_entrada * config.PRECO_ENTRADA_1M + tokens_saida * config.PRECO_SAIDA_1M) / 1e6
    return {
        "lotes": n_lotes,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "custo_usd": custo,
        "custo_por_avaliacao_usd": custo / max(1, len(textos)),
        "tempo_min_segundos": n_lotes * config.PAUSA_ENTRE_CHAMADAS,
    }


def classificar_dataframe(df: pd.DataFrame, cliente, tamanho_lote: int = config.TAMANHO_LOTE,
                          anonimizar_textos: bool = True, pausa: float | None = None,
                          ao_progredir=None) -> tuple[pd.DataFrame, Estatisticas]:
    """Classifica todas as linhas de df (precisa das colunas 'id' e 'texto').

    ao_progredir: função opcional f(fracao_concluida) para barras de progresso.
    Retorna (df com colunas novas, estatísticas).
    """
    if pausa is None:
        pausa = config.PAUSA_ENTRE_CHAMADAS if cliente.__class__.__name__ == "ClienteGemini" else 0
    stats = Estatisticas()
    df = df.copy()
    df["texto_enviado"] = df["texto"].map(anonimizar) if anonimizar_textos else df["texto"]

    itens = [{"id": int(i), "texto": t} for i, t in zip(df["id"], df["texto_enviado"])]
    resultados: dict[int, Classificacao] = {}
    lotes = [itens[i:i + tamanho_lote] for i in range(0, len(itens), tamanho_lote)]
    for n, lote in enumerate(lotes, start=1):
        resultados.update(classificar_lote(cliente, lote, stats, pausa))
        if ao_progredir:
            ao_progredir(n / len(lotes))

    df["sentimento"] = df["id"].map(lambda i: resultados[i].sentimento if i in resultados else None)
    df["temas"] = df["id"].map(lambda i: ";".join(resultados[i].temas) if i in resultados else None)
    df["intensidade"] = df["id"].map(lambda i: resultados[i].intensidade if i in resultados else None)
    df["resumo_curto"] = df["id"].map(lambda i: resultados[i].resumo_curto if i in resultados else None)
    df["status"] = df["id"].map(lambda i: "ok" if i in resultados else "erro")
    return df, stats


def lista_temas(valor) -> list[str]:
    """Converte a coluna 'temas' ("a;b") de volta em lista."""
    if not isinstance(valor, str) or not valor:
        return []
    return [t for t in valor.split(";") if t]
