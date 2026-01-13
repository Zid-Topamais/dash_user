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

    # --- MAPEAMENTO DE COLUNAS ---
    col_data_pagamento = cols[23]  # Coluna X (Data de Pagamento) - Referência Principal
    col_cliente = cols[4]          # Coluna E
    col_digitador = cols[15]       # Coluna P
    col_analise = cols[25]         # Coluna Z
    col_proposta = cols[26]        # Coluna AA
    col_motivo = cols[28]          # Coluna AC
    col_ticket = cols[29]          # Coluna AD
    col_nome_empresa = cols[33]     # Coluna AH
    col_cnpj = cols[34]            # Coluna AI
    col_func = cols[35]            # Coluna AJ

    # --- TRATAMENTO DE DADOS ---
    df_raw[col_ticket] = pd.to_numeric(df_raw[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_raw[col_func] = pd.to_numeric(df_raw[col_func], errors='coerce').fillna(0)
    
    # Tratando a Data de Pagamento (Coluna X)
    df_raw[col_data_pagamento] = pd.to_datetime(df_raw[col_data_pagamento], dayfirst=True, errors='coerce')
    # Para análise de funil completo, mantemos os registros, mas para o filtro principal usamos a Coluna X
    df_base = df_raw.copy()

    # --- SIDEBAR FILTROS ---
    st.sidebar.header("Filtros por Data de Pagamento")
    
    # Definindo o range de datas baseado na coluna X
    data_ref = df_base[df_base[col_data_pagamento].notnull()]
    if not data_ref.empty:
        data_min, data_max = data_ref[col_data_pagamento].min().date(), data_ref[col_data_pagamento].max().date()
    else:
        data_min, data_max = pd.Timestamp.now().date(), pd.Timestamp.now().date()
        
    periodo = st.sidebar.date_input("Período de Pagamento:", value=(data_min, data_max))

    lista_dig = sorted(df_base[col_digitador].dropna().unique().tolist())
    selecionado = st.sidebar.selectbox("Selecione o Digitador para Análise Individual:", lista_dig)

    # --- FILTRAGEM ---
    # Filtro de período aplicado na Coluna X (Data de Pagamento)
    df_periodo = df_base[
        (df_base[col_data_pagamento].dt.date >= periodo[0]) & 
        (df_base[col_data_pagamento].dt.date <= periodo[1])
    ]
    
    df_sel = df_periodo[df_periodo[col_digitador] == selecionado]

    # --- PROCESSAMENTO DE MÉTRICAS ---
    def get_metrics(df_input):
        pagos = df_input[df_input[col_proposta].str.upper().str.strip() == 'DISBURSED']
        return {
            "vol_pago": pagos[col_ticket].sum(),
            "qtd_pago": len(pagos),
            "ticket_medio": pagos[col_ticket].mean() if len(pagos) > 0 else 0,
            "simuladas": len(df_input)
        }

    m_sel = get_metrics(df_sel)
    
    # Benchmarking
    ranking_vol = df_periodo[df_periodo[col_proposta].str.upper().str.strip() == 'DISBURSED'].groupby(col_digitador)[col_ticket].sum().sort_values(ascending=False)
    top_nome = ranking_vol.index[0] if not ranking_vol.empty else "N/A"
    m_top = get_metrics(df_periodo[df_periodo[col_digitador] == top_nome])
    
    qtd_ativos = df_periodo[col_digitador].nunique()
    vol_total_equipe = df_periodo[df_periodo[col_proposta].str.upper().str.strip() == 'DISBURSED'][col_ticket].sum()
    media_vol = vol_total_equipe / qtd_ativos if qtd_ativos > 0 else 0

    # --- INTERFACE ---
    st.title(f"Performance Topa+ | {selecionado}")
    st.caption(f"Referência: Data de Pagamento (Coluna X) entre {periodo[0]} e {periodo[1]}")

    # 1. FINANCEIRO
    st.subheader("💰 Volume Pago no Período")
    c1, c2, c3 = st.columns(3)
    c1.metric("Meu Volume", formata_reais(m_sel["vol_pago"]))
    c2.metric("Média Equipe", formata_reais(media_vol), delta=formata_reais(m_sel["vol_pago"] - media_vol))
    c3.metric(f"Top 1 ({top_nome})", formata_reais(m_top["vol_pago"]), delta=formata_reais(m_sel["vol_pago"] - m_top["vol_pago"]), delta_color="normal")

    # 2. FUNIL DE EQUIPE (TABELA GERAL)
    st.divider()
    st.subheader("👥 Funil Geral de Digitadores")
    with st.expander("Ver Comparativo de Status (Qtd e Valor)", expanded=True):
        aba_qtd, aba_val = st.tabs(["Quantidade de Propostas", "Valor Total (R$)"])
        
        with aba_qtd:
            df_pivot_qtd = df_periodo.groupby([col_digitador, col_proposta]).size().unstack(fill_value=0)
            st.dataframe(df_pivot_qtd.style.background_gradient(cmap='Greens', axis=1), use_container_width=True)
            
        with aba_val:
            df_pivot_val = df_periodo.groupby([col_digitador, col_proposta])[col_ticket].sum().unstack(fill_value=0)
            st.dataframe(df_pivot_val.applymap(formata_reais), use_container_width=True)

    # 3. DRILL DOWN INDIVIDUAL
    st.divider()
    st.subheader(f"🔍 Drill Down: {selecionado}")
    t1, t2, t3 = st.tabs(["💸 Pagos (Disbursed)", "📋 Todas as Simuladas", "🚫 Reprovadas"])
    
    with t1:
        df_p = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED']
        st.dataframe(df_p[[col_data_pagamento, col_cliente, col_nome_empresa, col_ticket]], use_container_width=True)
    with t2:
        st.dataframe(df_sel[[col_cliente, col_analise, col_proposta, col_ticket]], use_container_width=True)
    with t3:
        df_r = df_sel[df_sel[col_analise].str.upper().str.strip() == 'REJECTED']
        st.dataframe(df_r[[col_cliente, col_motivo, col_ticket]], use_container_width=True)

    # 4. TOPA+ OPORTUNIDADES
    st.divider()
    st.subheader("🚀 Topa+ Oportunidades (Carteira Paga)")
    df_pago_op = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED']
    
    if not df_pago_op.empty:
        df_op = df_pago_op.groupby(col_cnpj).agg({
            col_nome_empresa: 'first',
            col_func: 'max',
            col_ticket: ['count', 'sum']
        }).reset_index()
        df_op.columns = ['CNPJ', 'Empresa', 'Total_Funcionarios', 'Efetivados', 'Volume_Realizado']
        
        tkt_medio = m_sel["ticket_medio"]
        df_op['Potencial_R$'] = df_op['Total_Funcionarios'] * tkt_medio
        df_op['Gap_Oportunidade'] = df_op['Potencial_R$'] - df_op['Volume_Realizado']
        
        # Formatação
        df_op_view = df_op.copy()
        for col in ['Volume_Realizado', 'Potencial_R$', 'Gap_Oportunidade']:
            df_op_view[col] = df_op_view[col].apply(formata_reais)
            
        st.dataframe(df_op_view.sort_values('Total_Funcionarios', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Selecione um período com pagamentos realizados para ver as oportunidades.")

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
