"""Leitura e validação do CSV de avaliações.

Trata os problemas mais comuns de arquivos reais:
- encoding (UTF-8 vs. Windows-1252, típico de CSV salvo no Excel);
- separador (vírgula ou ponto e vírgula);
- nomes de colunas variados ("comentário", "review", "Texto "...);
- linhas vazias, duplicadas, notas fora de 1–5 e datas inválidas.
"""
import io
import unicodedata

import pandas as pd

from . import config

COLUNA_OBRIGATORIA = "texto"
COLUNAS_OPCIONAIS = ["data", "nota", "fonte"]

# Nomes alternativos aceitos (já sem acento e em minúsculas)
SINONIMOS = {
    "texto": ["texto", "comentario", "avaliacao", "review", "review_text", "mensagem", "opiniao",
              "review_comment_message", "comment", "text"],
    "data": ["data", "date", "data_avaliacao", "submission_date", "review_creation_date"],
    "nota": ["nota", "estrelas", "rating", "score", "overall_rating", "review_score"],
    "fonte": ["fonte", "origem", "plataforma", "source", "canal"],
    "id": ["id"],
}


class ErroValidacaoCSV(Exception):
    """Erro que impede o uso do arquivo (mensagem amigável para o usuário)."""


def _normalizar_nome(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", str(nome).strip().lower())
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return nome.replace(" ", "_")


def _decodificar(conteudo: bytes) -> tuple[str, str]:
    """Tenta os encodings mais comuns no Brasil, do mais provável ao menos."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return conteudo.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ErroValidacaoCSV("Não foi possível ler o arquivo. Salve-o como CSV UTF-8.")


def ler_csv(arquivo) -> tuple[pd.DataFrame, list[str]]:
    """Lê um CSV (caminho, bytes ou arquivo enviado no Streamlit).

    Retorna (DataFrame limpo, lista de avisos para mostrar ao usuário).
    """
    avisos: list[str] = []

    if hasattr(arquivo, "read"):  # arquivo aberto ou upload do Streamlit
        conteudo = arquivo.read()
    elif isinstance(arquivo, bytes):
        conteudo = arquivo
    else:
        with open(arquivo, "rb") as f:
            conteudo = f.read()

    if not conteudo or not conteudo.strip():
        raise ErroValidacaoCSV("O arquivo está vazio.")

    texto, encoding = _decodificar(conteudo)
    if encoding != "utf-8-sig":
        avisos.append(f"Arquivo lido com encoding {encoding} (não era UTF-8).")

    try:
        # sep=None + engine="python" detecta vírgula, ponto e vírgula ou tab
        df = pd.read_csv(io.StringIO(texto), sep=None, engine="python", dtype=str)
    except Exception as erro:  # pandas lança vários tipos de erro de parsing
        raise ErroValidacaoCSV(f"O arquivo não parece ser um CSV válido: {erro}") from erro

    # Renomeia colunas para os nomes padrão
    df.columns = [_normalizar_nome(c) for c in df.columns]
    renomear = {}
    for padrao, alternativas in SINONIMOS.items():
        for coluna in df.columns:
            if coluna in alternativas and padrao not in renomear.values():
                renomear[coluna] = padrao
                break
    df = df.rename(columns=renomear)

    if COLUNA_OBRIGATORIA not in df.columns:
        raise ErroValidacaoCSV(
            f"Coluna obrigatória 'texto' não encontrada. Colunas no arquivo: {list(df.columns)}. "
            "Renomeie a coluna das avaliações para 'texto'."
        )

    # Remove linhas sem texto
    df["texto"] = df["texto"].fillna("").astype(str).str.strip()
    vazias = (df["texto"] == "").sum()
    if vazias:
        avisos.append(f"{vazias} linha(s) sem texto foram removidas.")
        df = df[df["texto"] != ""]

    duplicadas = df.duplicated(subset=["texto"]).sum()
    if duplicadas:
        avisos.append(f"{duplicadas} avaliação(ões) duplicada(s) foram removidas.")
        df = df.drop_duplicates(subset=["texto"])

    longas = (df["texto"].str.len() > config.MAX_CARACTERES_TEXTO).sum()
    if longas:
        avisos.append(f"{longas} avaliação(ões) com mais de {config.MAX_CARACTERES_TEXTO} "
                      "caracteres foram cortadas.")
        df["texto"] = df["texto"].str.slice(0, config.MAX_CARACTERES_TEXTO)

    if "nota" in df.columns:
        notas = pd.to_numeric(df["nota"].str.replace(",", "."), errors="coerce")
        invalidas = notas.notna() & ~notas.between(1, 5)
        if invalidas.sum() or (notas.isna() & df["nota"].notna()).sum():
            avisos.append("Algumas notas não estavam entre 1 e 5 e foram ignoradas.")
        df["nota"] = notas.where(notas.between(1, 5))

    if "data" in df.columns:
        # ISO (2018-04-12, como o próprio app exporta) é ano-mês-dia; o resto é tratado como
        # dia/mês/ano, o padrão brasileiro. Usar dayfirst no ISO transformaria 12/abr em 4/dez.
        texto_datas = df["data"].dropna().astype(str).str.strip()
        iso = len(texto_datas) > 0 and texto_datas.str.match(r"^\d{4}-\d{2}-\d{2}").all()
        datas = pd.to_datetime(df["data"], errors="coerce", dayfirst=not iso, format="mixed")
        invalidas = (datas.isna() & df["data"].notna()).sum()
        if invalidas:
            avisos.append(f"{invalidas} data(s) inválida(s) foram ignoradas.")
        df["data"] = datas

    if "fonte" in df.columns:
        df["fonte"] = df["fonte"].fillna("desconhecida").str.strip()

    # Mantém o id do arquivo se existir e for único (necessário na validação);
    # senão cria um sequencial.
    if "id" in df.columns:
        ids = pd.to_numeric(df["id"], errors="coerce")
        if ids.notna().all() and ids.is_unique:
            df["id"] = ids.astype(int)
        else:
            avisos.append("Coluna 'id' inválida ou repetida; ids novos foram criados.")
            df["id"] = range(1, len(df) + 1)
    else:
        df["id"] = range(1, len(df) + 1)

    if df.empty:
        raise ErroValidacaoCSV("Nenhuma avaliação válida encontrada no arquivo.")

    colunas = ["id", "texto"] + [c for c in COLUNAS_OPCIONAIS if c in df.columns]
    outras = [c for c in df.columns if c not in colunas]
    return df[colunas + outras].reset_index(drop=True), avisos
