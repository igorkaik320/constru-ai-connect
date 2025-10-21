# -*- coding: utf-8 -*-
import io
import time
import pandas as pd
import streamlit as st
import plotly.express as px

# Importa seu módulo
from sienge.sienge_financeiro import (
    resumo_financeiro_dre,
    fluxo_caixa,
    gastos_por_obra,
    gastos_por_centro_custo,
    gastos_por_fornecedor,
)

st.set_page_config(
    page_title="Financeiro • Constru.IA",
    page_icon="💼",
    layout="wide",
)

# =========================
# Sidebar (filtros)
# =========================
st.sidebar.title("⚙️ Filtros")
dias_fluxo = st.sidebar.slider("Período do fluxo de caixa (dias)", 7, 180, 30, step=1)
dias_analises = st.sidebar.slider("Período de análises (dias)", 30, 180, 60, step=5)

st.sidebar.markdown("---")
st.sidebar.caption("As análises usam dados do Sienge via API.\nOs períodos são aplicados nas coletas/estimativas.")

# =========================
# Header
# =========================
st.title("💼 Dashboard Financeiro — Constru.IA")

colA, colB = st.columns([1, 3])
with colA:
    if st.button("🔄 Atualizar agora"):
        st.experimental_rerun()
with colB:
    st.write("")

# =========================
# Coleta dos dados
# =========================
with st.spinner("Buscando dados no Sienge…"):
    # DRE (usa 30 dias internos ao módulo)
    dre = resumo_financeiro_dre()

    # Fluxo de caixa
    fluxo = fluxo_caixa(dias=dias_fluxo)
    df_fluxo = pd.DataFrame(fluxo) if fluxo else pd.DataFrame(columns=["data", "valor", "tipo"])

    # Gastos por Obra
    obras = gastos_por_obra()
    df_obras = pd.DataFrame(obras) if obras else pd.DataFrame(columns=["empresa", "obra", "valor"])

    # Gastos por Centro de Custo
    centros = gastos_por_centro_custo()
    df_cc = pd.DataFrame(centros) if centros else pd.DataFrame(columns=["centro_custo", "valor"])

    # Gastos por Fornecedor
    fornecedores = gastos_por_fornecedor()
    df_forn = pd.DataFrame(fornecedores) if fornecedores else pd.DataFrame(columns=["fornecedor", "valor"])

time.sleep(0.1)

# =========================
# Cards do DRE
# =========================
st.subheader("📊 DRE — Últimos 30 dias")
c1, c2, c3, c4 = st.columns(4)

periodo_txt = f"{dre['periodo']['inicio']} a {dre['periodo']['fim']}"
with c1:
    st.metric("Período", periodo_txt)
with c2:
    st.metric("Receitas", dre["formatado"]["receitas"])
with c3:
    st.metric("Despesas", dre["formatado"]["despesas"])
with c4:
    lucro = dre["lucro"]
    delta = "positivo" if lucro >= 0 else "negativo"
    st.metric("Lucro", dre["formatado"]["lucro"], delta=None)

st.markdown("---")

# =========================
# Fluxo de Caixa (linha)
# =========================
st.subheader("📈 Fluxo de Caixa (Saídas por dia)")
if df_fluxo.empty:
    st.info("Sem dados de fluxo no período selecionado.")
else:
    df_fluxo_plot = df_fluxo.copy()
    df_fluxo_plot["data"] = pd.to_datetime(df_fluxo_plot["data"])
    df_fluxo_plot = df_fluxo_plot.sort_values("data")
    fig_fluxo = px.line(
        df_fluxo_plot, x="data", y="valor",
        markers=True, title=f"Saídas diárias — últimos {dias_fluxo} dias"
    )
    fig_fluxo.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_fluxo, use_container_width=True)
    st.dataframe(df_fluxo_plot.rename(columns={"data": "Data", "valor": "Valor (R$)"}), use_container_width=True)

st.markdown("---")

