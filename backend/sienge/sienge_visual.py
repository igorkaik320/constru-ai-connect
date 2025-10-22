import pandas as pd
import plotly.express as px
import streamlit as st
from sienge.sienge_ia import gerar_analise_financeira


# ============================================================
# 🎨 FUNÇÃO PRINCIPAL — GERA SLIDES AUTOMÁTICOS
# ============================================================
def gerar_slides_financeiros(df: pd.DataFrame):
    """
    Gera visualizações e análises automáticas a partir do DataFrame financeiro.
    Cada seção (slide) exibe um gráfico e a explicação da IA.
    """

    if df.empty:
        st.warning("Nenhum dado encontrado para gerar slides.")
        return

    st.header("📊 Apresentação Interativa — Inteligência Financeira")

    # === SLIDE 1 — GASTOS POR OBRA ===
    if "obra" in df.columns:
        st.subheader("🏗️ Gastos por Obra")
        obra_data = df.groupby("obra")["valor_total"].sum().reset_index()
        fig = px.bar(obra_data, x="obra", y="valor_total", text_auto=".2s", title="Total de Gastos por Obra")
        st.plotly_chart(fig, use_container_width=True)

        with st.spinner("Gerando análise da IA..."):
            texto = gerar_analise_financeira("Gastos por Obra", obra_data)
            st.markdown(texto)

        st.divider()

    # === SLIDE 2 — GASTOS POR CENTRO DE CUSTO ===
    if "centro_custo" in df.columns:
        st.subheader("🏢 Gastos por Centro de Custo")
        cc_data = df.groupby("centro_custo")["valor_total"].sum().reset_index()
        fig = px.pie(cc_data, values="valor_total", names="centro_custo", title="Distribuição por Centro de Custo")
        st.plotly_chart(fig, use_container_width=True)

        with st.spinner("Gerando análise da IA..."):
            texto = gerar_analise_financeira("Gastos por Centro de Custo", cc_data)
            st.markdown(texto)

        st.divider()

    # === SLIDE 3 — GASTOS POR FORNECEDOR ===
    if "fornecedor" in df.columns:
        st.subheader("📦 Gastos por Fornecedor")
        forn_data = df.groupby("fornecedor")["valor_total"].sum().reset_index()
        forn_data = forn_data.sort_values("valor_total", ascending=False).head(10)
        fig = px.bar(forn_data, x="fornecedor", y="valor_total", text_auto=".2s", title="Top 10 Fornecedores")
        st.plotly_chart(fig, use_container_width=True)

        with st.spinner("Gerando análise da IA..."):
            texto = gerar_analise_financeira("Top Fornecedores", forn_data)
            st.markdown(texto)

        st.divider()

    # === SLIDE 4 — STATUS DAS DESPESAS ===
    if "status" in df.columns:
        st.subheader("📋 Status Financeiro das Despesas")
        status_data = df.groupby("status")["valor_total"].sum().reset_index()
        fig = px.bar(status_data, x="status", y="valor_total", text_auto=".2s", title="Despesas por Status")
        st.plotly_chart(fig, use_container_width=True)

        with st.spinner("Gerando análise da IA..."):
            texto = gerar_analise_financeira("Status das Despesas", status_data)
            st.markdown(texto)

        st.divider()

    # === SLIDE FINAL ===
    st.success("🎉 Fim da apresentação — relatório completo gerado com sucesso!")
