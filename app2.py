import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão com o Banco
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

# --- Estilização CSS para Mini-Cards Verticais ---
st.markdown("""
    <style>
    /* Estilo do container do KPI */
    .kpi-card {
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 5px;
        border-left: 3px solid #007bff;
        margin-bottom: 4px;
    }
    .kpi-label {
        font-size: 10px;
        color: #666;
        margin-bottom: 0px;
        text-transform: uppercase;
        font-weight: bold;
    }
    .kpi-value {
        font-size: 16px;
        font-weight: bold;
        color: #111;
    }
    /* Ajuste de títulos das colunas */
    .week-title {
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 8px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    engine = create_engine(DB_URL)
    # Query unificada para evitar múltiplas chamadas
    query_p = "SELECT typed_by, paid_at FROM app_topamais_proposal WHERE status = 'DISBURSED' AND paid_at IS NOT NULL"
    query_t = """
    SELECT 
        c.name AS "Empresa", s.name AS "Squad", u.name AS "Parceiro", u.created_at AS "Data de Criação",
        CASE WHEN EXISTS (SELECT 1 FROM app_topamais_proposal p WHERE p.typed_by = u.id AND p.status = 'DISBURSED' AND p.paid_at >= '2026-02-01' AND p.paid_at < '2026-02-08') THEN 'Sim' ELSE 'Não' END AS "Semana 1 - 7",
        CASE WHEN EXISTS (SELECT 1 FROM app_topamais_proposal p WHERE p.typed_by = u.id AND p.status = 'DISBURSED' AND p.paid_at >= '2026-02-08' AND p.paid_at < '2026-02-15') THEN 'Sim' ELSE 'Não' END AS "Semana 8 - 14"
    FROM app_topamais_user u
    LEFT JOIN app_topamais_user_company uc ON u.id = uc.user_id
    LEFT JOIN app_topamais_company c ON uc.company_id = c.id
    LEFT JOIN app_topamais_user_squad us ON u.id = us.user_id
    LEFT JOIN app_topamais_squad s ON us.squad_id = s.id
    ORDER BY u.created_at DESC
    """
    with engine.connect() as conn:
        df_p = pd.read_sql(query_p, conn)
        df_p['paid_at'] = pd.to_datetime(df_p['paid_at'])
        df_t = pd.read_sql(query_t, conn)
        return df_p, df_t

def render_mini_kpi(label, value):
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

try:
    df_p, df_t = load_data()
    META = 24

    # Cálculos Semana 1
    w1_range = df_p[(df_p['paid_at'].dt.day >= 1) & (df_p['paid_at'].dt.day <= 7)]
    prev_w1 = w1_range[(w1_range['paid_at'].dt.month == 1) & (w1_range['paid_at'].dt.year == 2026)]['typed_by'].nunique()
    act_w1 = w1_range[(w1_range['paid_at'].dt.month == 2) & (w1_range['paid_at'].dt.year == 2026)]['typed_by'].nunique()

    # Cálculos Semana 2
    w2_range = df_p[(df_p['paid_at'].dt.day >= 8) & (df_p['paid_at'].dt.day <= 14)]
    prev_w2 = w2_range[(w2_range['paid_at'].dt.month == 1) & (w2_range['paid_at'].dt.year == 2026)]['typed_by'].nunique()
    act_w2 = w2_range[(w2_range['paid_at'].dt.month == 2) & (w2_range['paid_at'].dt.year == 2026)]['typed_by'].nunique()

    # Alinhamento: As colunas da tabela são (Empresa, Squad, Parceiro, Data). 
    # Usamos um spacer proporcional para os KPIs caírem em cima das colunas de "Semana"
    col_spacer, col_w1, col_w2 = st.columns([3.8, 1, 1])

    with col_w1:
        st.markdown('<div class="week-title">Semana 1-7</div>', unsafe_allow_html=True)
        render_mini_kpi("Ant.", prev_w1)
        render_mini_kpi("Ativos", act_w1)
        render_mini_kpi("Meta", META)

    with col_w2:
        st.markdown('<div class="week-title">Semana 8-14</div>', unsafe_allow_html=True)
        render_mini_kpi("Ant.", prev_w2)
        render_mini_kpi("Ativos", act_w2)
        render_mini_kpi("Meta", META)

    st.divider()

    # Formatação Final da Tabela
    if not df_t.empty:
        df_t['Data de Criação'] = pd.to_datetime(df_t['Data de Criação']).dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_t, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
