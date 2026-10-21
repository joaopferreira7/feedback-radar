"""Anonimização básica antes de enviar textos ao LLM (LGPD).

LIMITAÇÃO IMPORTANTE: regex não encontra todos os nomes próprios. Removemos
padrões claros (e-mail, telefone, CPF, URL, @perfil) e nomes que aparecem
depois de palavras como "garçom", "atendente". Para dados reais, revise
uma amostra manualmente antes de enviar.
"""
import re

_PADROES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[LINK]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"(\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[TELEFONE]"),
    (re.compile(r"(?<!\w)@\w{3,}"), "[PERFIL]"),
]

# "o garçom João", "atendente Maria Clara", "entregador Zé"
_CARGOS = (r"(garçom|garcom|garçonete|atendente|funcionári[oa]|funcionari[oa]|entregador[a]?|"
           r"moço|moça|caixa|gerente|dono|dona|cozinheir[oa]|motoboy)")
_NOME_APOS_CARGO = re.compile(
    rf"(\b{_CARGOS}\s+(?:chamad[oa]\s+)?)([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)?)",
    re.IGNORECASE,
)


def anonimizar(texto: str, nomes_extras: list[str] | None = None) -> str:
    """Substitui dados pessoais por marcadores como [NOME] e [TELEFONE]."""
    for padrao, marcador in _PADROES:
        texto = padrao.sub(marcador, texto)

    def _troca_nome(m: re.Match) -> str:
        # Só troca se a palavra após o cargo começar com maiúscula (provável nome)
        return m.group(1) + "[NOME]" if m.group(3)[0].isupper() else m.group(0)

    texto = _NOME_APOS_CARGO.sub(_troca_nome, texto)

    for nome in nomes_extras or []:  # lista de nomes conhecidos (ex.: equipe)
        if nome.strip():
            texto = re.sub(rf"\b{re.escape(nome.strip())}\b", "[NOME]", texto, flags=re.IGNORECASE)
    return texto
