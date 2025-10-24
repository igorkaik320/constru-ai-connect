import os
import pandas as pd
import plotly.express as px
from sienge.sienge_ia import gerar_analise_financeira

def gerar_relatorio_gamma(df: pd.DataFrame, dre: dict, filtros: dict, user_email: str):
    os.makedirs("static", exist_ok=True)
    base = "https://constru-ai-connect.onrender.com/static"

    def parse_money(v):
        try:
            return float(str(v).replace("R$", "").replace(".", "").replace(",", ".").strip())
        except:
            return 0.0

    receitas = parse_money(dre.get("receitas", 0))
    despesas = parse_money(dre.get("despesas", 0))
    lucro = receitas - despesas
    margem = 0 if receitas == 0 else round((lucro / receitas) * 100, 2)

    estilo = """
    <style>
        body {background-color:#0F172A; color:#E2E8F0; font-family:'Poppins',sans-serif; margin:0;}
        h1,h2 {color:#00E0A0; text-align:center;}
        .card {background:#1E293B; border-radius:18px; padding:25px; margin:20px auto; width:90%; box-shadow:0 0 25px rgba(0,0,0,.5);}
        .analise {background:#0F172A; border-left:4px solid #00E0A0; padding:10px; margin-top:15px;}
        .kpi {font-size:26px; font-weight:bold;}
    </style>
    """

    # === KPIs ===
    kpis = f"""
    <div class='card'>
        <h1>📊 Relatório Financeiro — Constru.IA</h1>
        <p class='kpi'>💰 Receitas: R$ {receitas:,.2f} | 💸 Despesas: R$ {despesas:,.2f} | 📈 Lucro: R$ {lucro:,.2f} | 📊 Margem: {margem:.2f}%</p>
    </div>
    """

    # === Filtro Empresa ===
    empresa_filtro = filtros.get("enterpriseId")
    if empresa_filtro:
        df = df[df["empresa"].astype(str).str.contains(str(empresa_filtro), na=False)]

    # === Gráfico Plano de Contas ===
    planos = []
    for row in df.itertuples():
        if row.apropriacoes_financeiras:
            for a in row.apropriacoes_financeiras:
                planos.append({"categoria": a["categoria"], "valor": row.valor_total * (a["percentual"] / 100)})
    plano_df = pd.DataFrame(planos) if planos else pd.DataFrame(columns=["categoria", "valor"])

    graf_plano = px.bar(plano_df.groupby("categoria")["valor"].sum().reset_index().sort_values("valor", ascending=True),
                        x="valor", y="categoria", orientation="h", title="🏦 Gastos por Plano de Contas",
                        template="plotly_dark", color_discrete_sequence=["#FACC15"], text="valor")
    graf_plano.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
    graf_plano_html = graf_plano.to_html(full_html=False, include_plotlyjs='cdn')
    texto_plano = gerar_analise_financeira("Análise do plano de contas", plano_df)

    # === Obras ===
    graf_obras = px.bar(df.groupby("obra")["valor_total"].sum().reset_index().sort_values("valor_total", ascending=True),
                        x="valor_total", y="obra", orientation="h", title="🏗️ Top 10 Obras por Custo",
                        template="plotly_dark", color_discrete_sequence=["#FACC15"], text="valor_total")
    graf_obras.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
    graf_obras_html = graf_obras.to_html(full_html=False, include_plotlyjs='cdn')
    texto_obras = gerar_analise_financeira("Análise das obras", df)

    # === Fornecedores ===
    graf_forn = px.bar(df.groupby("fornecedor")["valor_total"].sum().reset_index().sort_values("valor_total", ascending=True).head(15),
                       x="valor_total", y="fornecedor", orientation="h", title="💼 Top 10 Fornecedores por Valor Pago",
                       template="plotly_dark", color_discrete_sequence=["#FACC15"], text="valor_total")
    graf_forn.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
    graf_forn_html = graf_forn.to_html(full_html=False, include_plotlyjs='cdn')
    texto_forn = gerar_analise_financeira("Análise dos fornecedores", df)

    # === Análise Geral ===
    texto_geral = gerar_analise_financeira("Resumo geral da empresa", df)

    html = f"""
    <html><head>{estilo}</head><body>
    {kpis}
    <div class='card'>{graf_plano_html}<div class='analise'><p>{texto_plano}</p></div></div>
    <div class='card'>{graf_obras_html}<div class='analise'><p>{texto_obras}</p></div></div>
    <div class='card'>{graf_forn_html}<div class='analise'><p>{texto_forn}</p></div></div>
    <div class='card'><h2>🧠 Análise Geral</h2><div class='analise'><p>{texto_geral}</p></div></div>
    </body></html>
    """

    path = f"static/relatorio_gamma_{user_email}_financeiro.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return f"{base}/relatorio_gamma_{user_email}_financeiro.html"
