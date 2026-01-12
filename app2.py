import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Topa+ | Performance", layout="wide")

# --- ESTILIZAÇÃO TURQUESA ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #99FFFF !important; }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stHeader {
        color: #004D40 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        border: 1px solid #eef2f7 !important;
    }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    .funnel-header { 
        background-color: #004D40; 
        color: white; 
        padding: 5px 15px; 
        border-radius: 5px; 
        margin-bottom: 15px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO GOOGLE SHEETS ---
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkNiuSPtTe5Pw"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados2"

@st.cache_data(ttl=600)
def load_data():
    return pd.read_csv(url, dtype=str)

try:
    df_base = load_data()
    df_base.columns = df_base.columns.str.strip()
    colunas_reais = df_base.columns.tolist()

    # --- MAPEAMENTO ---
    col_data = colunas_reais[2]  # Coluna C
    col_digitadores = colunas_reais[15] # Coluna P
    col_ticket = colunas_reais[29] # Coluna AD
    col_analise = colunas_reais[25] # Coluna Z
    col_proposta = colunas_reais[26] # Coluna AA
    col_motivo = colunas_reais[28] # Coluna AC

    # --- TRATAMENTO DE DADOS ---
    df_base[col_ticket] = df_base[col_ticket].fillna('0').astype(str).str.strip()
    df_base[col_ticket] = df_base[col_ticket].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df_base[col_ticket] = pd.to_numeric(df_base[col_ticket], errors='coerce').fillna(0)
    df_base[col_data] = pd.to_datetime(df_base[col_data], dayfirst=True, errors='coerce')
    df_base = df_base.dropna(subset=[col_data])

    # --- SIDEBAR FILTROS ---
    st.sidebar.header("Análise Individual")
    
    # 1. Filtro de Digitador (Obrigatório para o Benchmarking)
    lista_dig = sorted(df_base[col_digitadores].dropna().unique().astype(str).tolist())
    selecionado = st.sidebar.selectbox("Selecione o Digitador:", lista_dig)
    
    # 2. Filtro de Período
    data_min, data_max = df_base[col_data].min().date(), df_base[col_data].max().date()
    periodo = st.sidebar.date_input("Período:", value=(data_min, data_max))

    # --- PROCESSAMENTO DE DADOS ---
    # Filtrar período global
    df_periodo = df_base[(df_base[col_data].dt.date >= periodo[0]) & (df_base[col_data].dt.date <= periodo[1])]
    
    # Filtrar dados do Digitador Selecionado
    df_sel = df_periodo[df_periodo[col_digitadores] == selecionado]

    # Função para extrair métricas de um dataframe
    def get_stats(df):
        st_an = df[col_analise].fillna('VAZIO').astype(str).str.upper().str.strip()
        st_pr = df[col_proposta].fillna('VAZIO').astype(str).str.upper().str.strip()
        lista_gerados = ['CANCELLED_BY_USER', 'EXPIRED', 'CONTRACT_GENERATED', 'DISBURSED']
        
        pagos = df[st_pr == 'DISBURSED']
        return {
            "simu_qtd": len(df),
            "aprov_qtd": len(df[st_an == 'APPROVED']),
            "gerados_qtd": len(df[st_pr.isin(lista_gerados)]),
            "pagos_qtd": len(pagos),
            "pagos_vol": pagos[col_ticket].sum(),
            "ticket_medio": pagos[col_ticket].mean() if len(pagos) > 0 else 0
        }

    # Estatísticas do Selecionado
    stats_sel = get_stats(df_sel)

    # Estatísticas do Top 1 (Líder em Volume Pago)
    ranking_vol = df_periodo[df_periodo[col_proposta].str.upper().str.strip() == 'DISBURSED'].groupby(col_digitadores)[col_ticket].sum().sort_values(ascending=False)
    top_nome = ranking_vol.index[0] if not ranking_vol.empty else "N/A"
    df_top1 = df_periodo[df_periodo[col_digitadores] == top_nome]
    stats_top = get_stats(df_top1)

    # Estatísticas da Média da Equipe (Apenas digitadores que simularam no período)
    ativos_nomes = df_periodo[col_digitadores].unique()
    qtd_ativos = len(ativos_nomes)
    stats_total_periodo = get_stats(df_periodo)
    
    def calc_media(valor): return valor / qtd_ativos if qtd_ativos > 0 else 0

    def formata_reais(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # --- INTERFACE ---
    st.title(f"Performance: {selecionado}")
    st.markdown(f"Análise comparativa de **{periodo[0].strftime('%d/%m/%Y')}** a **{periodo[1].strftime('%d/%m/%Y')}**")
    st.divider()

    # --- 1. FINANCEIRO (COMPARATIVO) ---
    st.subheader("💰 KPI Financeiro - Volume Pago")
    f1, f2, f3 = st.columns(3)
    
    f1.metric("Individual", formata_reais(stats_sel['pagos_vol']))
    
    delta_med_vol = stats_sel['pagos_vol'] - calc_media(stats_total_periodo['pagos_vol'])
    f2.metric("Média Equipe", formata_reais(calc_media(stats_total_periodo['pagos_vol'])), 
              delta=formata_reais(delta_med_vol))
    
    delta_top_vol = stats_sel['pagos_vol'] - stats_top['pagos_vol']
    f3.metric(f"Top 1 ({top_nome})", formata_reais(stats_top['pagos_vol']), 
              delta=formata_reais(delta_top_vol), delta_color="normal")

    st.divider()

    # --- 2. FUNIL QUANTITATIVO (COMPARATIVO) ---
    st.subheader("📊 Funil de Propostas (Quantidade)")
    
    # Linha Simuladas
    st.markdown('<div class="funnel-header">1. PROPOSTAS SIMULADAS</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    q1.metric("Individual", f"{stats_sel['simu_qtd']} un")
    q2.metric("Média Equipe", f"{calc_media(stats_total_periodo['simu_qtd']):.1f} un", delta=f"{stats_sel['simu_qtd'] - calc_media(stats_total_periodo['simu_qtd']):.1f}")
    q3.metric("Top 1", f"{stats_top['simu_qtd']} un", delta=f"{stats_sel['simu_qtd'] - stats_top['simu_qtd']}", delta_color="normal")

    # Linha Aprovadas
    st.markdown('<div class="funnel-header">2. PROPOSTAS APROVADAS</div>', unsafe_allow_html=True)
    q4, q5, q6 = st.columns(3)
    q4.metric("Individual", f"{stats_sel['aprov_qtd']} un")
    q5.metric("Média Equipe", f"{calc_media(stats_total_periodo['aprov_qtd']):.1f} un", delta=f"{stats_sel['aprov_qtd'] - calc_media(stats_total_periodo['aprov_qtd']):.1f}")
    q6.metric("Top 1", f"{stats_top['aprov_qtd']} un", delta=f"{stats_sel['aprov_qtd'] - stats_top['aprov_qtd']}", delta_color="normal")

    # Linha Pagos
    st.markdown('<div class="funnel-header">3. CONTRATOS PAGOS</div>', unsafe_allow_html=True)
    q7, q8, q9 = st.columns(3)
    q7.metric("Individual", f"{stats_sel['pagos_qtd']} un")
    q8.metric("Média Equipe", f"{calc_media(stats_total_periodo['pagos_qtd']):.1f} un", delta=f"{stats_sel['pagos_qtd'] - calc_media(stats_total_periodo['pagos_qtd']):.1f}")
    q9.metric("Top 1", f"{stats_top['pagos_qtd']} un", delta=f"{stats_sel['pagos_qtd'] - stats_top['pagos_qtd']}", delta_color="normal")

    st.divider()

    # --- 3. CONVERSÕES E TICKET ---
    st.subheader("🎯 Eficiência Individual")
    e1, e2, e3 = st.columns(3)
    
    conv_final = (stats_sel['pagos_qtd'] / stats_sel['simu_qtd'] * 100) if stats_sel['simu_qtd'] > 0 else 0
    aproveitamento = (stats_sel['aprov_qtd'] / stats_sel['simu_qtd'] * 100) if stats_sel['simu_qtd'] > 0 else 0
    
    e1.metric("Conversão Final", f"{conv_final:.2f}%")
    e2.metric("Aproveitamento Crédito", f"{aproveitamento:.2f}%")
    e3.metric("Ticket Médio", formata_reais(stats_sel['ticket_medio']))

    # Barra de Progresso Financeiro
    if stats_top['pagos_vol'] > 0:
        progresso = min(stats_sel['pagos_vol'] / stats_top['pagos_vol'], 1.0)
        st.write(f"**Aproveitamento em R$ (vs Top 1):** {progresso*100:.1f}%")
        st.progress(progresso)

except Exception as e:
    st.error(f"Erro ao processar o dashboard: {e}")
