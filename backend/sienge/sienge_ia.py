# sienge/sienge_ia.py
import logging
from openai import OpenAI
import pandas as pd

logging.warning("🤖 Rodando módulo sienge_ia.py (análises automáticas de dados financeiros)")

# ============================================================
# 🔐 CLIENTE OPENAI
# ============================================================
# ⚠️ Certifique-se de ter a variável OPENAI_API_KEY configurada
# no ambiente (no Render: "Environment Variables").
client = OpenAI()

# ============================================================
# 🧠 FUNÇÃO PRINCIPAL DE ANÁLISE
# ============================================================
def gerar_analise_financeira(titulo: str, dados: pd.DataFrame) -> str:
    """
    Gera uma análise executiva dos dados financeiros (receitas, despesas, obras, fornecedores, etc.)
    usando o modelo GPT.
    """
    try:
        if dados.empty:
            return "⚠️ Nenhum dado encontrado para análise."

        amostra = dados.head(25).to_markdown(index=False)
        total = len(dados)

        prompt = f"""
        Você é um analista financeiro especialista no setor da construção civil.
        Analise o relatório abaixo e gere uma análise gerencial detalhada e clara.

        **Instruções:**
        - Identifique tendências de receitas e despesas.
        - Destaque obras, fornecedores ou centros de custo com maiores gastos.
        - Detecte possíveis anomalias ou oportunidades de otimização.
        - Termine com um resumo executivo em linguagem de negócio.

        **Relatório:**
        - Título: {titulo}
        - Registros: {total}
        - Amostra:
        {amostra}
        """

        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um consultor financeiro especializado em construção civil."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=900,
        )

        return resposta.choices[0].message.content

    except Exception as e:
        logging.exception("Erro ao gerar análise financeira:")
        return f"❌ Erro ao gerar análise financeira: {e}"
