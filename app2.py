import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

# Conexão com o Banco
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

# --- Estilização CSS ---
st.markdown("""
    <style>
    .kpi-card {
        background-color: #ffffff;
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid #e6e9ef;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .kpi-label { font-size: 11px; color: #555; font-weight: 500; }
    .kpi-value { font-size: 14px; font-weight: bold; color: #111; }
    .delta-up { color: #007bff; font-size: 10px; font-weight: bold; }
    .delta-down { color: #ff4b4b; font-size: 10px; font-weight: bold; }
    .meta-pct { color: #666; font-size: 10px; margin-left: 5px; }
    .week-title {
        font-size: 13px; font-weight: bold; margin-bottom: 6px;
        color: #1f2937; border-bottom: 2px solid #007bff; width: fit-content;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    engine = create_engine(DB_URL)
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

def calc_pct(current, previous):
    if previous == 0: return 0
    return ((current - previous) / previous) * 100

try:
    df_p, df_t = load_data()
    META = 24

    # --- SIDEBAR / FILTROS ---
    st.sidebar.header("Filtros")
    filtro_semana = st.sidebar.selectbox("Filtrar por Semana", ["Todas Semanas", "Semana 1 - 7", "Semana 8 - 14"])
    filtro_ativo = st.sidebar.radio("Apenas Ativos?", ["Ambos", "Sim", "Não"])

    # Aplicando Filtros na Tabela
    df_filtered = df_t.copy()
    
    if filtro_ativo != "Ambos":
        # Se filtrar por ativo, checamos se deu 'Sim' em QUALQUER uma das semanas selecionadas
        if filtro_semana == "Todas Semanas":
            mask = (df_filtered["Semana 1 - 7"] == filtro_ativo) | (df_filtered["Semana 8 - 14"] == filtro_ativo)
        else:
            mask = df_filtered[filtro_semana] == filtro_ativo
        df_filtered = df_filtered[mask]

    # --- LÓGICA DOS KPIS ---
    # Semana 1
    w1_range = df_p[(df_p['paid_at'].dt.day >= 1) & (df_p['paid_at'].dt.day <= 7)]
    prev_w1 = w1_range[(w1_range['paid_at'].dt.month == 1)]['typed_by'].nunique()
    act_w1 = w1_range[(w1_range['paid_at'].dt.month == 2)]['typed_by'].nunique()
    pct_w1 = calc_pct(act_w1, prev_w1)
    meta_pct_w1 = (act_w1 / META) * 100

    # Semana 2
    w2_range = df_p[(df_p['paid_at'].dt.day >= 8) & (df_p['paid_at'].dt.day <= 14)]
    prev_w2 = w2_range[(w2_range['paid_at'].dt.month == 1)]['typed_by'].nunique()
    act_w2 = w2_range[(w2_range['paid_at'].dt.month == 2)]['typed_by'].nunique()
    pct_w2 = calc_pct(act_w2, prev_w2)
    meta_cumulativa_w2 = ((act_w1 + act_w2) / META) * 100

    # --- RENDERIZAÇÃO ---
    col_spacer, col_w1, col_w2 = st.columns([3.8, 1, 1])

    # Mostrar KPIs apenas se a semana estiver selecionada ou "Todas"
    if filtro_semana in ["Todas Semanas", "Semana 1 - 7"]:
        with col_w1:
            st.markdown('<div class="week-title">Semana 1-7</div>', unsafe_allow_html=True)
            color = "delta-up" if pct_w1 >= 0 else "delta-down"
            st.markdown(f'''
                <div class="kpi-card"><span class="kpi-label">Ant.</span><span class="kpi-value">{prev_w1}</span></div>
                <div class="kpi-card"><span class="kpi-label">Ativos</span><span class="kpi-value">{act_w1} <span class="{color}">{pct_w1:+.1f}%</span></span></div>
                <div class="kpi-card"><span class="kpi-label">Meta</span><span class="kpi-value">{META} <span class="meta-pct">({meta_pct_w1:.0f}%)</span></span></div>
            ''', unsafe_allow_html=True)

    if filtro_semana in ["Todas Semanas", "Semana 8 - 14"]:
        with col_w2:
            st.markdown('<div class="week-title">Semana 8-14</div>', unsafe_allow_html=True)
            color = "delta-up" if pct_w2 >= 0 else "delta-down"
            st.markdown(f'''
                <div class="kpi-card"><span class="kpi-label">Ant.</span><span class="kpi-value">{prev_w2}</span></div>
                <div class="kpi-card"><span class="kpi-label">Ativos</span><span class="kpi-value">{act_w2} <span class="{color}">{pct_w2:+.1f}%</span></span></div>
                <div class="kpi-card"><span class="kpi-label">Meta</span><span class="kpi-value">{META} <span class="meta-pct">({meta_cumulativa_w2:.0f}% sum)</span></span></div>
            ''', unsafe_allow_html=True)

    st.divider()

    # Tabela Final
    if not df_filtered.empty:
        df_filtered['Data de Criação'] = pd.to_datetime(df_filtered['Data de Criação']).dt.strftime('%d/%m/%Y')
        # Se filtrar uma semana específica, podemos esconder a outra na tabela para ficar mais limpo
        cols_to_show = ["Empresa", "Squad", "Parceiro", "Data de Criação"]
        if filtro_semana == "Todas Semanas":
            cols_to_show += ["Semana 1 - 7", "Semana 8 - 14"]
        else:
            cols_to_show.append(filtro_semana)
            
        st.dataframe(df_filtered[cols_to_show], use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
