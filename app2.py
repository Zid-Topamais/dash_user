import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão segura
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url)

st.title("🚀 Ativação de Parceiros")
st.subheader("Novos parceiros registrados na última semana")

try:
    engine = get_engine()
    
    # Query que junta Usuário, Squad e Empresa
    # Nota: Usei 'company_id' e 'squad_id' como chaves comuns de ligação (JOIN)
    query = """
    SELECT 
        u.name AS parceiro,
        u.created_at AS data_cadastro,
        c.name AS empresa,
        s.name AS squad
    FROM app_topamais_user u
    LEFT JOIN app_topamais_company c ON u.company_id = c.id
    LEFT JOIN app_topamais_squad s ON u.squad_id = s.id
    WHERE u.created_at >= CURRENT_DATE - INTERVAL '7 days'
    ORDER BY u.created_at DESC
    """
    
    df = pd.read_sql(query, engine)

    # Tratamento de datas para exibição e compatibilidade
    if not df.empty:
        df['data_cadastro'] = pd.to_datetime(df['data_cadastro']).dt.tz_localize(None)
        
        # KPIs (Indicadores)
        total_semana = len(df)
        st.metric("Novos Parceiros (Últimos 7 dias)", total_semana)
        
        st.markdown("---")
        
        # Tabela formatada
        st.dataframe(
            df, 
            column_config={
                "data_cadastro": st.column_config.DatetimeColumn("Data de Cadastro", format="DD/MM/YYYY HH:mm"),
                "parceiro": "Nome do Parceiro",
                "empresa": "Empresa",
                "squad": "Squad/Equipe"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum novo parceiro ativado nos últimos 7 dias.")

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
    st.info("Dica: Verifique se os nomes das colunas de ligação (company_id/squad_id) estão corretos.")
