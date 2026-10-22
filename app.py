"""Dashboard do Feedback Radar (Streamlit).

Rodar com:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from feedback_radar import config
from feedback_radar.classificador import ErroAPI, classificar_dataframe, estimar_custo, lista_temas
from feedback_radar.graficos import (grafico_evolucao, grafico_matriz_confusao, grafico_sentimento,
                                     grafico_temas)
from feedback_radar.leitura_csv import ErroValidacaoCSV, ler_csv
from feedback_radar.llm import ErroConfiguracao, criar_cliente
from feedback_radar.login import exigir_login
from feedback_radar.relatorio import (calcular_impacto, gerar_relatorio, markdown_para_pdf,
                                      relatorio_markdown)
from feedback_radar.taxonomia import NOMES_TEMAS, SENTIMENTOS
from feedback_radar.validacao import calcular_metricas, carregar_gabarito, tabela_de_erros

EXEMPLO = Path(__file__).parent / "data" / "exemplos" / "avaliacoes_exemplo.csv"

st.set_page_config(page_title="Feedback Radar", layout="wide")
st.title("Feedback Radar")
st.caption("Classificação de avaliações de clientes e lista de prioridades de melhoria.")
exigir_login()  # nada abaixo roda (nem chamadas à API) sem login

# ---------------- Barra lateral: configurações ----------------
with st.sidebar:
    st.header("Configurações")
    provedor = st.selectbox(
        "Provedor de IA", ["gemini", "simulado"],
        index=0 if config.PROVEDOR_LLM == "gemini" else 1,
        help="'simulado' usa regras por palavras-chave (sem IA, sem custo) para testar o fluxo.")
    tamanho_lote = st.slider("Avaliações por chamada (lote)", 1, 25, config.TAMANHO_LOTE)
    anonimizar = st.checkbox("Anonimizar dados pessoais antes de enviar", value=True,
                             help="Remove e-mails, telefones, CPFs, links, @perfis e nomes após "
                                  "palavras como 'garçom'. Não é perfeito: revise dados reais.")
    st.divider()
    st.caption(f"Modelo: {config.GEMINI_MODELO if provedor == 'gemini' else 'regras (sem IA)'}")
    st.caption(f"Limite por execução: {config.MAX_AVALIACOES} avaliações")


def _df() -> pd.DataFrame | None:
    return st.session_state.get("df_classificado")


aba_dados, aba_dash, aba_rel, aba_val = st.tabs(
    ["Dados", "Painel", "Prioridades", "Validação"])

# ---------------- Aba 1: upload e classificação ----------------
with aba_dados:
    st.subheader("Arquivo de avaliações")
    st.markdown("Coluna obrigatória: **texto**. Opcionais: **data**, **nota** (1 a 5), **fonte**. "
                "Um arquivo já classificado pelo Feedback Radar é carregado sem nova classificação.")
    col_up, col_ex = st.columns([3, 1])
    arquivo = col_up.file_uploader("Arquivo CSV", type=["csv"])
    usar_exemplo = col_ex.button("Usar dados de exemplo")

    origem = arquivo.getvalue() if arquivo is not None else (str(EXEMPLO) if usar_exemplo else None)
    if origem is not None:
        try:
            df_bruto, avisos = ler_csv(origem)
            st.session_state["df_bruto"] = df_bruto
            st.session_state["avisos"] = avisos
            # CSV já classificado? Então não gastamos chamadas de novo.
            if {"sentimento", "temas", "status"}.issubset(df_bruto.columns):
                df_bruto["intensidade"] = pd.to_numeric(df_bruto["intensidade"], errors="coerce")
                st.session_state["df_classificado"] = df_bruto
                st.session_state["stats"] = None
                st.success("Arquivo já classificado carregado.")
        except ErroValidacaoCSV as erro:
            st.error(f"Problema no arquivo: {erro}")
            st.session_state.pop("df_bruto", None)

    df_bruto = st.session_state.get("df_bruto")
    if df_bruto is not None:
        for aviso in st.session_state.get("avisos", []):
            st.warning(aviso)
        st.write(f"**{len(df_bruto)} avaliações válidas.** Prévia:")
        st.dataframe(df_bruto.head(10), width="stretch", hide_index=True)

        if len(df_bruto) > config.MAX_AVALIACOES:
            st.warning(f"Só as primeiras {config.MAX_AVALIACOES} avaliações serão classificadas "
                       "(limite em MAX_AVALIACOES no .env ou nos Secrets).")
        a_classificar = df_bruto.head(config.MAX_AVALIACOES)

        est = estimar_custo(a_classificar["texto"].tolist(), tamanho_lote)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Chamadas ao LLM", est["lotes"])
        c2.metric("Tokens estimados", f"{est['tokens_entrada'] + est['tokens_saida']:,}".replace(",", "."))
        c3.metric("Custo se fosse pago", f"US$ {est['custo_usd']:.4f}")
        c4.metric("Tempo mínimo", f"{est['tempo_min_segundos'] / 60:.1f} min" if provedor == "gemini"
                  else "instantâneo")
        st.caption("No plano gratuito do Gemini o custo é zero, mas há limite de requisições por minuto "
                   "e por dia. Estimativa aproximada (~4 caracteres por token).")

        if st.button("Classificar avaliações", type="primary"):
            try:
                cliente = criar_cliente(provedor)
            except ErroConfiguracao as erro:
                st.error(str(erro))
                st.stop()
            barra = st.progress(0.0, text="Classificando...")
            try:
                df_class, stats = classificar_dataframe(
                    a_classificar, cliente, tamanho_lote, anonimizar_textos=anonimizar,
                    ao_progredir=lambda f: barra.progress(f, text=f"Classificando... {f:.0%}"))
            except ErroAPI as erro:
                st.error(f"{erro}\n\nVerifique a chave e o nome do modelo (GEMINI_MODELO) no .env ou nos Secrets.")
                st.stop()
            barra.empty()
            st.session_state["df_classificado"] = df_class
            st.session_state["stats"] = stats
            st.session_state["nome_modelo"] = cliente.nome
            st.session_state.pop("relatorio_md", None)

        stats = st.session_state.get("stats")
        if stats is not None and _df() is not None:
            falhas = (_df()["status"] == "erro").sum()
            (st.warning if falhas else st.success)(
                f"Concluído: {len(_df()) - falhas} classificadas, {falhas} com erro · "
                f"{stats.chamadas} chamadas · {stats.retries} retries · "
                f"{stats.tokens_entrada + stats.tokens_saida} tokens · "
                f"custo estimado US$ {stats.custo_estimado_usd:.4f} · {stats.segundos:.0f}s de API")
            if stats.erros:
                with st.expander(f"Ver {len(stats.erros)} erro(s) registrados"):
                    st.code("\n".join(stats.erros))

# ---------------- Aba 2: dashboard ----------------
with aba_dash:
    df = _df()
    if df is None:
        st.info("Nenhum arquivo classificado ainda. Comece pela aba Dados.")
    else:
        ok = df[df["status"] == "ok"]
        pct = ok["sentimento"].value_counts(normalize=True).reindex(SENTIMENTOS, fill_value=0) * 100
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Avaliações", len(ok))
        c2.metric("Positivas", f"{pct['positivo']:.0f}%")
        c3.metric("Neutras", f"{pct['neutro']:.0f}%")
        c4.metric("Negativas", f"{pct['negativo']:.0f}%")
        nota = pd.to_numeric(ok["nota"], errors="coerce").mean() if "nota" in ok else None
        c5.metric("Nota média", f"{nota:.1f}/5" if nota and nota == nota else "—")

        g1, g2 = st.columns(2)
        g1.plotly_chart(grafico_sentimento(ok), width="stretch")
        g2.plotly_chart(grafico_temas(ok), width="stretch")
        if "data" in ok and ok["data"].notna().any():
            st.plotly_chart(grafico_evolucao(ok), width="stretch")
        else:
            st.caption("Sem coluna de data: gráfico de evolução temporal indisponível.")

        st.subheader("Avaliações classificadas")
        f1, f2, f3 = st.columns(3)
        filtro_sent = f1.multiselect("Sentimento", SENTIMENTOS, default=SENTIMENTOS)
        filtro_tema = f2.multiselect("Tema", list(NOMES_TEMAS), format_func=NOMES_TEMAS.get)
        busca = f3.text_input("Buscar no texto")
        tabela = ok[ok["sentimento"].isin(filtro_sent)]
        if filtro_tema:
            tabela = tabela[tabela["temas"].map(lambda v: bool(set(lista_temas(v)) & set(filtro_tema)))]
        if busca:
            tabela = tabela[tabela["texto"].str.contains(busca, case=False, na=False)]
        colunas = [c for c in ["id", "texto", "sentimento", "temas", "intensidade", "resumo_curto",
                               "nota", "data", "fonte"] if c in tabela]
        st.dataframe(tabela[colunas], width="stretch", hide_index=True)

        st.download_button("Baixar CSV classificado",
                           df.to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig abre certo no Excel
                           "avaliacoes_classificadas.csv", "text/csv")

# ---------------- Aba 3: relatório ----------------
with aba_rel:
    df = _df()
    if df is None:
        st.info("Nenhum arquivo classificado ainda. Comece pela aba Dados.")
    else:
        st.subheader("Impacto por tema")
        st.caption("Impacto = frequência do tema × % de menções negativas × (intensidade média negativa ÷ 5). "
                   "Calculado pelo código, não pelo LLM.")
        impacto = calcular_impacto(df)
        st.dataframe(impacto.style.format({"frequencia": "{:.0%}", "pct_negativas": "{:.0f}%",
                                           "intensidade_media_neg": "{:.1f}", "impacto": "{:.3f}"}),
                     width="stretch", hide_index=True)

        if st.button("Gerar relatório", type="primary"):
            try:
                cliente = criar_cliente(provedor)
                with st.spinner("Gerando relatório..."):
                    relatorio, dados = gerar_relatorio(df, cliente)
                st.session_state["relatorio_md"] = relatorio_markdown(relatorio, dados, df, cliente.nome)
            except (ErroConfiguracao, ValueError, RuntimeError) as erro:
                st.error(str(erro))

        md = st.session_state.get("relatorio_md")
        if md:
            st.divider()
            st.markdown(md)
            d1, d2 = st.columns(2)
            d1.download_button("Baixar Markdown", md.encode("utf-8"), "relatorio_prioridades.md",
                               "text/markdown")
            d2.download_button("Baixar PDF", markdown_para_pdf(md), "relatorio_prioridades.pdf",
                               "application/pdf")

# ---------------- Aba 4: validação ----------------
with aba_val:
    st.subheader("Comparação com a rotulagem do grupo")
    st.markdown("Envie a planilha de rotulagem preenchida (gerada por "
                "`scripts/gerar_planilha_rotulagem.py`). Ela é comparada com o arquivo classificado "
                "carregado na aba Dados (os ids precisam ser os mesmos).")
    gabarito_arq = st.file_uploader("Planilha de rotulagem (.xlsx ou .csv)", type=["xlsx", "csv"])
    df = _df()
    if gabarito_arq is not None and df is None:
        st.info("Carregue também o CSV classificado na aba Dados.")
    elif gabarito_arq is not None:
        try:
            gabarito = carregar_gabarito(gabarito_arq)
            m = calcular_metricas(gabarito, df)
        except (ValueError, KeyError) as erro:
            st.error(f"Não foi possível comparar: {erro}")
            st.stop()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Avaliações comparadas", m["n"])
        c2.metric("Acurácia (sentimento)", f"{m['acuracia']:.0%}")
        c3.metric("F1 macro", f"{m['f1_macro']:.2f}")
        c4.metric("Kappa de Cohen", f"{m['kappa']:.2f}")
        c5.metric("Jaccard médio (temas)", f"{m['jaccard_medio']:.2f}")
        st.caption("Kappa: <0,4 fraco · 0,4–0,6 moderado · 0,6–0,8 substancial · >0,8 quase perfeito "
                   "(Landis & Koch). Jaccard = temas em comum ÷ temas no total.")

        v1, v2 = st.columns(2)
        v1.plotly_chart(grafico_matriz_confusao(m["matriz_confusao"]), width="stretch")
        v2.markdown("**Por classe de sentimento**")
        v2.dataframe(m["por_classe"].round(2), hide_index=True, width="stretch")
        st.markdown(f"Temas: acerto exato do conjunto em {m['acerto_exato_temas']:.0%}")
        st.dataframe(m["temas"].round(2), hide_index=True, width="stretch")

        st.markdown("Casos em que a IA discordou do grupo. As causas sugeridas são automáticas e precisam de revisão.")
        erros = tabela_de_erros(m)
        st.dataframe(erros, hide_index=True, width="stretch")
        st.download_button("Baixar tabela de erros", erros.to_csv(index=False).encode("utf-8-sig"),
                           "analise_de_erros.csv", "text/csv")
