

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Performance Individual | Topa+", layout="wide")

# --- ESTILIZAÇÃO (TURQUESA) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #99FFFF !important; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border-left: 5px solid #00CCCC !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
    }
    .highlight { color: #008080; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO ---
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
    col_status_an = cols[25]
    col_status_pr = cols[26]
    col_motivo = cols[28]
    col_ticket = cols[29]

    # Tratamento
    df_base[col_ticket] = pd.to_numeric(df_base[col_ticket].str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
    df_base[col_data] = pd.to_datetime(df_base[col_data], dayfirst=True, errors='coerce')
    df_base = df_base.dropna(subset=[col_data])

    # --- FILTROS SIDEBAR ---
    st.sidebar.header("Análise Individual")
    
    # 1. Filtro de Digitador (Obrigatório selecionar um)
    lista_digitadores = sorted(df_base[col_digitador].dropna().unique().tolist())
    selecionado = st.sidebar.selectbox("Escolha o Digitador para Análise:", lista_digitadores)
    
    # 2. Filtro de Período
    data_min, data_max = df_base[col_data].min().date(), df_base[col_data].max().date()
    periodo = st.sidebar.date_input("Período:", value=(data_min, data_max))

    # Filtragem Base
    df_periodo = df_base[(df_base[col_data].dt.date >= periodo[0]) & (df_base[col_data].dt.date <= periodo[1])]
    
    # Separação de Dados
    df_individuo = df_periodo[df_periodo[col_digitador] == selecionado]
    # Média do grupo (excluindo o selecionado para um comparativo real, ou mantendo todos)
    df_grupo = df_periodo 

    # --- CÁLCULOS DE KPI ---
    def get_metrics(df):
        pagos = df[df[col_status_pr].str.upper() == 'DISBURSED']
        aprov = df[df[col_status_an].str.upper() == 'APPROVED']
        return {
            "vol_pago": pagos[col_ticket].sum(),
            "qtd_pago": len(pagos),
            "ticket_medio": pagos[col_ticket].mean() if len(pagos) > 0 else 0,
            "conversao": (len(pagos) / len(df) * 100) if len(df) > 0 else 0
        }

    m_ind = get_metrics(df_individuo)
    
    # Média por digitador do grupo
    digitadores_ativos = df_grupo[col_digitador].nunique()
    m_grupo = {
        "vol_pago": df_grupo[df_grupo[col_status_pr].str.upper() == 'DISBURSED'][col_ticket].sum() / digitadores_ativos,
        "qtd_pago": len(df_grupo[df_grupo[col_status_pr].str.upper() == 'DISBURSED']) / digitadores_ativos,
        "ticket_medio": df_grupo[df_grupo[col_status_pr].str.upper() == 'DISBURSED'][col_ticket].mean()
    }

    # --- INTERFACE ---
    st.title(f"Performance: {selecionado}")
    st.markdown(f"Análise de **{periodo[0].strftime('%d/%m/%Y')}** até **{periodo[1].strftime('%d/%m/%Y')}**")

    # 1. KPIs COMPARATIVOS
    st.subheader("📊 Comparativo vs Média da Equipe")
    c1, c2, c3 = st.columns(3)
    
    def format_reais(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    with c1:
        delta = m_ind["vol_pago"] - m_grupo["vol_pago"]
        st.metric("Volume Pago", format_reais(m_ind["vol_pago"]), delta=format_reais(delta))
        st.caption(f"Média Equipe: {format_reais(m_grupo['vol_pago'])}")

    with c2:
        delta_qtd = m_ind["qtd_pago"] - m_grupo["qtd_pago"]
        st.metric("Contratos Pagos", f"{m_ind['qtd_pago']} un", delta=f"{delta_qtd:.1f}")
        st.caption(f"Média Equipe: {m_grupo['qtd_pago']:.1f} un")

    with c3:
        st.metric("Conversão Individual", f"{m_ind['conversao']:.2f}%")
        st.progress(m_ind['conversao'] / 100)

    st.divider()

    # 2. RADAR DE MOTIVOS DO DIGITADOR
    st.subheader("🚫 Motivos de Reprovação do Digitador")
    df_repro = df_individuo[df_individuo[col_status_an].str.upper() == 'REJECTED']
    
    if not df_repro.empty:
        motivos = df_repro[col_motivo].value_counts()
        cols_m = st.columns(len(motivos.head(4)))
        for i, (motivo, qtd) in enumerate(motivos.head(4).items()):
            cols_m[i].markdown(f"""
                <div style="background:#FFF3E0; padding:10px; border-radius:10px; border-left:4px solid #FF9800">
                    <small>{motivo[:25]}...</small>
                    <h3>{qtd}</h3>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Nenhuma reprovação para este digitador no período!")

    # 3. EVOLUÇÃO DIÁRIA DO DIGITADOR
    st.subheader("📈 Evolução de Produção (R$)")
    df_evol = df_individuo.groupby(df_individuo[col_data].dt.date)[col_ticket].sum().reset_index()
    fig = go.Figure(go.Scatter(x=df_evol[col_data], y=df_evol[col_ticket], fill='tozeroy', line_color='#008080'))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar análise do digitador: {e}")

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

    # 3. HIERARQUIA
    with st.expander("👥 KPI's - Performance da Hierarquia", expanded=True):
        h1, h2, h3, h4 = st.columns(4)
        df_pagos = dfs["Pagos"]
        qtd_ativos_pagos = df_pagos[col_digitadores].nunique() if not df_pagos.empty else 0
        h1.metric("Digitadores Ativos (Pagos)", qtd_ativos_pagos)
        total_pago_hierarquia = df_pagos[col_ticket].sum()
        media_pago = (total_pago_hierarquia / qtd_ativos_pagos) if qtd_ativos_pagos > 0 else 0
        h2.metric("Média R$ / Digitador", formata_reais(media_pago))
        media_qtd = (len(df_pagos) / qtd_ativos_pagos) if qtd_ativos_pagos > 0 else 0
        h3.metric("Média Contratos / Digitador", f"{media_qtd:.1f}")
        ticket_medio_pagos = df_pagos[col_ticket].mean() if len(df_pagos) > 0 else 0
        h4.metric("Ticket Médio (Pagos)", formata_reais(ticket_medio_pagos))

        st.markdown("---")
        st.subheader("🏆 Top 10 Digitadores - Performance (Pagos)")
        if not df_pagos.empty:
            top_10 = df_pagos.groupby(col_digitadores)[col_ticket].sum().sort_values(ascending=False).head(10).reset_index()
            fig_top = go.Figure(go.Bar(
                x=top_10[col_ticket], y=top_10[col_digitadores], orientation='h',
                marker_color='#00CCCC', text=top_10[col_ticket].apply(formata_reais), textposition='auto'
            ))
            fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
            st.plotly_chart(fig_top, use_container_width=True)



 

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
    
