import streamlit as st
import pandas as pd
import plotly.express as px
from sienge.sienge_financeiro import gerar_relatorio_json
from sienge.sienge_ia import gerar_analise_financeira

st.set_page_config(page_title="Constru.IA Financeiro", page_icon="💼", layout="wide")

st.title("💼 Dashboard Financeiro Inteligente — Constru.IA")
st.caption("Dados obtidos via API Sienge • Análise automática com IA")

with st.spinner("Buscando dados..."):
    relatorio = gerar_relatorio_json()
    df = pd.DataFrame(relatorio["todas_despesas"])

if df.empty:
    st.error("Nenhum dado encontrado.")
    st.stop()

# =======================
# KPI Cards
# =======================
col1, col2, col3 = st.columns(3)
col1.metric("Receitas", relatorio["dre"]["formatado"]["receitas"])
col2.metric("Despesas", relatorio["dre"]["formatado"]["despesas"])
col3.metric("Lucro", relatorio["dre"]["formatado"]["lucro"])

st.divider()

# =======================
# Gráficos
# =======================
st.subheader("📈 Distribuição de Gastos")
aba = st.radio("Visualizar por:", ["Empresa", "Fornecedor", "Conta Financeira", "Status"])

campo = {
    "Empresa": "empresa",
    "Fornecedor": "fornecedor",
    "Conta Financeira": "conta_financeira",
    "Status": "status"
}[aba]

df_plot = df.groupby(campo)["valor_total"].sum().reset_index()
fig = px.bar(df_plot, x=campo, y="valor_total", text_auto=".2s", title=f"Gastos por {aba}")
st.plotly_chart(fig, use_container_width=True)

# =======================
# Análise Automática com IA
# =======================
st.subheader("🤖 Análise Inteligente (OpenAI)")
if st.button("Gerar Análise Completa"):
    with st.spinner("Gerando análise com IA..."):
        analise = gerar_analise_financeira("Relatório Financeiro Completo", df)
        st.markdown(analise)

st.divider()
st.dataframe(df, use_container_width=True)
