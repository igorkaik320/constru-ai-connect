import os
import pandas as pd
import plotly.express as px
from datetime import datetime
from sienge.sienge_ia import gerar_analise_financeira


def gerar_relatorio_gamma(df: pd.DataFrame, dre: dict, filtros: dict, user_email: str):
    """
    Relatório financeiro estilo Gamma em uma única página:
    - Visual escuro (dark mode amarelo)
    - Fluxo de caixa mensal
    - Gastos por plano de contas, obra e fornecedor
    - Análise automática IA
    """
    os.makedirs("static", exist_ok=True)
    base = "https://constru-ai-connect.onrender.com/static"

    # === Função auxiliar ===
    def parse_money(valor):
        if isinstance(valor, (int, float)):
            return float(valor)
        try:
            return float(str(valor).replace("R$", "").replace(".", "").replace(",", ".").strip())
        except:
            return 0.0

    # === Conversão de valores DRE ===
    receitas = parse_money(dre.get('receitas', 0))
    despesas = parse_money(dre.get('despesas', 0))
    lucro = receitas - despesas
    margem = 0 if receitas == 0 else round((lucro / receitas) * 100, 2)

    # === Estilo visual ===
    estilo = """
    <style>
        body {background-color:#0D0D0D; color:#F1F5F9; font-family:'Poppins',sans-serif; margin:0;}
        h1,h2,h3 {color:#FACC15; text-align:center;}
        .card {background:#1E1E1E; border-radius:16px; padding:20px; margin:20px auto; max-width:1200px; box-shadow:0 0 20px rgba(250,204,21,0.15);}
        .kpi {font-size:28px; font-weight:bold; color:#FACC15;}
        .container {width:90%; margin:auto;}
        .grafico {margin-top:30px;}
        p {font-size:16px; line-height:1.6; color:#E2E8F0;}
        .analise {background:#111827; border-left:6px solid #FACC15; padding:20px; border-radius:10px; margin-top:20px;}
    </style>
    """

    # === KPIs principais ===
    kpis_html = f"""
    <div class='card'>
        <h1>💼 Relatório Financeiro — Constru.IA</h1>
        <div style='display:flex; justify-content:space-around; flex-wrap:wrap; margin-top:20px;'>
            <div><h3>💰 Receitas</h3><div class='kpi'>R$ {receitas:,.2f}</div></div>
            <div><h3>💸 Despesas</h3><div class='kpi'>R$ {despesas:,.2f}</div></div>
            <div><h3>📈 Lucro</h3><div class='kpi'>R$ {lucro:,.2f}</div></div>
            <div><h3>📊 Margem</h3><div class='kpi'>{margem:.2f}%</div></div>
        </div>
    </div>
    """

    # === Fluxo de Caixa Mensal ===
    if 'data_vencimento' in df.columns:
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'], errors='coerce')
        df['mes'] = df['data_vencimento'].dt.to_period('M').astype(str)

        despesas_mensais = df.groupby('mes')['valor_total'].sum().reset_index()
        despesas_mensais.rename(columns={'valor_total': 'despesas'}, inplace=True)

        fluxo_df = despesas_mensais.copy()
        fluxo_df['saldo_acumulado'] = fluxo_df['despesas'].cumsum()

        graf_fluxo = px.line(
            fluxo_df,
            x='mes', y='saldo_acumulado',
            title='📆 Fluxo de Caixa Mensal (Acumulado)',
            template='plotly_dark', markers=True,
        )
        graf_fluxo.update_traces(line_color="#FACC15", fill='tozeroy')
        graf_fluxo_html = graf_fluxo.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_fluxo_html = "<p>Sem dados de data para gerar fluxo de caixa.</p>"

    # === Análise por Plano de Contas ===
    contas_col = "apropriacoes_financeiras"
    plano_data = []
    for _, row in df.iterrows():
        aprop = row.get(contas_col, [])
        for a in aprop:
            plano_data.append({
                "categoria": a.get("categoria", "N/A"),
                "percentual": a.get("percentual", 0),
                "valor": row["valor_total"] * (a.get("percentual", 0) / 100)
            })
    plano_df = pd.DataFrame(plano_data)

    if not plano_df.empty:
        graf_plano = px.bar(
            plano_df.groupby("categoria")["valor"].sum().reset_index().sort_values("valor", ascending=False).head(15),
            x="valor", y="categoria", orientation="h",
            title="🏦 Gastos por Plano de Contas (Apropriações Financeiras)",
            template="plotly_dark", color_discrete_sequence=["#FACC15"]
        )
        graf_plano_html = graf_plano.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_plano_html = "<p>Sem apropriações financeiras disponíveis.</p>"

    # === Obras ===
    if 'obra' in df.columns:
        top_obras = df.groupby('obra')['valor_total'].sum().reset_index().sort_values('valor_total', ascending=False).head(10)
        graf_obras = px.bar(top_obras, x='valor_total', y='obra', orientation='h',
                            title='🏗️ Top 10 Obras por Custo', template='plotly_dark',
                            color_discrete_sequence=['#FACC15'])
        graf_obras_html = graf_obras.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_obras_html = "<p>Sem dados de obras disponíveis.</p>"

    # === Fornecedores ===
    if 'fornecedor' in df.columns:
        top_forn = df.groupby('fornecedor')['valor_total'].sum().reset_index().sort_values('valor_total', ascending=False).head(10)
        graf_forn = px.bar(top_forn, x='valor_total', y='fornecedor', orientation='h',
                           title='🤝 Top 10 Fornecedores por Valor Pago', template='plotly_dark',
                           color_discrete_sequence=['#FACC15'])
        graf_forn_html = graf_forn.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_forn_html = "<p>Sem dados de fornecedores.</p>"

    # === IA: Análise automática ===
    texto_ia = gerar_analise_financeira("Relatório Financeiro", df)

    # === HTML Final ===
    html = f"""
    <html><head><meta charset='utf-8'>{estilo}</head><body>
    {kpis_html}
    <div class='card grafico'>{graf_fluxo_html}</div>
    <div class='card grafico'>{graf_plano_html}</div>
    <div class='card grafico'>{graf_obras_html}</div>
    <div class='card grafico'>{graf_forn_html}</div>
    <div class='card'>
        <h2>🧠 Análise Inteligente</h2>
        <div class='analise'><p>{texto_ia}</p></div>
    </div>
    </body></html>
    """

    # === Salvar arquivo HTML ===
    path = f"static/relatorio_gamma_{user_email}_financeiro.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return f"{base}/relatorio_gamma_{user_email}_financeiro.html"
