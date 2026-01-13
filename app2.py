import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Command Center Topa+", layout="wide")

# --- ESTILIZAÇÃO TURQUESA ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #99FFFF !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #004D40 !important; font-weight: 700 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        border: 1px solid #eef2f7 !important;
    }
    .funnel-header { 
        background-color: #004D40; color: white; padding: 8px 15px; 
        border-radius: 8px; margin-bottom: 15px; font-size: 14px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO E CARREGAMENTO ---
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkVptkNiuSPtTe5Pw"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados2"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(url, dtype=str)
    df.columns = df.columns.str.strip()
    return df

def formata_reais(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

try:
    df_raw = load_data()
    cols = df_raw.columns.tolist()

    # --- MAPEAMENTO DE COLUNAS ---
    col_data_criacao = cols[2]     # Coluna C (Data de Criação)
    col_data_pagamento = cols[23]  # Coluna X (Data de Pagamento)
    col_cliente = cols[4]          # Coluna E
    col_digitador = cols[15]       # Coluna P
    col_analise = cols[25]         # Coluna Z
    col_proposta = cols[26]        # Coluna AA
    col_motivo = cols[28]          # Coluna AC
    col_ticket = cols[29]          # Coluna AD
    col_nome_empresa = cols[33]    # Coluna AH
    col_cnpj = cols[34]            # Coluna AI
    col_func = cols[35]            # Coluna AJ

    # --- TRATAMENTO ---
    df_raw[col_ticket] = pd.to_numeric(df_raw[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_raw[col_func] = pd.to_numeric(df_raw[col_func], errors='coerce').fillna(0)
    
    df_raw[col_data_criacao] = pd.to_datetime(df_raw[col_data_criacao], dayfirst=True, errors='coerce')
    df_raw[col_data_pagamento] = pd.to_datetime(df_raw[col_data_pagamento], dayfirst=True, errors='coerce')

    # --- SIDEBAR FILTROS ---
    st.sidebar.header("Filtros de Performance")
    
    data_min = df_raw[col_data_criacao].min().date()
    data_max = df_raw[col_data_criacao].max().date()
    periodo = st.sidebar.date_input("Período de Análise:", value=(data_min, data_max))
    
    lista_dig = sorted(df_raw[col_digitador].dropna().unique().tolist())
    selecionado = st.sidebar.selectbox("Selecione o Digitador:", ["Todos"] + lista_dig)

    # --- LÓGICA DE FILTRAGEM HÍBRIDA (REGRA DE NEGÓCIO) ---
    def filtrar_por_data_hibrida(df, start_date, end_date):
        # Condição A: Status é DISBURSED -> Olha para a Coluna X (Pagamento)
        cond_pago = (df[col_proposta].str.upper().str.strip() == 'DISBURSED') & \
                    (df[col_data_pagamento].dt.date >= start_date) & \
                    (df[col_data_pagamento].dt.date <= end_date)
        
        # Condição B: Outros Status -> Olha para a Coluna C (Criação)
        cond_outros = (df[col_proposta].str.upper().str.strip() != 'DISBURSED') & \
                      (df[col_data_criacao].dt.date >= start_date) & \
                      (df[col_data_criacao].dt.date <= end_date)
        
        return df[cond_pago | cond_outros]

    df_periodo = filtrar_por_data_hibrida(df_raw, periodo[0], periodo[1])
    
    if selecionado != "Todos":
        df_sel = df_periodo[df_periodo[col_digitador] == selecionado]
    else:
        df_sel = df_periodo

    # --- INTERFACE ---
    st.title(f"Performance Topa+ | {selecionado}")
    st.info(f"Critério: 'DISBURSED' pela data de pagamento (X). Demais status pela data de criação (C).")

    # 1. MÉTRICAS FINANCEIRAS
    st.subheader("💰 Volume Consolidado")
    df_pagos_periodo = df_periodo[df_periodo[col_proposta].str.upper().str.strip() == 'DISBURSED']
    
    vol_total = df_pagos_periodo[col_ticket].sum()
    qtd_dig_ativos = df_periodo[col_digitador].nunique()
    media_equipe = vol_total / qtd_dig_ativos if qtd_dig_ativos > 0 else 0
    
    vol_sel = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED'][col_ticket].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("Volume Pago (Período)", formata_reais(vol_sel))
    m2.metric("Média por Digitador", formata_reais(media_equipe), delta=formata_reais(vol_sel - media_equipe))
    m3.metric("Digitadores Ativos", f"{qtd_dig_ativos} un")

    # 2. FUNIL DE EQUIPE COM DRILL DOWN (MÉTRICA PEDIDA)
    st.divider()
    st.subheader("👥 Seção 2: Funil Comparativo de Digitadores")
    

    with st.expander("📊 Visão de Status: Quantidade e Valores Retidos", expanded=True):
        col_t1, col_t2 = st.tabs(["Quantidade de Propostas", "Valor Parado/Pago (R$)"])
        
        with col_t1:
            st.markdown("**Propostas por Digitador em cada etapa:**")
            df_status_qtd = df_periodo.groupby([col_digitador, col_proposta]).size().unstack(fill_value=0)
            st.dataframe(df_status_qtd.style.background_gradient(cmap='Greens', axis=1), use_container_width=True)
            
        with col_t2:
            st.markdown("**Valores (R$) por Digitador em cada etapa:**")
            df_status_val = df_periodo.groupby([col_digitador, col_proposta])[col_ticket].sum().unstack(fill_value=0)
            st.dataframe(df_status_val.applymap(formata_reais), use_container_width=True)

    # 3. DETALHAMENTO INDIVIDUAL (DRILL DOWN)
    st.divider()
    st.subheader(f"🔍 Drill Down Individual: {selecionado}")
    t1, t2, t3 = st.tabs(["💸 Pagos", "📋 Todos os Status", "🚫 Motivos de Reprovação"])
    
    with t1:
        st.dataframe(df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED'][[col_data_pagamento, col_cliente, col_ticket]], use_container_width=True)
    with t2:
        st.dataframe(df_sel[[col_data_criacao, col_cliente, col_proposta, col_ticket]], use_container_width=True)
    with t3:
        df_rep = df_sel[df_sel[col_analise].str.upper().str.strip() == 'REJECTED']
        st.dataframe(df_rep[[col_cliente, col_motivo, col_ticket]], use_container_width=True)

    # 4. TOPA+ OPORTUNIDADES
    st.divider()
    st.subheader("🚀 Topa+ Oportunidades")
    df_pago_op = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED']
    
    if not df_pago_op.empty:
        df_op = df_pago_op.groupby(col_cnpj).agg({
            col_nome_empresa: 'first',
            col_func: 'max',
            col_ticket: ['count', 'sum']
        }).reset_index()
        df_op.columns = ['CNPJ', 'Empresa', 'Funcionários', 'Efetivados', 'Realizado']
        
        tkt_medio = df_pago_op[col_ticket].mean()
        df_op['Potencial R$'] = df_op['Funcionários'] * tkt_medio
        df_op['Gap R$'] = df_op['Potencial R$'] - df_op['Realizado']
        
        df_view = df_op.copy()
        for c in ['Realizado', 'Potencial R$', 'Gap R$']:
            df_view[c] = df_view[c].apply(formata_reais)
        
        st.dataframe(df_view.sort_values('Funcionários', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao processar: {e}")
