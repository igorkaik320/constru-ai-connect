import os
import pandas as pd
from jinja2 import Template
import plotly.express as px
import plotly.io as pio
import openai

def gerar_apresentacao_gamma(df: pd.DataFrame, dre: dict, titulo="Relatório Financeiro — Constru.IA") -> str:
    """Gera relatório visual tipo Gamma (HTML interativo com IA e gráficos)."""
    try:
        # === KPIs principais ===
        receitas = dre.get("receitas", "R$ 0,00")
        despesas = dre.get("despesas", "R$ 0,00")
        lucro = dre.get("lucro", "R$ 0,00")

        # === Gráfico principal ===
        if "centro_custo" in df.columns and not df["centro_custo"].isnull().all():
            graf = px.bar(
                df.groupby("centro_custo")["valor_total"].sum().reset_index().sort_values("valor_total", ascending=False),
                x="centro_custo",
                y="valor_total",
                title="Gastos por Centro de Custo",
                color="valor_total",
                color_continuous_scale="Blues",
            )
        else:
            graf = px.bar(
                df.groupby("fornecedor")["valor_total"].sum().reset_index().sort_values("valor_total", ascending=False),
                x="fornecedor",
                y="valor_total",
                title="Gastos por Fornecedor",
                color="valor_total",
                color_continuous_scale="Blues",
            )
        graf.update_layout(
            xaxis_title="", yaxis_title="Valor Total (R$)",
            template="plotly_white", title_x=0.5
        )
        graf_html = pio.to_html(graf, full_html=False, include_plotlyjs="cdn")

        # === Geração de análise via IA ===
        analise_texto = ""
        try:
            prompt = f"""
            Gere uma análise em até 3 parágrafos, de forma consultiva e objetiva,
            com base nesses dados financeiros:
            - Receitas: {receitas}
            - Despesas: {despesas}
            - Lucro: {lucro}
            Aponte possíveis causas, tendências e oportunidades de otimização.
            """
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um analista financeiro especializado em construtoras."},
                    {"role": "user", "content": prompt},
                ],
            )
            analise_texto = resp.choices[0].message.content.strip()
        except Exception as e:
            analise_texto = f"[⚠️ Erro ao gerar análise IA: {e}]"

        # === Template HTML estilizado ===
        html_template = Template("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ titulo }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', sans-serif;
                    margin: 40px;
                    background: #f8faff;
                    color: #222;
                }
                h1 { color: #003366; text-align: center; }
                .kpis { display: flex; justify-content: center; gap: 20px; margin-top: 30px; }
                .kpi {
                    background: white; border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    padding: 20px; width: 25%; text-align: center;
                }
                .kpi h3 { color: #0050a0; margin-bottom: 10px; }
                .kpi h2 { color: #004080; margin: 0; font-size: 1.6em; }
                .grafico, .analise {
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    padding: 25px;
                    margin-top: 40px;
                }
                .analise h3 { color: #004080; }
                .footer { text-align: center; margin-top: 60px; font-size: 0.9em; color: #888; }
            </style>
        </head>
        <body>
            <h1>{{ titulo }}</h1>
            <div class="kpis">
                <div class="kpi"><h3>💵 Receitas</h3><h2>{{ receitas }}</h2></div>
                <div class="kpi"><h3>💸 Despesas</h3><h2>{{ despesas }}</h2></div>
                <div class="kpi"><h3>📈 Lucro</h3><h2>{{ lucro }}</h2></div>
            </div>

            <div class="grafico">{{ grafico | safe }}</div>

            <div class="analise">
                <h3>🔎 Análise Gerada pela IA</h3>
                <p>{{ analise }}</p>
            </div>

            <div class="footer">
                Relatório gerado automaticamente via Constru.IA — Integração com Sienge.
            </div>
        </body>
        </html>
        """)

        return html_template.render(
            titulo=titulo,
            receitas=receitas,
            despesas=despesas,
            lucro=lucro,
            grafico=graf_html,
            analise=analise_texto,
        )

    except Exception as e:
        return f"<h1>Erro ao gerar relatório Gamma</h1><p>{e}</p>"
