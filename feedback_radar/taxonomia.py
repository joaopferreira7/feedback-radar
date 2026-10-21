"""Taxonomia fechada de temas.

Uma lista FECHADA (em vez de deixar o LLM inventar temas) permite:
- contar e comparar temas entre execuções;
- validar automaticamente a resposta do modelo;
- comparar com a rotulagem manual do grupo.
"""

# identificador -> (nome para exibição, definição usada no prompt e no manual de rotulagem)
TEMAS = {
    "atendimento": (
        "Atendimento",
        "Comportamento das pessoas: simpatia, educação, atenção e prestatividade de "
        "funcionários, garçons, caixas ou entregadores; resposta a reclamações.",
    ),
    "preco": (
        "Preço",
        "Preço, custo-benefício, porções em relação ao valor, taxas, promoções e cobranças.",
    ),
    "demora": (
        "Demora",
        "Tempo de espera: fila, demora no preparo, atraso na entrega, lentidão para ser atendido.",
    ),
    "qualidade_produto": (
        "Qualidade do produto",
        "Sabor, frescor, temperatura, apresentação e qualidade da comida ou do produto.",
    ),
    "limpeza_ambiente": (
        "Limpeza e ambiente",
        "Higiene, limpeza, banheiro, conforto, barulho, decoração, estacionamento e estrutura do local.",
    ),
    "pedido_entrega": (
        "Pedido e entrega",
        "Itens errados ou faltando, embalagem, pedido trocado, problemas no app ou na logística "
        "(exceto tempo, que é 'demora').",
    ),
    "outros": (
        "Outros",
        "Usar SOMENTE quando nenhum outro tema se aplica.",
    ),
}

TEMAS_VALIDOS = list(TEMAS.keys())
NOMES_TEMAS = {chave: nome for chave, (nome, _) in TEMAS.items()}
SENTIMENTOS = ["positivo", "neutro", "negativo"]


def taxonomia_em_texto() -> str:
    """Formata a taxonomia como lista para colocar dentro do prompt."""
    return "\n".join(f'- "{chave}": {definicao}' for chave, (_, definicao) in TEMAS.items())
