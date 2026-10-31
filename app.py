"""Dashboard do Feedback Radar (Streamlit).

Rodar com:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from feedback_radar import config
from feedback_radar.agente import criar_indice, perguntar, resumo_resultado
from feedback_radar.classificador import ErroAPI, classificar_dataframe, estimar_custo, lista_temas
from feedback_radar.exportacao import para_csv, para_excel
from feedback_radar.graficos import (grafico_concordancia, grafico_evolucao, grafico_matriz_confusao,
                                     grafico_sentimento, grafico_temas)
from feedback_radar.leitura_csv import ErroValidacaoCSV, ler_csv
from feedback_radar.comparacao import acuracia_por_modelo, classificar_com_modelos, concordancia
from feedback_radar.llm import ErroConfiguracao, criar_cliente, provedores_configurados
from feedback_radar.login import exigir_login
from feedback_radar.relatorio import (calcular_impacto, gerar_relatorio, markdown_para_pdf,
                                      relatorio_markdown)
from feedback_radar.taxonomia import NOMES_TEMAS, SENTIMENTOS
from feedback_radar.validacao import calcular_metricas, carregar_gabarito, tabela_de_erros

EXEMPLO = Path(__file__).parent / "data" / "exemplos" / "avaliacoes_exemplo.csv"
MODELOS = {"gemini": config.GEMINI_MODELO, "groq": config.GROQ_MODELO, "nvidia": config.NVIDIA_MODELO,
           "simulado": "regras (sem IA)"}

st.set_page_config(page_title="Feedback Radar", layout="wide")
st.title("Feedback Radar")
st.caption("Classificação de avaliações de clientes e lista de prioridades de melhoria.")
exigir_login()  # nada abaixo roda (nem chamadas à API) sem login

# ---------------- Barra lateral: configurações ----------------
with st.sidebar:
    st.header("Configurações")
    opcoes = provedores_configurados()  # só aparecem os provedores com chave preenchida
    provedor = st.selectbox(
        "Provedor de IA", opcoes,
        index=opcoes.index(config.PROVEDOR_LLM) if config.PROVEDOR_LLM in opcoes else 0,
        help="'simulado' usa regras por palavras-chave (sem IA, sem custo) para testar o fluxo.")
    tamanho_lote = st.slider("Avaliações por chamada (lote)", 1, 25, config.TAMANHO_LOTE)
    anonimizar = st.checkbox("Anonimizar dados pessoais antes de enviar", value=True,
                             help="Remove e-mails, telefones, CPFs, links, @perfis e nomes após "
                                  "palavras como 'garçom'. Não é perfeito: revise dados reais.")
    st.divider()
    st.caption(f"Modelo: {MODELOS[provedor]}")
    st.caption(f"Limite por execução: {config.MAX_AVALIACOES} avaliações")


def _df() -> pd.DataFrame | None:
    return st.session_state.get("df_classificado")


aba_dados, aba_dash, aba_rel, aba_ana, aba_val = st.tabs(
    ["Dados", "Painel", "Prioridades", "Analista", "Comparação de modelos"])

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
            if stats.interrompido:
                st.warning(stats.interrompido + " As avaliações que faltaram estão com status 'erro'. "
                           "Para completá-las sem refazer as outras, use "
                           "`python scripts/classificar_cli.py ... --continuar`.")
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

        b1, b2, _ = st.columns([1, 1, 2])
        b1.download_button("Baixar planilha Excel", para_excel(df), "avaliacoes_classificadas.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary")
        b2.download_button("Baixar CSV", para_csv(df), "avaliacoes_classificadas.csv", "text/csv",
                           help="Separado por ponto e vírgula, como o Excel em português espera. "
                                "Pode ser enviado de volta ao app sem classificar de novo.")

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

# ---------------- Aba 4: agente analista ----------------
SUGESTOES = ["O que mais irrita os clientes?", "O que eles mais elogiam?",
             "Os problemas de entrega pioraram ao longo dos meses?"]

with aba_ana:
    df = _df()
    if df is None:
        st.info("Nenhum arquivo classificado ainda. Comece pela aba Dados.")
    else:
        st.subheader("Pergunte sobre as avaliações")
        st.caption("A IA investiga em vários passos antes de responder: busca avaliações parecidas com o "
                   "assunto, pede contagens e comparações ao código e só então responde, citando "
                   "avaliações reais. As contas são sempre feitas pelo código.")
        conversa = st.session_state.setdefault("conversa", [])

        for item in conversa:
            r = item["resultado"]
            with st.container(border=True):
                st.markdown(f"**{item['pergunta']}**")
                if r.fora_do_escopo:
                    st.info(r.resposta)
                    continue
                st.write(r.resposta)
                col = "texto_enviado" if "texto_enviado" in df else "texto"
                textos = df.set_index(df["id"].astype(int))
                for id_ in r.citacoes:
                    linha = textos.loc[id_]
                    st.markdown(f"> {linha[col]}\n>\n> *avaliação {id_}, {linha['sentimento']}*")
                if r.citacoes_rejeitadas:
                    st.caption(f"{len(r.citacoes_rejeitadas)} citação(ões) descartada(s): a IA citou "
                               "avaliações que não tinha lido.")
                with st.expander(f"Como a IA chegou nisso ({len(r.passos)} passos)"):
                    for n, passo in enumerate(r.passos, start=1):
                        if passo.erro:
                            st.markdown(f"**{n}.** Resposta rejeitada pelo validador: {passo.erro[:200]}")
                        elif passo.ferramenta:
                            st.markdown(f"**{n}.** {passo.pensamento}  \n`{passo.ferramenta}` "
                                        f"`{json.dumps(passo.argumentos, ensure_ascii=False)}`  \n"
                                        f"{resumo_resultado(passo.resultado)}")
                        else:
                            st.markdown(f"**{n}.** {passo.pensamento} Resposta final.")
                st.caption(f"{r.chamadas} chamadas ao LLM · {r.tokens_entrada + r.tokens_saida} tokens · "
                           f"custo estimado US$ {r.custo_estimado_usd:.4f}")

        clicada = None
        colunas = st.columns(len(SUGESTOES))
        for coluna, sugestao in zip(colunas, SUGESTOES):
            if coluna.button(sugestao, key=f"sugestao_{sugestao}", width="stretch"):
                clicada = sugestao
        with st.form("form_pergunta", clear_on_submit=True):
            texto = st.text_input("Sua pergunta", placeholder="Ex.: por que as notas caíram em março?")
            enviar = st.form_submit_button("Perguntar", type="primary")
        pergunta = clicada or (texto.strip() if enviar else "")

        if pergunta:
            try:
                cliente = criar_cliente(provedor)
            except ErroConfiguracao as erro:
                st.error(str(erro))
                st.stop()
            # O índice de busca é montado uma vez por arquivo classificado e provedor
            chave = (provedor, id(df))
            if st.session_state.get("indice_chave") != chave:
                with st.spinner("Preparando a busca nas avaliações..."):
                    st.session_state["indice"] = criar_indice(df, cliente)
                st.session_state["indice_chave"] = chave
            indice = st.session_state["indice"]
            if indice.aviso:
                st.warning(indice.aviso)
            # Perguntas recusadas não entram no histórico: não ajudam e poderiam desviar o modelo
            historico = [{"pergunta": c["pergunta"], "resposta": c["resultado"].resposta} for c in conversa
                         if not c["resultado"].fora_do_escopo]
            with st.status("Investigando...", expanded=True) as status:
                try:
                    resultado = perguntar(pergunta, df, cliente, indice, historico,
                                          ao_passo=lambda p: status.write(
                                              f"{p.ferramenta}: {resumo_resultado(p.resultado)}"))
                except ErroAPI as erro:
                    status.update(label="Erro", state="error")
                    st.error(str(erro))
                    st.stop()
            conversa.append({"pergunta": pergunta, "resultado": resultado})
            st.rerun()

        if conversa and st.button("Limpar conversa"):
            st.session_state["conversa"] = []
            st.rerun()

# ---------------- Aba 5: comparação de modelos ----------------
with aba_val:
    st.subheader("Os modelos chegam ao mesmo resultado?")
    st.markdown("Classifica as mesmas avaliações com vários modelos de IA e mostra onde eles concordam "
                "e onde discordam. Concordar não é acertar: modelos diferentes podem errar do mesmo jeito. "
                "Para medir acerto, envie o gabarito do grupo no fim da página.")
    df = _df()
    df_base = df if df is not None else st.session_state.get("df_bruto")
    if df_base is None:
        st.info("Carregue um arquivo na aba Dados primeiro.")
    else:
        disponiveis = provedores_configurados()
        faltando = [p for p in ("groq", "nvidia") if p not in disponiveis]
        if faltando:
            st.caption(f"Sem chave configurada: {', '.join(faltando)}. Veja docs/comparacao-modelos.md.")
        c1, c2 = st.columns([3, 1])
        escolhidos = c1.multiselect(
            "Modelos", disponiveis, default=disponiveis,
            format_func=lambda p: f"{p} ({MODELOS[p]})" if p != "simulado" else "linha de base (regras)")
        n = c2.number_input("Avaliações", 5, min(200, len(df_base)), min(30, len(df_base)), step=5,
                            help="Cada modelo classifica as mesmas avaliações. Use poucas para poupar a cota.")

        if st.button("Comparar modelos", type="primary", disabled=len(escolhidos) < 2):
            try:
                clientes = {p: criar_cliente(p) for p in escolhidos}
            except ErroConfiguracao as erro:
                st.error(str(erro))
                st.stop()
            barra = st.progress(0.0, text="Classificando...")
            total = len(clientes)
            ordem = {nome: i for i, nome in enumerate(clientes)}

            def _progresso(nome, fracao):
                barra.progress((ordem[nome] + fracao) / total, text=f"Classificando com {nome}...")

            try:
                resultados, estatisticas = classificar_com_modelos(df_base.head(int(n)), clientes,
                                                                   tamanho_lote, _progresso)
            except ErroAPI as erro:
                barra.empty()
                st.error(str(erro))
                st.stop()
            barra.empty()
            st.session_state["comparacao"] = {"resultados": resultados, "estatisticas": estatisticas,
                                              "nomes": {p: clientes[p].nome for p in clientes}}

        comp = st.session_state.get("comparacao")
        if comp:
            resultados = comp["resultados"]
            for nome, stats in comp["estatisticas"].items():
                falhas = (resultados[nome]["status"] == "erro").sum()
                aviso = f" · {falhas} sem classificação" if falhas else ""
                st.caption(f"{comp['nomes'][nome]}: {stats.chamadas} chamadas, {stats.segundos:.0f} s{aviso}"
                           + (f" · {stats.interrompido}" if stats.interrompido else ""))

            k = concordancia(resultados)
            m1, m2 = st.columns(2)
            m1.metric("Avaliações comparadas", k["comparadas"])
            m2.metric("Todos os modelos concordam no sentimento",
                      f"{k['todas_iguais']} ({k['todas_iguais'] / max(1, k['comparadas']):.0%})")

            g1, g2 = st.columns(2)
            g1.plotly_chart(grafico_concordancia(k["sentimento"], "Concordância de sentimento"),
                            width="stretch")
            g2.plotly_chart(grafico_concordancia(k["temas"], "Concordância de temas (Jaccard)"),
                            width="stretch")

            st.markdown("**Avaliações em que os modelos discordam.** Costumam ser as ambíguas: ironia, "
                        "elogio misturado com crítica, texto curto.")
            st.dataframe(k["divergentes"], hide_index=True, width="stretch")
            st.download_button("Baixar comparação (Excel)",
                               para_excel(k["divergentes"], "Divergências"), "comparacao_modelos.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.divider()
            st.markdown("**Acerto contra o gabarito do grupo (opcional).** Envie a planilha de rotulagem "
                        "preenchida das mesmas avaliações; os ids precisam ser os mesmos.")
            gabarito_arq = st.file_uploader("Gabarito (.xlsx ou .csv)", type=["xlsx", "csv"])
            if gabarito_arq is not None:
                try:
                    gabarito = carregar_gabarito(gabarito_arq)
                    notas = acuracia_por_modelo(resultados, gabarito)
                except (ValueError, KeyError) as erro:
                    st.error(f"Não foi possível comparar com o gabarito: {erro}")
                    st.stop()
                st.dataframe(notas.style.format({"acuracia": "{:.0%}", "f1_macro": "{:.2f}",
                                                 "kappa": "{:.2f}", "recall_negativo": "{:.0%}",
                                                 "jaccard_temas": "{:.2f}"}),
                             hide_index=True, width="stretch")
                st.caption("Kappa: <0,4 fraco · 0,4–0,6 moderado · 0,6–0,8 substancial · >0,8 quase "
                           "perfeito (Landis & Koch).")

                detalhe = st.selectbox("Ver detalhes de um modelo", list(resultados))
                m = calcular_metricas(gabarito, resultados[detalhe])
                v1, v2 = st.columns(2)
                v1.plotly_chart(grafico_matriz_confusao(m["matriz_confusao"]), width="stretch")
                v2.markdown("**Por classe de sentimento**")
                v2.dataframe(m["por_classe"].round(2), hide_index=True, width="stretch")
                erros = tabela_de_erros(m)
                st.markdown("Casos em que o modelo discordou do grupo (causas sugeridas automaticamente):")
                st.dataframe(erros, hide_index=True, width="stretch")
                st.download_button("Baixar erros (Excel)", para_excel(erros, "Erros da IA"),
                                   f"erros_{detalhe}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
