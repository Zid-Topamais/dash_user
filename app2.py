import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão com o Banco
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def load_data():
    engine = create_engine(DB_URL)
    
    # Query SQL otimizada com as colunas condicionais (Case When)
    query = """
    SELECT 
        c.name AS "Empresa",
        s.name AS "Squad",
        u.name AS "Parceiro",
        u.created_at AS "Data de Criação",
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM app_topamais_proposal p 
                WHERE p.typed_by = u.id 
                AND p.status = 'DISBURSED' 
                AND p.paid_at >= '2026-02-01' AND p.paid_at < '2026-02-08'
            ) THEN 'Sim' 
            ELSE 'Não' 
        END AS "Semana 1 - 7",
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM app_topamais_proposal p 
                WHERE p.typed_by = u.id 
                AND p.status = 'DISBURSED' 
                AND p.paid_at >= '2026-02-08' AND p.paid_at < '2026-02-15'
            ) THEN 'Sim' 
            ELSE 'Não' 
        END AS "Semana 8 - 14"
    FROM app_topamais_user u
    LEFT JOIN app_topamais_user_company uc ON u.id = uc.user_id
    LEFT JOIN app_topamais_company c ON uc.company_id = c.id
    LEFT JOIN app_topamais_user_squad us ON u.id = us.user_id
    LEFT JOIN app_topamais_squad s ON us.squad_id = s.id
    ORDER BY u.created_at DESC
    """
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

# Interface
st.title("Ativação de Parceiros")

try:
    df = load_data()
    
    # Formatação apenas da data de visualização
    if not df.empty:
        df['Data de Criação'] = pd.to_datetime(df['Data de Criação']).dt.strftime('%d/%m/%Y %H:%M')
    
    # Exibição direta da tabela
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
