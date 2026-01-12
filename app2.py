
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

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
        transition: transform 0.3s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
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
    col_estado = colunas_reais[6]  # Estado (G)
    col_data = colunas_reais[2]  # Coluna C
    col_ticket = 'ticket' if 'ticket' in colunas_reais else colunas_reais[29] # Coluna AD
    col_digitadores = colunas_reais[15] # Coluna P

    # Mapeamento específico para as colunas de CNPJ e Ticket
    col_ticket = 'ticket' if 'ticket' in colunas_reais else colunas_reais[29]
    col_cnpj = 'employer_document' if 'employer_document' in colunas_reais else colunas_reais[34]
    col_func = 'qtde_funcionarios' if 'qtde_funcionarios' in colunas_reais else colunas_reais[35]

    

    # --- TRATAMENTO DE TICKET ---
    df_base[col_ticket] = df_base[col_ticket].fillna('0').astype(str).str.strip()
    df_base[col_ticket] = df_base[col_ticket].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df_base[col_ticket] = pd.to_numeric(df_base[col_ticket], errors='coerce').fillna(0)

    # --- TRATAMENTO DE DATA (AJUSTE CRÍTICO) ---
    # Usamos dayfirst=True para evitar que 05/01 vire 01 de Maio
    df_base[col_data] = pd.to_datetime(df_base[col_data], dayfirst=True, errors='coerce')
    df_base = df_base.dropna(subset=[col_data])

    # --- SIDEBAR ---
    logo = "topa (1).png" 
    if os.path.exists(logo):
        st.sidebar.image(logo, use_container_width=True)
    
    st.sidebar.header("Filtros")
    data_min, data_max = df_base[col_data].min().date(), df_base[col_data].max().date()
    periodo = st.sidebar.date_input("Período:", value=(data_min, data_max))

    df_filtrado = df_base.copy()
    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        # Filtro comparando apenas a data (ignora a hora da planilha)
        df_filtrado = df_filtrado[(df_filtrado[col_data].dt.date >= periodo[0]) & (df_filtrado[col_data].dt.date <= periodo[1])]

    # Filtros Hierárquicos
    for col_ref, label in zip(['Empresa', 'Squad', 'Digitado por'], ['Master (Q)', 'Equipe (R)', 'Digitador (P)']):
        col_real = next((c for c in colunas_reais if col_ref.upper() in str(c).upper()), None)
        if col_real:
            opc = ["Todos"] + sorted(df_filtrado[col_real].dropna().unique().astype(str).tolist())
            sel = st.sidebar.selectbox(label, opc)
            if sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_real] == sel]

    # --- LÓGICA DE STATUS ---
    col_analise = colunas_reais[25] # Coluna Z
    col_proposta = colunas_reais[26] # Coluna AA
    col_descricao_status_proposta = colunas_reais[27] # Coluna AB
    col_motivo_da_decisao = colunas_reais[28] # Coluna AC
         
    status_analise_limpo = df_filtrado[col_analise].fillna('VAZIO').astype(str).str.upper().str.strip()
    status_proposta_limpo = df_filtrado[col_proposta].fillna('VAZIO').astype(str).str.upper().str.strip()

    excluir_passivos = ['NOT_ANALIZED', 'NOT_ANALYZED', 'FAILED_DATAPREV', 'VAZIO', 'NAN', 'CREATED', 'TOKEN_SENT']
    lista_analisadas_base = ['REJECTED']
    lista_gerados = ['CANCELLED_BY_USER', 'EXPIRED', 'CONTRACT_GENERATED', 'DISBURSED']

    dfs = {
        "Simuladas": df_filtrado,
        "Passíveis": df_filtrado[~status_analise_limpo.isin(excluir_passivos)],
        "Analisadas": df_filtrado[(status_analise_limpo.isin(lista_analisadas_base)) | (status_analise_limpo == 'APPROVED')],
        "Aprovadas": df_filtrado[status_analise_limpo == 'APPROVED'],
        "Gerados": df_filtrado[status_proposta_limpo.isin(lista_gerados)],
        "Pagos": df_filtrado[status_proposta_limpo == 'DISBURSED'],
    }

    def formata_reais(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # --- INTERFACE ---
    st.title("Command Center | Topa & Bull")
    st.divider()

    # 1. FINANCEIRO
    with st.expander("💰 KPI's - Volume Financeiro (R$)", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Propostas Aprovadas", formata_reais(dfs["Aprovadas"][col_ticket].sum()))
        f2.metric("Contratos Gerados", formata_reais(dfs["Gerados"][col_ticket].sum()))
        f3.metric("Contratos Pagos", formata_reais(dfs["Pagos"][col_ticket].sum()))
        ticket_medio = dfs["Pagos"][col_ticket].mean() if len(dfs["Pagos"]) > 0 else 0
        f4.metric("Ticket Médio (Pagos)", formata_reais(ticket_medio))

        st.markdown("---")
        c1, c2, = st.columns(2)      
        vol_total = dfs["Simuladas"][col_ticket].sum()
        vol_gerados = dfs["Gerados"][col_ticket].sum()
        vol_pagos = dfs["Pagos"][col_ticket].sum()
        c1.metric("Conversão Simulados x Pagos", f"{(vol_pagos/vol_total*100 if vol_total > 0 else 0):.2f}%")
        c2.metric("Conversão Contratos Gerados x Pagos", f"{(vol_pagos/vol_gerados*100 if vol_gerados > 0 else 0):.2f}%")

    # 2. QUANTITATIVO
    with st.expander("📊 KPI's - Fluxo de Propostas (Qtd)", expanded=True):
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Qtd. Simuladas", len(dfs["Simuladas"]))
        q2.metric("Qtd. Passíveis", len(dfs["Passíveis"]))
        q3.metric("Qtd. Analisadas", len(dfs["Analisadas"]))
        q4.metric("Qtd. Aprovadas", len(dfs["Aprovadas"]))
        st.markdown("---")
        q5, q6, q7, q8 = st.columns(4)
        q5.metric("Contratos Gerados", len(dfs["Gerados"]))
        q6.metric("Contratos Pagos", len(dfs["Pagos"]))
        q7.metric("Conversão Final", f"{(len(dfs['Pagos'])/len(dfs['Simuladas'])*100 if len(dfs['Simuladas'])>0 else 0):.2f}%")
        q8.metric("Aproveitamento", f"{(len(dfs['Aprovadas'])/len(dfs['Passíveis'])*100 if len(dfs['Passíveis'])>0 else 0):.1f}%")

   True)



 

    # 4. EVOLUÇÃO DIÁRIA (COM SELETOR DE PERÍODO RESTAURADO)
    st.markdown("---")
    st.subheader("📈 Evolução de Pagamentos Diários")
    col_filtro1, col_filtro2 = st.columns([1, 2])
    with col_filtro1:
        opcao_data = st.selectbox("Filtrar período do gráfico:", ["Tudo (Filtro Lateral)", "Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias", "Personalizado (Comparativo)"])

    df_grafico = dfs["Pagos"].copy()
    hoje = pd.Timestamp.now().normalize()

    if opcao_data == "Últimos 7 dias":
        df_grafico = df_grafico[df_grafico[col_data] >= (hoje - pd.Timedelta(days=7))]
    elif opcao_data == "Últimos 15 dias":
        df_grafico = df_grafico[df_grafico[col_data] >= (hoje - pd.Timedelta(days=15))]
    elif opcao_data == "Últimos 30 dias":
        df_grafico = df_grafico[df_grafico[col_data] >= (hoje - pd.Timedelta(days=30))]
    elif opcao_data == "Personalizado (Comparativo)":
        with col_filtro2:
            data_comp = st.date_input("Início da comparação:", value=hoje.date() - pd.Timedelta(days=30))
            df_grafico = df_base[(df_base[col_data].dt.date >= data_comp) & (df_base[col_data].dt.date <= data_comp + pd.Timedelta(days=30))]

    if not df_grafico.empty:
        df_pagos_diario = df_grafico.groupby(df_grafico[col_data].dt.date)[col_ticket].sum().reset_index()
        df_pagos_diario.columns = ['Data', 'Volume Pago']
        df_pagos_diario['Dia'] = pd.to_datetime(df_pagos_diario['Data']).dt.day.astype(str)
        fig_diario = go.Figure(go.Bar(x=df_pagos_diario['Dia'], y=df_pagos_diario['Volume Pago'], marker_color='#008080'))
        st.plotly_chart(fig_diario, use_container_width=True)

    # 5. REPROVADAS E RADAR (RESTAURADO COMPLETO)
    df_reprovadas = df_filtrado[status_analise_limpo == 'REJECTED'].copy()
    
    with st.expander("🚫 Detalhamento de Propostas Reprovadas", expanded=True):
        if not df_reprovadas.empty:
            df_drill_down = df_reprovadas[[col_data, col_digitadores, col_analise, col_proposta, col_descricao_status_proposta, col_motivo_da_decisao]].copy()
            
            def aplicar_depara_inteligente(texto):
                t = str(texto).strip()
                if 'Valor margem rejeitado' in t: return 'Cliente sem margem'
                if 'Faixa de Renda' in t: return 'Faixa de Renda < 1 Salário Mínimo'
                if 'Tempo de Emprego' in t: return 'Tempo de Emprego < 3 meses'
                if 'etaria' in t: return 'Faixa etaria inadequada'
                if 'CPF Nao Esta Regular' in t: return 'CPF Irregular'
                if t.upper() in ['NAN', '#N/A', '', 'NONE', '0']: return "Análise Técnica"
                return t

            df_drill_down[col_motivo_da_decisao] = df_drill_down[col_motivo_da_decisao].apply(aplicar_depara_inteligente)
            contagem_motivos = df_drill_down[col_motivo_da_decisao].value_counts()
            cols_motivos = st.columns(4)
            for i, (motivo, qtd) in enumerate(contagem_motivos.items()):
                with cols_motivos[i % 4]:
                    st.markdown(f'<div style="background-color:#E0F7FA; padding:10px; border-radius:10px; border-left: 5px solid #00BCD4; margin-bottom:10px;"><p style="margin:0; font-size:11px; font-weight:bold;">{motivo}</p><h3>{int(qtd)}</h3></div>', unsafe_allow_html=True)
            
            df_exibir = df_drill_down.copy()
            df_exibir[col_data] = df_exibir[col_data].dt.strftime('%d/%m/%Y')
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

    # 6. RADAR DE NEGÓCIOS (RESTAURADO COMPLETO)
    with st.expander("🎯 RADAR DE NEGÓCIOS - Motivos Críticos", expanded=True):
        motivos_radar = ['Tempo de Emprego < 3 meses', 'Cliente sem margem', 'Possui Alertas - Férias ou afastamento', 'CPF Irregular', 'Faixa de Renda < 1 Salário Mínimo']
        if not df_reprovadas.empty:
            df_radar_focado = df_drill_down[df_drill_down[col_motivo_da_decisao].isin(motivos_radar)].copy()
            contagem_radar = df_radar_focado[col_motivo_da_decisao].value_counts()
            c1, c2, c3 = st.columns(3)
            for i, motivo in enumerate(motivos_radar):
                qtd = contagem_radar.get(motivo, 0)
                with [c1, c2, c3][i % 3]:
                    st.markdown(f'<div style="background-color:#FFF3E0; padding:12px; border-radius:10px; border-left: 5px solid #FF9800; margin-bottom:10px;"><p style="margin:0; font-size:12px; font-weight:bold;">{motivo}</p><h2>{int(qtd)}</h2></div>', unsafe_allow_html=True)

            if st.button("🔍 Ver Lista de Clientes (Tempo de Emprego)"):
                indices = df_drill_down[df_drill_down[col_motivo_da_decisao] == 'Tempo de Emprego < 3 meses'].index
                df_oportunidade = df_filtrado.loc[indices].copy()
                if not df_oportunidade.empty:
                    st.write(df_oportunidade[[colunas_reais[4], colunas_reais[36]]])

except Exception as e:
    st.error(f"Erro: {e}")
