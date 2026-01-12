import streamlit as st
import pandas as pd

# Configuração simples para foco total nos KPIs
st.set_page_config(page_title="KPI Financeiro | Benchmarking", layout="wide")

# --- CONEXÃO ---
sheet_id = "1_p5-a842gjyMoif57NdJLrUfccNkVptkNiuSPtTe5Pw"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Dados2"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(url, dtype=str)
    df.columns = df.columns.str.strip()
    return df

try:
    df_base = load_data()
    cols = df_base.columns.tolist()
    
    # Mapeamento
    col_data = cols[2]
    col_digitador = cols[15]
    col_status_pr = cols[26] # Coluna AA
    col_ticket = cols[29]    # Coluna AD

    # Tratamento Financeiro
    df_base[col_ticket] = pd.to_numeric(df_base[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_base[col_data] = pd.to_datetime(df_base[col_data], dayfirst=True, errors='coerce')

    # Filtros de Sidebar
    st.sidebar.header("Parâmetros de Comparação")
    lista_digitadores = sorted(df_base[col_digitador].dropna().unique().tolist())
    selecionado = st.sidebar.selectbox("Selecione o Digitador:", lista_digitadores)
    
    data_min, data_max = df_base[col_data].min().date(), df_base[col_data].max().date()
    periodo = st.sidebar.date_input("Período de Análise:", value=(data_min, data_max))

    # --- PROCESSAMENTO ---
    # 1. Filtrar apenas o período e apenas quem teve PAGAMENTO (DISBURSED)
    df_periodo = df_base[(df_base[col_data].dt.date >= periodo[0]) & (df_base[col_data].dt.date <= periodo[1])]
    df_pagos = df_periodo[df_periodo[col_status_pr].str.upper() == 'DISBURSED']

    # 2. Agrupamento por Digitador para Ranking e Média
    ranking_financeiro = df_pagos.groupby(col_digitador)[col_ticket].sum().sort_values(ascending=False)
    
    # 3. Definição das Variáveis de Comparação
    valor_selecionado = ranking_financeiro.get(selecionado, 0.0)
    
    # Média dos Digitadores Ativos (Quem pagou pelo menos 1 no período)
    qtd_ativos = len(ranking_financeiro)
    media_equipe = ranking_financeiro.mean() if qtd_ativos > 0 else 0
    
    # O Maior Digitador (Top 1)
    maior_valor = ranking_financeiro.max() if not ranking_financeiro.empty else 0
    nome_top1 = ranking_financeiro.index[0] if not ranking_financeiro.empty else "N/A"

    # --- INTERFACE DE KPI ---
    st.title(f"💰 Análise Financeira: {selecionado}")
    st.divider()

    def format_reais(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Layout em Colunas
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            label="Volume Pago (Individual)", 
            value=format_reais(valor_selecionado)
        )
        st.caption("Valor total liquidado pelo digitador.")

    with c2:
        delta_media = valor_selecionado - media_equipe
        st.metric(
            label="vs Média dos Ativos", 
            value=format_reais(media_equipe),
            delta=format_reais(delta_media)
        )
        st.caption(f"Baseado em {qtd_ativos} digitadores ativos.")

    with c3:
        delta_top = valor_selecionado - maior_valor
        st.metric(
            label=f"vs Top 1 ({nome_top1})", 
            value=format_reais(maior_valor),
            delta=format_reais(delta_top),
            delta_color="normal" 
        )
        st.caption("Distância para o líder do ranking.")

    # --- BARRA DE PROGRESSO VISUAL ---
    st.markdown("---")
    if maior_valor > 0:
        percentual_do_lider = (valor_selecionado / maior_valor)
        st.write(f"**Aproveitamento em relação ao líder:** {percentual_do_lider*100:.1f}%")
        st.progress(percentual_do_lider)

except Exception as e:
    st.error(f"Erro ao processar KPIs: {e}")