# =========================
# Gastos por Obra (barras)
# =========================
st.subheader("🏗️ Gastos por Obra")
if df_obras.empty:
    st.info("Sem dados de obras no período.")
else:
    # filtros opcionais
    empresas = sorted(df_obras["empresa"].dropna().unique().tolist())
    empresa_sel = st.multiselect("Filtrar por empresa", empresas, default=empresas[:1] if empresas else [])
    df_obras_f = df_obras.copy()
    if empresa_sel:
        df_obras_f = df_obras_f[df_obras_f["empresa"].isin(empresa_sel)]
    # top obras
    df_top_obras = (
        df_obras_f.groupby(["empresa", "obra"])["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
        .head(15)
    )
    fig_obras = px.bar(
        df_top_obras,
        x="obra", y="valor", color="empresa",
        title="Top 15 obras por gasto (estimado pela apropriação)",
        text_auto=".2s"
    )
    fig_obras.update_layout(height=380, xaxis_tickangle=-20, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_obras, use_container_width=True)
    st.dataframe(df_top_obras.rename(columns={"empresa": "Empresa", "obra": "Obra", "valor": "Valor (R$)"}), use_container_width=True)

st.markdown("---")

# =========================
# Gastos por Centro de Custo (barras)
# =========================
st.subheader("🏢 Gastos por Centro de Custo")
if df_cc.empty:
    st.info("Sem dados de centros de custo no período.")
else:
    df_cc_plot = df_cc.sort_values("valor", ascending=False).head(20)
    fig_cc = px.bar(
        df_cc_plot, x="centro_custo", y="valor",
        title="Top 20 centros de custo (gastos)",
        text_auto=".2s"
    )
    fig_cc.update_layout(height=380, xaxis_tickangle=-20, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_cc, use_container_width=True)
    st.dataframe(df_cc_plot.rename(columns={"centro_custo": "Centro de Custo", "valor": "Valor (R$)"}), use_container_width=True)

st.markdown("---")

# =========================
# Gastos por Fornecedor (barras)
# =========================
st.subheader("👥 Gastos por Fornecedor")
if df_forn.empty:
    st.info("Sem dados de fornecedores no período.")
else:
    df_forn_plot = df_forn.sort_values("valor", ascending=False).head(20)
    fig_forn = px.bar(
        df_forn_plot, x="fornecedor", y="valor",
        title="Top 20 fornecedores (gastos)",
        text_auto=".2s"
    )
    fig_forn.update_layout(height=380, xaxis_tickangle=-20, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_forn, use_container_width=True)
    st.dataframe(df_forn_plot.rename(columns={"fornecedor": "Fornecedor", "valor": "Valor (R$)"}), use_container_width=True)

st.markdown("---")

# =========================
# Exportação Excel (todas as abas)
# =========================
st.subheader("⬇️ Exportar Relatório (Excel)")
def to_excel_bytes() -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # DRE em uma aba
        df_dre = pd.DataFrame([{
            "Período (início)": dre["periodo"]["inicio"],
            "Período (fim)": dre["periodo"]["fim"],
            "Receitas": dre["receitas"],
            "Despesas": dre["despesas"],
            "Lucro": dre["lucro"],
        }])
        df_dre.to_excel(writer, sheet_name="DRE", index=False)

        # Fluxo
        (pd.DataFrame(df_fluxo)).to_excel(writer, sheet_name="Fluxo de Caixa", index=False)
        # Obras
        (pd.DataFrame(df_obras)).to_excel(writer, sheet_name="Obras", index=False)
        # Centros de Custo
        (pd.DataFrame(df_cc)).to_excel(writer, sheet_name="Centros de Custo", index=False)
        # Fornecedores
        (pd.DataFrame(df_forn)).to_excel(writer, sheet_name="Fornecedores", index=False)

    return output.getvalue()

excel_bytes = to_excel_bytes()
st.download_button(
    label="📥 Baixar Excel (DRE + Fluxo + Obras + CC + Forn.)",
    data=excel_bytes,
    file_name="relatorio_financeiro_construIA.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
