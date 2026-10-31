"""Esquemas (Pydantic) que validam o JSON devolvido pelo LLM.

Nunca confiamos cegamente no modelo: toda resposta passa por aqui. Se algo
estiver fora do formato (sentimento inexistente, tema fora da taxonomia,
intensidade 7...), o Pydantic lança ValidationError e o pipeline tenta de novo.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .taxonomia import TEMAS_VALIDOS


class Classificacao(BaseModel):
    id: int
    sentimento: Literal["positivo", "neutro", "negativo"]
    temas: list[str] = Field(min_length=1, max_length=4)
    intensidade: int = Field(ge=1, le=5)
    resumo_curto: str = Field(min_length=3, max_length=250)

    @field_validator("sentimento", mode="before")
    @classmethod
    def normalizar_sentimento(cls, valor):
        # Aceita "Positivo", " negativo " etc.
        return valor.strip().lower() if isinstance(valor, str) else valor

    @field_validator("temas", mode="before")
    @classmethod
    def normalizar_temas(cls, valor):
        if isinstance(valor, str):  # o modelo às vezes manda string em vez de lista
            valor = [valor]
        return [t.strip().lower() for t in valor if isinstance(t, str)]

    @field_validator("temas")
    @classmethod
    def temas_na_taxonomia(cls, valor):
        invalidos = [t for t in valor if t not in TEMAS_VALIDOS]
        if invalidos:
            raise ValueError(f"temas fora da taxonomia: {invalidos}")
        return list(dict.fromkeys(valor))  # remove repetidos mantendo a ordem


class RespostaLote(BaseModel):
    classificacoes: list[Classificacao]


# ---------- Relatório de prioridades ----------

class Prioridade(BaseModel):
    tema: str
    diagnostico: str = Field(min_length=10)
    acoes: list[str] = Field(min_length=3, max_length=5)
    ids_exemplos: list[int] = Field(min_length=1, max_length=3)

    @field_validator("tema")
    @classmethod
    def tema_valido(cls, valor):
        if valor not in TEMAS_VALIDOS:
            raise ValueError(f"tema fora da taxonomia: {valor}")
        return valor


class RespostaRelatorio(BaseModel):
    resumo_geral: str = Field(min_length=20)
    prioridades: list[Prioridade] = Field(min_length=1)
    pontos_fortes: list[str] = Field(default_factory=list, max_length=5)


# ---------- Agente analista ----------

class AcaoAgente(BaseModel):
    """Um passo do agente: usar uma ferramenta ou responder."""
    pensamento: str = ""
    acao: Literal["ferramenta", "responder", "recusar"]
    ferramenta: str | None = None
    argumentos: dict = Field(default_factory=dict)
    resposta: str | None = None
    citacoes: list[int] = Field(default_factory=list)

    @field_validator("acao", mode="before")
    @classmethod
    def normalizar_acao(cls, valor):
        return valor.strip().lower() if isinstance(valor, str) else valor

    @field_validator("argumentos", mode="before")
    @classmethod
    def argumentos_vazios(cls, valor):
        return valor or {}  # o modelo às vezes manda null

    @field_validator("resposta")
    @classmethod
    def resposta_nao_vazia(cls, valor):
        if valor is not None and len(valor.strip()) < 10:
            raise ValueError("resposta vazia ou curta demais")
        return valor
