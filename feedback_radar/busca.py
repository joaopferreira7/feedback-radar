"""Busca semântica nas avaliações (a parte de "recuperação" do RAG).

O agente analista não recebe todas as avaliações no prompt: ele pede para a
busca as avaliações mais parecidas com o que quer investigar.

Dois métodos, com a mesma interface:
- embeddings do Gemini: cada texto vira um vetor; textos com sentido parecido
  ficam próximos, mesmo sem palavras em comum ("demorou" ~ "esperei 1 hora");
- TF-IDF (scikit-learn): compara palavras. Usado no modo simulado e quando a
  API de embeddings falha. É pior com sinônimos, mas não custa nada.
"""
import re
import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class IndiceBusca:
    def __init__(self, ids: list[int], textos: list[str], cliente=None):
        self.ids = [int(i) for i in ids]
        self.aviso = None
        self._cliente = None
        # O TF-IDF é montado sempre: é barato e serve de reserva se a API falhar no meio da conversa
        self._tfidf = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                                      sublinear_tf=True)
        self._matriz_tfidf = self._tfidf.fit_transform(textos)
        self.metodo = "tfidf"
        if hasattr(cliente, "embeddings"):
            try:
                self._matriz = _normalizar(np.array(cliente.embeddings(textos)))
                self._cliente = cliente
                self.metodo = "embeddings"
            except Exception as erro:  # modelo indisponível, limite de uso etc.
                self.aviso = f"Embeddings indisponíveis ({str(erro)[:120]}); usando busca por palavras."

    def buscar(self, consulta: str, n: int = 8, ids_permitidos: set[int] | None = None) -> list[tuple[int, float]]:
        """Retorna até n pares (id, similaridade de 0 a 1), do mais parecido para o menos."""
        metodo = self.metodo
        if metodo == "embeddings":
            vetor = self._vetor_consulta(consulta)
            if vetor is None:
                metodo = "tfidf"
            else:
                notas = self._matriz @ vetor
        if metodo == "tfidf":
            # vetores do TF-IDF já saem com norma 1, então o produto é a similaridade do cosseno
            notas = (self._matriz_tfidf @ self._tfidf.transform([consulta]).T).toarray().ravel()

        resultado = []
        for posicao in np.argsort(-notas):
            id_ = self.ids[posicao]
            if ids_permitidos is not None and id_ not in ids_permitidos:
                continue
            if metodo == "tfidf" and notas[posicao] <= 0:
                break  # nenhuma palavra em comum: não é resultado
            resultado.append((id_, round(float(notas[posicao]), 3)))
            if len(resultado) == n:
                break
        return resultado

    def _vetor_consulta(self, consulta: str):
        """Embedding da pergunta. No plano gratuito, indexar 100 avaliações já gasta o limite
        de 100 textos por minuto; então esperamos o tempo pedido pela API (até 40 s) e tentamos
        uma vez mais. Se ainda falhar, devolve None e a busca usa TF-IDF nesta consulta."""
        for tentativa in range(2):
            try:
                return _normalizar(np.array(self._cliente.embeddings([consulta], tipo="RETRIEVAL_QUERY")))[0]
            except Exception as erro:
                espera = _segundos_para_tentar(erro)
                if tentativa == 0 and espera is not None and espera <= 40:
                    time.sleep(espera + 1)
                    continue
                self.aviso = f"Uma busca usou palavras em vez de embeddings ({str(erro)[:100]})."
                return None


def _segundos_para_tentar(erro: Exception) -> float | None:
    """Lê o 'Please retry in 32.07s' das mensagens de limite por minuto (429)."""
    achado = re.search(r"retry in ([\d.]+)s", str(erro))
    return float(achado.group(1)) if achado and "PerMinute" in str(erro) else None


def _normalizar(matriz: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    return matriz / np.where(normas == 0, 1, normas)
