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
# Verifique se este ID está correto na sua barra de endereços do navegador
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkNiuSPtTe5Pw"
# Verifique se a aba se chama exatamente "Dados2"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados2"

@st.cache_data(ttl=600)
def load_data(url_link):
    try:
        df = pd.read_csv(url_link, dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        st.info("Verifique se a planilha está 'Publicada na Web' como CSV e se o nome da aba é 'Dados2'.")
        return None

def formata_reais(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df_raw = load_data(url)

if df_raw is not None:
    try:
        cols = df_raw.columns.tolist()

        # --- MAPEAMENTO DE COLUNAS ---
        col_data_criacao = cols[2]     # C
        col_data_pagamento = cols[23]  # X
        col_cliente = cols[4]          # E
        col_digitador = cols[15]       # P
        col_analise = cols[25]         # Z
        col_proposta = cols[26]        # AA
        col_motivo = cols[28]          # AC
        col_ticket = cols[29]          # AD
        col_nome_empresa = cols[33]    # AH
        col_cnpj = cols[34]            # AI
        col_func = cols[35]            # AJ

        # --- TRATAMENTO ---
        df_raw[col_ticket] = pd.to_numeric(df_raw[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
        df_raw[col_func] = pd.to_numeric(df_raw[col_func], errors='coerce').fillna(0)
        df_raw[col_data_criacao] = pd.to_datetime(df_raw[col_data_criacao], dayfirst=True, errors='coerce')
        df_raw[col_data_pagamento] = pd.to_datetime(df_raw[col_data_pagamento], dayfirst=True, errors='coerce')

        # --- FILTROS SIDEBAR ---
        st.sidebar.header("Filtros de Performance")
        data_min = df_raw[col_data_criacao].min().date() if not df_raw[col_data_criacao].dropna().empty else pd.Timestamp.now().date()
        data_max = df_raw[col_data_criacao].max().date() if not df_raw[col_data_criacao].dropna().empty else pd.Timestamp.now().date()
        
        periodo = st.sidebar.date_input("Período de Análise:", value=(data_min, data_max))
        
        lista_dig = sorted(df_raw[col_digitador].dropna().unique().tolist())
        selecionado = st.sidebar.selectbox("Selecione o Digitador:", ["Todos"] + lista_dig)

        # --- LÓGICA DE FILTRAGEM HÍBRIDA ---
        def filtrar_por_data_hibrida(df, start_date, end_date):
            # Se DISBURSED -> Data de Pagamento (X)
            cond_pago = (df[col_proposta].str.upper().str.strip() == 'DISBURSED') & \
                        (df[col_data_pagamento].dt.date >= start_date) & \
                        (df[col_data_pagamento].dt.date <= end_date)
            # Senão -> Data de Criação (C)
            cond_outros = (df[col_proposta].str.upper().str.strip() != 'DISBURSED') & \
                          (df[col_data_criacao].dt.date >= start_date) & \
                          (df[col_data_criacao].dt.date <= end_date)
            return df[cond_pago | cond_outros]

        df_periodo = filtrar_por_data_hibrida(df_raw, periodo[0], periodo[1])
        df_sel = df_periodo if selecionado == "Todos" else df_periodo[df_periodo[col_digitador] == selecionado]

        # --- INTERFACE ---
        st.title(f"Performance Topa+ | {selecionado}")
        
        # 1. KPIs
        vol_sel = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED'][col_ticket].sum()
        qtd_ativos = df_periodo[col_digitador].nunique()
        media_equipe = (df_periodo[df_periodo[col_proposta].str.upper().str.strip() == 'DISBURSED'][col_ticket].sum() / qtd_ativos) if qtd_ativos > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Meu Volume Pago", formata_reais(vol_sel))
        m2.metric("Média Equipe", formata_reais(media_equipe), delta=formata_reais(vol_sel - media_equipe))
        m3.metric("Digitadores no Período", f"{qtd_ativos} un")

        # 2. FUNIL COMPARATIVO (QTD E VALOR)
        st.divider()
        st.subheader("👥 Funil Comparativo de Digitadores")
        tab_q, tab_v = st.tabs(["Quantidade", "Valores (R$)"])
        
        with tab_q:
            df_q = df_periodo.groupby([col_digitador, col_proposta]).size().unstack(fill_value=0)
            st.dataframe(df_q.style.background_gradient(cmap='Greens', axis=1), use_container_width=True)
        with tab_v:
            df_v = df_periodo.groupby([col_digitador, col_proposta])[col_ticket].sum().unstack(fill_value=0)
            st.dataframe(df_v.applymap(formata_reais), use_container_width=True)

        # 3. DRILL DOWN INDIVIDUAL
        st.divider()
        st.subheader(f"🔍 Detalhes: {selecionado}")
        t1, t2, t3 = st.tabs(["💸 Pagos", "📋 Todos", "🚫 Reprovados"])
        with t1:
            st.dataframe(df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED'][[col_data_pagamento, col_cliente, col_ticket]], use_container_width=True)
        with t2:
            st.dataframe(df_sel[[col_data_criacao, col_cliente, col_proposta, col_ticket]], use_container_width=True)
        with t3:
            st.dataframe(df_sel[df_sel[col_analise].str.upper().str.strip() == 'REJECTED'][[col_cliente, col_motivo]], use_container_width=True)

        # 4. OPORTUNIDADES
        st.divider()
        st.subheader("🚀 Topa+ Oportunidades")
        df_pago_op = df_sel[df_sel[col_proposta].str.upper().str.strip() == 'DISBURSED']
        if not df_pago_op.empty:
            df_op = df_pago_op.groupby(col_cnpj).agg({col_nome_empresa:'first', col_func:'max', col_ticket:['count','sum']}).reset_index()
            df_op.columns = ['CNPJ','Empresa','Colab','Efetivados','Realizado']
            tkt = df_pago_op[col_ticket].mean()
            df_op['Potencial R$'] = df_op['Colab'] * tkt
            df_op['Gap R$'] = df_op['Potencial R$'] - df_op['Realizado']
            st.dataframe(df_op.sort_values('Colab', ascending=False).applymap(lambda x: formata_reais(x) if isinstance(x, (int, float)) and x > 1000 else x), use_container_width=True)

    except Exception as e:
        st.error(f"Erro na análise dos dados: {e}")
