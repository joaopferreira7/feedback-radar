"""Busca semântica nas avaliações (a parte de "recuperação" do RAG).

O agente analista não recebe todas as avaliações no prompt: ele pede para a
busca as avaliações mais parecidas com o que quer investigar.

Dois métodos, com a mesma interface:
- embeddings do Gemini: cada texto vira um vetor; textos com sentido parecido
  ficam próximos, mesmo sem palavras em comum ("demorou" ~ "esperei 1 hora");
- TF-IDF (scikit-learn): compara palavras. Usado no modo simulado e quando a
  API de embeddings falha. É pior com sinônimos, mas não custa nada.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class IndiceBusca:
    def __init__(self, ids: list[int], textos: list[str], cliente=None):
        self.ids = [int(i) for i in ids]
        self.aviso = None
        self._cliente = None
        if hasattr(cliente, "embeddings"):
            try:
                self._matriz = _normalizar(np.array(cliente.embeddings(textos)))
                self._cliente = cliente
                self.metodo = "embeddings"
                return
            except Exception as erro:  # modelo indisponível, limite de uso etc.
                self.aviso = f"Embeddings indisponíveis ({str(erro)[:120]}); usando busca por palavras."
        self._tfidf = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                                      sublinear_tf=True)
        self._matriz = self._tfidf.fit_transform(textos)
        self.metodo = "tfidf"

    def buscar(self, consulta: str, n: int = 8, ids_permitidos: set[int] | None = None) -> list[tuple[int, float]]:
        """Retorna até n pares (id, similaridade de 0 a 1), do mais parecido para o menos."""
        if self.metodo == "embeddings":
            vetor = _normalizar(np.array(self._cliente.embeddings([consulta], tipo="RETRIEVAL_QUERY")))
            notas = self._matriz @ vetor[0]
        else:
            # vetores do TF-IDF já saem com norma 1, então o produto é a similaridade do cosseno
            notas = (self._matriz @ self._tfidf.transform([consulta]).T).toarray().ravel()

        resultado = []
        for posicao in np.argsort(-notas):
            id_ = self.ids[posicao]
            if ids_permitidos is not None and id_ not in ids_permitidos:
                continue
            if self.metodo == "tfidf" and notas[posicao] <= 0:
                break  # nenhuma palavra em comum: não é resultado
            resultado.append((id_, round(float(notas[posicao]), 3)))
            if len(resultado) == n:
                break
        return resultado


def _normalizar(matriz: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    return matriz / np.where(normas == 0, 1, normas)
