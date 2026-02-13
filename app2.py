import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão com o Banco
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def load_kpi_data():
    engine = create_engine(DB_URL)
    query = """
    SELECT typed_by, paid_at 
    FROM app_topamais_proposal 
    WHERE status = 'DISBURSED' AND paid_at IS NOT NULL
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        df['paid_at'] = pd.to_datetime(df['paid_at'])
        return df

def calculate_week_metrics(df, start_day, end_day, current_month=2, current_year=2026):
    df_range = df[(df['paid_at'].dt.day >= start_day) & (df['paid_at'].dt.day <= end_day)]
    
    # Período Anterior (Mesmo range no mês passado - Jan 2026)
    prev_month_mask = (df_range['paid_at'].dt.year == current_year) & (df_range['paid_at'].dt.month == (current_month - 1))
    prev_period = df_range[prev_month_mask]['typed_by'].nunique()
    
    # Ativos (Atuais - Fev 2026)
    current_mask = (df_range['paid_at'].dt.year == current_year) & (df_range['paid_at'].dt.month == current_month)
    actives = df_range[current_mask]['typed_by'].nunique()
    
    return prev_period, actives

def load_table_data():
    engine = create_engine(DB_URL)
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

# --- Estilização CSS para os quadrinhos verticais ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e0e4e9;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

try:
    df_kpis = load_kpi_data()
    df_table = load_table_data()

    # Cálculos
    prev_w1, active_w1 = calculate_week_metrics(df_kpis, 1, 7)
    prev_w2, active_w2 = calculate_week_metrics(df_kpis, 8, 14)
    META = 24

    # Layout: Colunas para alinhar KPIs com a tabela abaixo
    # Ajustando o peso das colunas para os KPIs ficarem em cima das colunas Sim/Não
    col_info, col_w1, col_w2 = st.columns([2.5, 1, 1])

    with col_w1:
        st.subheader("Semana 1 - 7")
        # Infos empilhadas verticalmente
        st.metric("Período Anterior", prev_w1)
        st.metric("Ativos", active_w1)
        st.metric("Meta Fev", META, delta=active_w1 - META)

    with col_w2:
        st.subheader("Semana 8 - 14")
        # Infos empilhadas verticalmente
        st.metric("Período Anterior", prev_w2)
        st.metric("Ativos", active_w2)
        st.metric("Meta Fev", META, delta=active_w2 - META)

    st.divider()

    # Tratamento da tabela
    if not df_table.empty:
        df_table['Data de Criação'] = pd.to_datetime(df_table['Data de Criação']).dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_table, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
