import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão com o Banco
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def load_kpi_data():
    engine = create_engine(DB_URL)
    # Trazemos apenas o necessário para calcular os KPIs em memória (mais rápido que subqueries complexas)
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
    # Filtra apenas propostas dentro do range de dias (ex: dia 1 a 7 de QUALQUER mês)
    df_range = df[(df['paid_at'].dt.day >= start_day) & (df['paid_at'].dt.day <= end_day)]
    
    # 1. Melhor Semana da História (Máximo de parceiros distintos em um único mês nesse range de dias)
    # Agrupa por Ano-Mês e conta usuários únicos
    history_group = df_range.groupby([df_range['paid_at'].dt.year, df_range['paid_at'].dt.month])['typed_by'].nunique()
    best_week = history_group.max() if not history_group.empty else 0
    
    # 2. Período Anterior (Mesmo range no mês passado - Jan 2026)
    prev_month_mask = (df_range['paid_at'].dt.year == current_year) & (df_range['paid_at'].dt.month == (current_month - 1))
    prev_period = df_range[prev_month_mask]['typed_by'].nunique()
    
    # 3. Ativos (Atuais - Fev 2026)
    current_mask = (df_range['paid_at'].dt.year == current_year) & (df_range['paid_at'].dt.month == current_month)
    actives = df_range[current_mask]['typed_by'].nunique()
    
    return best_week, prev_period, actives

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

# --- Interface ---
st.title("Ativação de Parceiros")

try:
    # Carregar dados
    df_kpis = load_kpi_data()
    df_table = load_table_data()

    # Cálculos KPIs
    # Semana 1 (Dias 1 a 7)
    best_w1, prev_w1, active_w1 = calculate_week_metrics(df_kpis, 1, 7)
    # Semana 2 (Dias 8 a 14)
    best_w2, prev_w2, active_w2 = calculate_week_metrics(df_kpis, 8, 14)

    META = 24

    # Layout dos KPIs
    st.markdown("### Resumo de Performance")
    col_spacer, col_w1, col_w2 = st.columns([2, 1, 1]) # Espaço para alinhar com as colunas da direita

    with col_w1:
        st.markdown("**Semana 1 - 7**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Melhor Hist.", best_w1)
        c2.metric("Mês Ant.", prev_w1)
        c3.metric("Ativos/Meta", f"{active_w1}/{META}", delta=active_w1-META)
        
    with col_w2:
        st.markdown("**Semana 8 - 14**")
        c4, c5, c6 = st.columns(3)
        c4.metric("Melhor Hist.", best_w2)
        c5.metric("Mês Ant.", prev_w2)
        c6.metric("Ativos/Meta", f"{active_w2}/{META}", delta=active_w2-META)

    st.divider()

    # Tabela Principal
    if not df_table.empty:
        df_table['Data de Criação'] = pd.to_datetime(df_table['Data de Criação']).dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_table, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
