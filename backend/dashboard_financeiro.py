import streamlit as st
import pandas as pd
import plotly.express as px
from sienge.sienge_financeiro import gerar_relatorio_json
from sienge.sienge_ia import gerar_analise_financeira

st.set_page_config(page_title="Constru.IA Financeiro", page_icon="💼", layout="wide")

st.title("💼 Dashboard Financeiro Inteligente — Constru.IA")
st.caption("📊 Dados via API Sienge • 💡 IA integrada para análises e apresentações automáticas")

col1, col2, col3 = st.columns(3)
inicio = col1.date_input("Início", pd.Timestamp.today() - pd.Timedelta(days=365))
fim = col2.date_input("Fim", pd.Timestamp.today())
enterprise_id = col3.text_input("Enterprise ID (opcional)", "")

params = {"startDate": str(inicio), "endDate": str(fim)}
if enterprise_id.strip():
    params["enterpriseId"] = enterprise_id.strip()

with st.spinner("🔄 Buscando dados financeiros..."):
    relatorio = gerar_relatorio_json(**params)

df = pd.DataFrame(relatorio.get("todas_despesas", []))
dre = relatorio.get("dre", {}).get("formatado", {})

if df.empty:
    st.warning("⚠️ Nenhuma despesa encontrada para o período/empresa selecionado.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("💵 Receitas", dre.get("receitas", "R$ 0,00"))
c2.metric("💸 Despesas", dre.get("despesas", "R$ 0,00"))
c3.metric("📈 Lucro", dre.get("lucro", "R$ 0,00"))

st.divider()
st.subheader("📊 Distribuição de Gastos")

aba = st.radio(
    "Visualizar por:",
    ["empresa", "fornecedor", "centro_custo", "conta_financeira", "obra", "status"],
    horizontal=True
)

if aba not in df.columns:
    st.error(f"⚠️ A coluna '{aba}' não foi encontrada nos dados.")
else:
    df_plot = df.groupby(aba)["valor_total"].sum().reset_index()
    fig = px.bar(
        df_plot,
        x=aba,
        y="valor_total",
        text_auto=".2s",
        title=f"Gastos por {aba.capitalize()}",
        color="valor_total",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("📋 Dados Detalhados")
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("🎬 Geração Automática de Apresentação (Estilo Gamma)")

if st.button("🧠 Gerar Apresentação Interativa (IA + Gráficos)"):
    with st.spinner("Gerando slides e narrativa..."):
        analise = gerar_analise_financeira("Apresentação Financeira", df)
        st.markdown(analise)

st.divider()
st.caption("🚀 Constru.IA — Relatórios Inteligentes via API Sienge + OpenAI")
