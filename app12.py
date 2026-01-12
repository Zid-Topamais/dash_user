import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Dashboard Topa+", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkNiuSPtTe5Pw"
# Usamos gviz para exportar CSV da aba específica 'Dados2'
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados2"

@st.cache_data(ttl=600) # Atualiza a cada 10 minutos
def load_data():
    return pd.read_csv(url)

try:
    df_base = load_data()
    colunas_reais = df_base.columns.tolist()

    # --- TRATAMENTO ---
    col_data = colunas_reais[2]  # Coluna C
    col_ticket = colunas_reais[29] # Coluna AD (Ticket)
    col_digitadores = colunas_reais[15] # Coluna P
    
    df_base[col_data] = pd.to_datetime(df_base[col_data], errors='coerce')
    df_base[col_ticket] = pd.to_numeric(df_base[col_ticket], errors='coerce').fillna(0)
    df_base = df_base.dropna(subset=[col_data])

    # --- LOGO (GITHUB) ---
    # Se o arquivo estiver na raiz do seu repo com esse nome, ele vai ler
    logo = "topa (1).png" 
    if os.path.exists(logo):
        st.sidebar.image(logo, use_container_width=True)
    
    # --- FILTROS ---
    st.sidebar.header("Filtros")
    data_min, data_max = df_base[col_data].min().date(), df_base[col_data].max().date()
    periodo = st.sidebar.date_input("Período:", value=(data_min, data_max))

    df_filtrado = df_base.copy()
    if len(periodo) == 2:
        df_filtrado = df_filtrado[(df_filtrado[col_data].dt.date >= periodo[0]) & (df_filtrado[col_data].dt.date <= periodo[1])]

    # Filtros de Hierarquia
    for col_ref, label in zip(['Empresa', 'Squad', 'Digitado por'], ['Master (Q)', 'Equipe (R)', 'Digitador (P)']):
        col_real = next((c for c in colunas_reais if col_ref.upper() in str(c).upper()), None)
        if col_real:
            opc = ["Todos"] + sorted(df_filtrado[col_real].dropna().unique().astype(str).tolist())
            sel = st.sidebar.selectbox(label, opc)
            if sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_real] == sel]

    # --- LÓGICA DE STATUS ---
    col_analise = colunas_reais[25] # Coluna Z
    col_proposta = colunas_reais[26] # Coluna AA
    
    status_analise_limpo = df_filtrado[col_analise].fillna('VAZIO').astype(str).str.upper().str.strip()
    status_proposta_limpo = df_filtrado[col_proposta].fillna('VAZIO').astype(str).str.upper().str.strip()

    excluir_passivos = ['NOT_ANALIZED', 'NOT_ANALYZED', 'FAILED_DATAPREV', 'VAZIO', 'NAN', 'CREATED', 'TOKEN_SENT']
    lista_analisadas_base = ['NOT_AUTHORIZED_DATAPREV', 'SEM_DADOS_DATAPREV', 'CPF_EMPLOYER', 'NO_AVAILABLE_MARGIN']
    lista_gerados = ['CANCELLED_BY_USER', 'EXPIRED', 'CONTRACT_GENERATED', 'DISBURSED']

    # Dataframes de Status
    dfs = {
        "Simuladas": df_filtrado,
        "Passíveis": df_filtrado[~status_analise_limpo.isin(excluir_passivos)],
        "Analisadas": df_filtrado[(status_analise_limpo.isin(lista_analisadas_base)) | (status_analise_limpo == 'APPROVED')],
        "Aprovadas": df_filtrado[status_analise_limpo == 'APPROVED'],
        "Gerados": df_filtrado[status_proposta_limpo.isin(lista_gerados)],
        "Pagos": df_filtrado[status_proposta_limpo == 'DISBURSED']
    }

    def formata_reais(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # --- CONTAGEM HIERARQUIA ---
    qtd_digitadores_ativos = df_filtrado[col_digitadores].nunique()

    # --- INTERFACE ---
    st.title("Command Center | Topa & Bull")
    st.divider()

    # 1. FINANCEIRO
    with st.expander("💰 KPI's - Volume Financeiro (R$)", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Vol. Simuladas", formata_reais(dfs["Simuladas"][col_ticket].sum()))
        f2.metric("Vol. Passíveis", formata_reais(dfs["Passíveis"][col_ticket].sum()))
        f3.metric("Vol. Analisadas", formata_reais(dfs["Analisadas"][col_ticket].sum()))
        f4.metric("Vol. Aprovadas", formata_reais(dfs["Aprovadas"][col_ticket].sum()))

    # 2. QUANTITATIVO
    with st.expander("📊 KPI's - Fluxo de Propostas (Qtd)", expanded=True):
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Qtd. Simuladas", len(dfs["Simuladas"]))
        q2.metric("Qtd. Pagos", len(dfs["Pagos"]))
        q3.metric("Conversão Final", f"{(len(dfs['Pagos'])/len(dfs['Simuladas'])*100 if len(dfs['Simuladas'])>0 else 0):.2f}%")
        q4.metric("Aproveitamento", f"{(len(dfs['Aprovadas'])/len(dfs['Passíveis'])*100 if len(dfs['Passíveis'])>0 else 0):.1f}%")

    # 3. HIERARQUIA (AJUSTADO)
    with st.expander("👥 KPI's - Performance da Hierarquia", expanded=True):
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Digitadores Ativos", qtd_digitadores_ativos)
        
        # Cálculo de Médias por Digitador
        media_pago = (dfs["Pagos"][col_ticket].sum() / qtd_digitadores_ativos) if qtd_digitadores_ativos > 0 else 0
        media_qtd = (len(dfs["Pagos"]) / qtd_digitadores_ativos) if qtd_digitadores_ativos > 0 else 0
        
        h2.metric("Média R$ / Digitador", formata_reais(media_pago))
        h3.metric("Média Contratos / Digitador", f"{media_qtd:.1f}")
        h4.metric("Ticket Médio (Geral)", formata_reais(dfs["Pagos"][col_ticket].mean()) if len(dfs["Pagos"]) > 0 else "R$ 0,00")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
