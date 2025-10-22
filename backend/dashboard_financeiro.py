import streamlit as st
import pandas as pd
import plotly.express as px
from sienge.sienge_financeiro import gerar_relatorio_json

st.set_page_config(page_title="Constru.IA Financeiro", page_icon="💼", layout="wide")

st.title("💼 Dashboard Financeiro Inteligente — Constru.IA")
st.caption("Dados via API Sienge • IA opcional via backend")

# Filtros (período e empresa)
colf1, colf2, colf3 = st.columns(3)
inicio = colf1.date_input("Início", pd.Timestamp.today() - pd.Timedelta(days=365))
fim = colf2.date_input("Fim", pd.Timestamp.today())
enterprise_id = colf3.text_input("Enterprise ID (opcional)", "")

params = {
    "startDate": str(inicio),
    "endDate": str(fim),
}
if enterprise_id.strip():
    params["enterpriseId"] = enterprise_id.strip()

with st.spinner("Buscando dados..."):
    relatorio = gerar_relatorio_json(**params)

df = pd.DataFrame(relatorio.get("todas_despesas", []))
dre = relatorio.get("dre", {}).get("formatado", {})

if df.empty:
    st.warning("Nenhuma despesa encontrada para o período/empresa.")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas", dre.get("receitas", "R$ 0,00"))
    c2.metric("Despesas", dre.get("despesas", "R$ 0,00"))
    c3.metric("Lucro", dre.get("lucro", "R$ 0,00"))

    st.divider()
    st.subheader("📈 Distribuição de Gastos")
    aba = st.radio("Visualizar por:", ["empresa", "fornecedor", "centro_custo", "conta_financeira", "obra", "status"], horizontal=True)
    df_plot = df.groupby(aba)["valor_total"].sum().reset_index()
    fig = px.bar(df_plot, x=aba, y="valor_total", text_auto=".2s", title=f"Gastos por {aba}")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.dataframe(df, use_container_width=True)
