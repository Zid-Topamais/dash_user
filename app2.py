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
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkNiuSPtTe5Pw"
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

    # Mapeamento de Colunas
    col_data = cols[2]        # C
    col_cliente = cols[4]     # E
    col_digitador = cols[15]  # P
    col_analise = cols[25]    # Z
    col_proposta = cols[26]   # AA
    col_motivo = cols[28]     # AC
    col_ticket = cols[29]     # AD
    col_nome_empresa = cols[33] # AH
    col_cnpj = cols[34]       # AI
    col_func = cols[35]       # AJ

    # --- TRATAMENTO ---
    df_raw[col_ticket] = pd.to_numeric(df_raw[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_raw[col_func] = pd.to_numeric(df_raw[col_func], errors='coerce').fillna(0)
    df_raw[col_data] = pd.to_datetime(df_raw[col_data], dayfirst=True, errors='coerce')
    df_raw = df_raw.dropna(subset=[col_data])

    # --- FILTROS SIDEBAR ---
    st.sidebar.header("Filtros de Performance")
    lista_dig = sorted(df_raw[col_digitador].dropna().unique().tolist())
    selecionado = st.sidebar.selectbox("Selecione o Digitador:", lista_dig)
    
    data_min, data_max = df_raw[col_data].min().date(), df_raw[col_data].max().date()
    periodo = st.sidebar.date_input("Período:", value=(data_min, data_max))

    # --- PROCESSAMENTO ---
    df_periodo = df_raw[(df_raw[col_data].dt.date >= periodo[0]) & (df_raw[col_data].dt.date <= periodo[1])]
    df_sel = df_periodo[df_periodo[col_digitador] == selecionado]
    
    # Benchmarking
    ranking_vol = df_periodo[df_periodo[col_proposta].str.upper() == 'DISBURSED'].groupby(col_digitador)[col_ticket].sum().sort_values(ascending=False)
    top_nome = ranking_vol.index[0] if not ranking_vol.empty else "N/A"
    df_top1 = df_periodo[df_periodo[col_digitador] == top_nome]
    qtd_ativos = df_periodo[col_digitador].nunique()

    def get_dfs_status(df_input):
        st_an = df_input[col_analise].fillna('V').astype(str).str.upper()
        st_pr = df_input[col_proposta].fillna('V').astype(str).str.upper()
        return {
            "Simuladas": df_input,
            "Aprovadas": df_input[st_an == 'APPROVED'],
            "Pagos": df_input[st_pr == 'DISBURSED'],
            "Reprovadas": df_input[st_an == 'REJECTED']
        }

    data_sel = get_dfs_status(df_sel)
    data_total = get_dfs_status(df_periodo)
    data_top = get_dfs_status(df_top1)

    # --- INTERFACE ---
    st.title(f"Performance Individual: {selecionado}")
    
    # 1. KPIs FINANCEIROS
    f1, f2, f3 = st.columns(3)
    vol_sel = data_sel["Pagos"][col_ticket].sum()
    vol_med = data_total["Pagos"][col_ticket].sum() / qtd_ativos if qtd_ativos > 0 else 0
    vol_top = data_top["Pagos"][col_ticket].sum()

    f1.metric("Meu Volume Pago", formata_reais(vol_sel))
    f2.metric("Média Equipe", formata_reais(vol_med), delta=formata_reais(vol_sel - vol_med))
    f3.metric(f"Líder ({top_nome})", formata_reais(vol_top), delta=formata_reais(vol_sel - vol_top), delta_color="normal")

    # --- 2. FUNIL DE EQUIPE COM DRILL DOWN (POR DIGITADOR) ---
    st.divider()
    st.subheader("👥 Funil Comparativo de Digitadores")

    # Preparação dos dados para a tabela pivot
    # Vamos agrupar por Digitador e Status da Proposta
    # col_proposta (AA) e col_ticket (AD)
    
    with st.expander("📊 Visão Consolidada: Qtd e Valor por Status", expanded=True):
        
        # 1. Tabela de QUANTIDADE (Qtd de Propostas por Status)
        df_status_qtd = df_periodo.groupby([col_digitador, col_proposta]).size().unstack(fill_value=0)
        
        # 2. Tabela de VALOR (Soma de R$ por Status)
        df_status_val = df_periodo.groupby([col_digitador, col_proposta])[col_ticket].sum().unstack(fill_value=0)

        # Seleção do que visualizar
        visao = st.radio("Escolha a métrica da tabela:", ["Quantidade de Propostas", "Valor Total (R$)"], horizontal=True)

        if visao == "Quantidade de Propostas":
            st.markdown("**Contagem de propostas por etapa do funil:**")
            # Estilização para destacar números maiores
            st.dataframe(df_status_qtd.style.background_gradient(cmap='Greens', axis=0), use_container_width=True)
            
        else:
            st.markdown("**Valores financeiros (R$) parados/pagos em cada etapa:**")
            # Formatando os valores para Reais na exibição
            df_val_formatado = df_status_val.applymap(formata_reais)
            st.dataframe(df_val_formatado, use_container_width=True)

        st.caption("ℹ️ Use a barra de rolagem lateral da tabela para ver todos os status (CANCELLED, DISBURSED, EXPIRED, etc.)")

    # --- 2.1 DRILL DOWN INDIVIDUAL (O QUE VOCÊ JÁ TINHA, MAS REATIVO) ---
    st.divider()
    st.subheader(f"🔍 Detalhamento Individual: {selecionado}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Simuladas", "✅ Aprovadas", "💸 Pagos", "🚫 Reprovadas"])

    with tab1:
        st.markdown(f'<div class="funnel-header">LISTA: SIMULADAS ({selecionado})</div>', unsafe_allow_html=True)
        st.dataframe(data_sel["Simuladas"][[col_data, col_cliente, col_analise, col_proposta, col_ticket]], use_container_width=True)
    with tab2:
        st.markdown(f'<div class="funnel-header">LISTA: APROVADAS ({selecionado})</div>', unsafe_allow_html=True)
        st.dataframe(data_sel["Aprovadas"][[col_data, col_cliente, col_ticket]], use_container_width=True)
    with tab3:
        st.markdown(f'<div class="funnel-header">LISTA: PAGOS ({selecionado})</div>', unsafe_allow_html=True)
        st.dataframe(data_sel["Pagos"][[col_data, col_cliente, col_ticket]], use_container_width=True)
    with tab4:
        st.markdown(f'<div class="funnel-header">MOTIVOS DE REPROVAÇÃO ({selecionado})</div>', unsafe_allow_html=True)
        st.dataframe(data_sel["Reprovadas"][[col_cliente, col_motivo]], use_container_width=True)

    # --- 3. TOPA+ OPORTUNIDADES (SOMENTE DISBURSED) ---
    st.divider()
    st.subheader("🚀 Topa+ Oportunidades (Base: Empresas Pagas)")
    
    # Lógica: Filtrar apenas registros onde o status da proposta é DISBURSED
    df_pagos_op = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED']
    
    if not df_pagos_op.empty:
        # Agrupar por CNPJ apenas as empresas que já tiveram pagamentos
        df_op = df_pagos_op.groupby(col_cnpj).agg({
            col_nome_empresa: 'first',
            col_func: 'max',
            col_ticket: ['count', 'sum']
        }).reset_index()
        
        df_op.columns = ['CNPJ', 'Empresa', 'Colaboradores', 'Qtd Efetivada', 'Volume Realizado']
        
        # Ticket Médio do Digitador (usando todos os seus pagamentos do período)
        tkt_medio = data_sel["Pagos"][col_ticket].mean()
        
        # Cálculo de Potencial
        df_op['Potencial Total'] = df_op['Colaboradores'] * tkt_medio
        df_op['Gap (R$)'] = df_op['Potencial Total'] - df_op['Volume Realizado']
        df_op['Penetração'] = (df_op['Qtd Efetivada'] / df_op['Colaboradores'] * 100).fillna(0)

        o1, o2, o3 = st.columns(3)
        o1.metric("Empresas com Pagos", f"{len(df_op)} un")
        o2.metric("Potencial Restante", formata_reais(df_op['Gap (R$)'].sum()))
        o3.metric("Ticket Médio Ref.", formata_reais(tkt_medio))

        # Tabela Drill Down Formatada
        df_op_disp = df_op.copy()
        for c in ['Volume Realizado', 'Potencial Total', 'Gap (R$)']:
            df_op_disp[c] = df_op_disp[c].apply(formata_reais)
        df_op_disp['Penetração'] = df_op_disp['Penetração'].apply(lambda x: f"{x:.1f}%")
        
        st.markdown("**Análise de Carteira Ativa:**")
        st.dataframe(df_op_disp.sort_values('Gap (R$)', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("Este digitador ainda não possui propostas com status 'Disbursed' no período selecionado.")

except Exception as e:
    st.error(f"Erro ao processar o Dashboard: {e}")
