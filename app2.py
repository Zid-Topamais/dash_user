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

    # Mapeamento de Colunas (Índices baseados na sua estrutura)
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

    # --- PROCESSAMENTO DE DADOS ---
    df_periodo = df_raw[(df_raw[col_data].dt.date >= periodo[0]) & (df_raw[col_data].dt.date <= periodo[1])]
    df_sel = df_periodo[df_periodo[col_digitador] == selecionado]
    
    # Identificar Benchmarks (Top 1 e Ativos)
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

    # --- 1. KPI FINANCEIRO (BENCHMARKING) ---
    st.title(f"Performance Individual: {selecionado}")
    st.subheader("💰 Volume Pago (R$)")
    
    f1, f2, f3 = st.columns(3)
    vol_sel = data_sel["Pagos"][col_ticket].sum()
    vol_med = data_total["Pagos"][col_ticket].sum() / qtd_ativos if qtd_ativos > 0 else 0
    vol_top = data_top["Pagos"][col_ticket].sum()

    f1.metric("Meu Volume", formata_reais(vol_sel))
    f2.metric("Média Equipe", formata_reais(vol_med), delta=formata_reais(vol_sel - vol_med))
    f3.metric(f"Top 1 ({top_nome})", formata_reais(vol_top), delta=formata_reais(vol_sel - vol_top), delta_color="normal")

    # --- 2. FUNIL QUANTITATIVO COM DRILL DOWN ---
    st.divider()
    st.subheader("📊 Funil de Propostas (Qtd) & Drill Down")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Simuladas", "✅ Aprovadas", "💸 Pagos", "🚫 Reprovadas"])

    with tab1:
        st.markdown('<div class="funnel-header">DETALHE: SIMULADAS</div>', unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        q1.metric("Individual", f"{len(data_sel['Simuladas'])} un")
        q2.metric("Média Equipe", f"{len(data_total['Simuladas'])/qtd_ativos:.1f} un")
        q3.metric("Líder", f"{len(data_top['Simuladas'])} un")
        st.dataframe(data_sel["Simuladas"][[col_data, col_cliente, col_analise, col_proposta, col_ticket]], use_container_width=True)

    with tab2:
        st.markdown('<div class="funnel-header">DETALHE: APROVADAS</div>', unsafe_allow_html=True)
        q4, q5, q6 = st.columns(3)
        q4.metric("Individual", f"{len(data_sel['Aprovadas'])} un")
        q5.metric("Média Equipe", f"{len(data_total['Aprovadas'])/qtd_ativos:.1f} un")
        q6.metric("Líder", f"{len(data_top['Aprovadas'])} un")
        st.dataframe(data_sel["Aprovadas"][[col_data, col_cliente, col_ticket]], use_container_width=True)

    with tab3:
        st.markdown('<div class="funnel-header">DETALHE: PAGOS</div>', unsafe_allow_html=True)
        q7, q8, q9 = st.columns(3)
        q7.metric("Individual", f"{len(data_sel['Pagos'])} un")
        q8.metric("Média Equipe", f"{len(data_total['Pagos'])/qtd_ativos:.1f} un")
        q9.metric("Líder", f"{len(data_top['Pagos'])} un")
        st.dataframe(data_sel["Pagos"][[col_data, col_cliente, col_ticket]], use_container_width=True)

    with tab4:
        st.markdown('<div class="funnel-header">ANÁLISE DE PERDAS (REPROVADAS)</div>', unsafe_allow_html=True)
        if not data_sel["Reprovadas"].empty:
            st.dataframe(data_sel["Reprovadas"][[col_cliente, col_motivo]], use_container_width=True)
        else:
            st.success("Nenhuma reprovação no período.")

    # --- 3. TOPA+ OPORTUNIDADES (POTENCIAL) ---
    st.divider()
    st.subheader("🚀 Topa+ Oportunidades - Potencial de Negócios")
    
    # Agrupamento por CNPJ para análise de potencial
    df_op = data_sel["Simuladas"].groupby(col_cnpj).agg({
        col_nome_empresa: 'first',
        col_func: 'max',
        col_ticket: 'sum' # O que já foi vendido
    }).reset_index()
    
    # Filtrar apenas quem pagou na realidade do digitador para pegar o ticket médio dele
    tkt_medio = data_sel["Pagos"][col_ticket].mean() if not data_sel["Pagos"].empty else 0
    
    df_op.columns = ['CNPJ', 'Empresa', 'Funcionários', 'Volume Realizado']
    df_op['Potencial Total'] = df_op['Funcionários'] * tkt_medio
    df_op['Gap (Oportunidade)'] = df_op['Potencial Total'] - df_op['Volume Realizado']

    o1, o2, o3 = st.columns(3)
    o1.metric("Empresas em Carteira", f"{len(df_op)} un")
    o2.metric("Potencial em Carteira", formata_reais(df_op['Potencial Total'].sum()))
    o3.metric("Ticket Médio Ref.", formata_reais(tkt_medio))

    # Tabela Drill Down Oportunidades
    df_op_disp = df_op.copy()
    for c in ['Volume Realizado', 'Potencial Total', 'Gap (Oportunidade)']:
        df_op_disp[c] = df_op_disp[c].apply(formata_reais)
    
    st.markdown("**Onde está o dinheiro (por Empresa):**")
    st.dataframe(df_op_disp.sort_values('Funcionários', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao carregar o Dashboard: {e}")
