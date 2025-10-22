# sienge/sienge_ia.py
import logging
from openai import OpenAI
import pandas as pd

logging.warning("🤖 Rodando módulo sienge_ia.py (análises automáticas de dados financeiros)")

# ⚠️ Configure OPENAI_API_KEY no Render
client = OpenAI()

def gerar_analise_financeira(titulo: str, dados: pd.DataFrame) -> str:
    """Gera uma análise executiva com base no DataFrame de despesas/receitas."""
    try:
        if dados is None or len(dados) == 0:
            return "⚠️ Nenhum dado encontrado para análise."

        # amostra compacta para contexto
        preview = dados.head(40).to_markdown(index=False)

        prompt = f"""
Você é um analista financeiro especialista em construção civil.
Analise os dados a seguir e produza:
1) Principais destaques (receitas, despesas, lucros).
2) Obras/centros/fornecedores de maior impacto.
3) Alertas de risco ou anomalias (variações, concentração, sazonalidade).
4) Recomendações práticas (redução de custos, renegociação, priorização de obras).
Responda em formato executivo, com bullet points e linguagem simples.

Título: {titulo}
Amostra (até 40 linhas):
{preview}
        """

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um consultor financeiro sênior para construção civil."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=900,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.exception("Erro na IA:")
        return f"❌ Erro ao gerar análise financeira: {e}"
