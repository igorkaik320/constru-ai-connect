import streamlit as st
import pandas as pd
import plotly.express as px
from sienge.sienge_financeiro import gerar_relatorio_json
from sienge.sienge_visual import gerar_slides_financeiros
from sienge.sienge_apresentacao import gerar_apresentacao_ppt

# ============================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ============================================================
st.set_page_config(page_title="Constru.IA Financeiro", page_icon="💼", layout="wide")

st.title("💼 Dashboard Financeiro Inteligente — Constru.IA")
st.caption("📊 Dados via API Sienge • 💡 IA integrada para análises e apresentações automáticas")

# ============================================================
# 📅 FILTROS DE PERÍODO E EMPRESA
# ============================================================
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

# ============================================================
# 📦 COLETA DE DADOS
# ============================================================
with st.spinner("🔄 Buscando dados financeiros..."):
    relatorio = gerar_relatorio_json(**params)

df = pd.DataFrame(relatorio.get("todas_despesas", []))
dre = relatorio.get("dre", {}).get("formatado", {})

# ============================================================
# ⚠️ VALIDAÇÃO DE DADOS
# ============================================================
if df.empty:
    st.warning("Nenhuma despesa encontrada para o período/empresa selecionado.")
    st.stop()

# ============================================================
# 💰 INDICADORES GERAIS (KPI)
# ============================================================
c1, c2, c3 = st.columns(3)
c1.metric("Receitas", dre.get("receitas", "R$ 0,00"))
c2.metric("Despesas", dre.get("despesas", "R$ 0,00"))
c3.metric("Lucro", dre.get("lucro", "R$ 0,00"))

# ============================================================
# 📊 GRÁFICO INTERATIVO DE GASTOS
# ============================================================
st.divider()
st.subheader("📈 Distribuição de Gastos")

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

# ============================================================
# 📋 TABELA DETALHADA
# ============================================================
st.divider()
st.subheader("📋 Dados Detalhados")
st.dataframe(df, use_container_width=True)

# ============================================================
# 🎬 GERAÇÃO DE APRESENTAÇÃO
# ============================================================
st.divider()
st.subheader("🎬 Geração Automática de Apresentação (Estilo Gamma)")

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("🧠 Gerar Apresentação Interativa (IA + Gráficos)"):
        gerar_slides_financeiros(df)

with col_btn2:
    if st.button("💾 Exportar para PowerPoint (.pptx)"):
        with st.spinner("Gerando arquivo .pptx com gráficos e análises da IA..."):
            ppt = gerar_apresentacao_ppt(df, dre)
            st.download_button(
                "📥 Baixar Apresentação",
                data=ppt,
                file_name="Relatorio_Financeiro_ConstruIA.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

# ============================================================
# 🏁 RODAPÉ
# ============================================================
st.divider()
st.caption("🚀 Constru.IA — Relatórios Inteligentes via API Sienge + OpenAI")
