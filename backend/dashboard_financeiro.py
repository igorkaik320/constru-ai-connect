import os
import pandas as pd
import plotly.express as px
from datetime import datetime
from sienge.sienge_ia import gerar_analise_financeira


def gerar_relatorio_gamma(df: pd.DataFrame, dre: dict, filtros: dict, user_email: str):
    """
    Gera 5 páginas HTML (Visão Geral, Obras, Centros de Custo, Fornecedores, Análise IA)
    com visual dark premium, estilo Gamma + Power BI.
    """
    os.makedirs("static", exist_ok=True)
    base = "https://constru-ai-connect.onrender.com/static"

    # === Função auxiliar para converter valores monetários ===
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

    # === Estilo global ===
    estilo = """
    <style>
        body {background-color:#0F172A; color:#F1F5F9; font-family:'Poppins',sans-serif; margin:0;}
        h1,h2,h3 {color:#00E0A0; text-align:center;}
        .card {background:#1E293B; border-radius:16px; padding:20px; margin:10px; text-align:center; box-shadow:0 0 15px rgba(0,0,0,.3);}
        .kpi {font-size:28px; font-weight:bold;}
        .menu {background:#1E293B; padding:10px; text-align:center; position:sticky; top:0;}
        .menu a {color:#F1F5F9; margin:0 15px; text-decoration:none; font-weight:bold;}
        .menu a:hover {color:#00E0A0;}
        .container {width:90%; margin:auto;}
    </style>
    """

    # === Menu de navegação ===
    menu_html = f"""
    <div class='menu'>
        <a href='relatorio_gamma_{user_email}_visao_geral.html'>Visão Geral</a>
        <a href='relatorio_gamma_{user_email}_obras.html'>Obras</a>
        <a href='relatorio_gamma_{user_email}_centros.html'>Centros de Custo</a>
        <a href='relatorio_gamma_{user_email}_fornecedores.html'>Fornecedores</a>
        <a href='relatorio_gamma_{user_email}_analise.html'>Análise IA</a>
    </div>
    """

    # === KPIs ===
    kpis = f"""
    <div class='container'>
        <div style='display:flex; justify-content:space-around; flex-wrap:wrap;'>
            <div class='card'><h3>💰 Receitas</h3><div class='kpi'>R$ {receitas:,.2f}</div></div>
            <div class='card'><h3>💸 Despesas</h3><div class='kpi'>R$ {despesas:,.2f}</div></div>
            <div class='card'><h3>📈 Lucro</h3><div class='kpi'>R$ {lucro:,.2f}</div></div>
            <div class='card'><h3>📊 Margem</h3><div class='kpi'>{margem:.2f}%</div></div>
        </div>
    </div>
    """

    # === VISÃO GERAL ===
    if 'data_emissao' in df.columns:
        df['data_emissao'] = pd.to_datetime(df['data_emissao'], errors='coerce')
        df['mes'] = df['data_emissao'].dt.strftime('%b/%Y')
        graf_linha = px.line(
            df.groupby('mes')['valor_total'].sum().reset_index(),
            x='mes', y='valor_total',
            title='📆 Evolução Mensal de Gastos',
            template='plotly_dark', markers=True
        )
        graf_linha_html = graf_linha.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_linha_html = "<p>Sem dados de data para gerar evolução mensal.</p>"

    graf_tipo = px.pie(
        df, names='tipo_lancamento', values='valor_total',
        title='📑 Distribuição por Tipo de Lançamento',
        template='plotly_dark'
    )
    graf_tipo_html = graf_tipo.to_html(full_html=False, include_plotlyjs='cdn')

    html_visao = f"""
    <html><head>{estilo}</head><body>{menu_html}
    <h1>Relatório Financeiro — Constru.IA</h1>{kpis}
    <div class='container'>{graf_linha_html}{graf_tipo_html}</div></body></html>
    """

    # === OBRAS ===
    if 'obra' in df.columns:
        top_obras = df.groupby('obra')['valor_total'].sum().reset_index().sort_values('valor_total', ascending=False).head(10)
        graf_obras = px.bar(top_obras, x='obra', y='valor_total', title='🏗️ Top 10 Obras por Custo', template='plotly_dark')
        graf_obras_html = graf_obras.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_obras_html = "<p>Sem dados de obra disponíveis.</p>"

    html_obras = f"""
    <html><head>{estilo}</head><body>{menu_html}<h1>🏗️ Obras</h1>
    <div class='container'>{graf_obras_html}</div></body></html>
    """

    # === CENTROS DE CUSTO ===
    if 'centro_custo' in df.columns:
        top_cc = df.groupby('centro_custo')['valor_total'].sum().reset_index().sort_values('valor_total', ascending=False).head(10)
        graf_cc = px.bar(top_cc, x='valor_total', y='centro_custo', orientation='h',
                         title='📂 Top 10 Centros de Custo', template='plotly_dark')
        graf_cc_html = graf_cc.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_cc_html = "<p>Sem dados de centro de custo.</p>"

    html_cc = f"""
    <html><head>{estilo}</head><body>{menu_html}<h1>📂 Centros de Custo</h1>
    <div class='container'>{graf_cc_html}</div></body></html>
    """

    # === FORNECEDORES ===
    if 'fornecedor' in df.columns:
        top_forn = df.groupby('fornecedor')['valor_total'].sum().reset_index().sort_values('valor_total', ascending=False).head(10)
        graf_forn = px.bar(top_forn, x='fornecedor', y='valor_total', title='💼 Top 10 Fornecedores', template='plotly_dark')
        graf_forn_html = graf_forn.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graf_forn_html = "<p>Sem dados de fornecedor disponíveis.</p>"

    html_forn = f"""
    <html><head>{estilo}</head><body>{menu_html}<h1>💼 Fornecedores</h1>
    <div class='container'>{graf_forn_html}</div></body></html>
    """

    # === ANÁLISE IA ===
    texto_ia = gerar_analise_financeira("Relatório Financeiro", df)
    html_ia = f"""
    <html><head>{estilo}</head><body>{menu_html}<h1>🧠 Análise Automática</h1>
    <div class='container'><div class='card'><p>{texto_ia}</p></div></div></body></html>
    """

    # === SALVAR TODAS AS PÁGINAS ===
    paginas = {
        f"static/relatorio_gamma_{user_email}_visao_geral.html": html_visao,
        f"static/relatorio_gamma_{user_email}_obras.html": html_obras,
        f"static/relatorio_gamma_{user_email}_centros.html": html_cc,
        f"static/relatorio_gamma_{user_email}_fornecedores.html": html_forn,
        f"static/relatorio_gamma_{user_email}_analise.html": html_ia,
    }

    for path, conteudo in paginas.items():
        with open(path, 'w', encoding='utf-8') as f:
            f.write(conteudo)

    return f"{base}/relatorio_gamma_{user_email}_visao_geral.html"
