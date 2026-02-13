import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard Topa+", layout="wide")

# 2. Conexão com o Banco de Dados
# Nota: Em produção, coloque essa URL no arquivo .streamlit/secrets.toml
DB_URL = "postgresql://neondb_owner:npg_BaxWC3beIzq6@ep-shy-dew-accl78ee-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

@st.cache_data(ttl=600)  # Atualiza os dados a cada 10 minutos
def load_data_from_db():
    engine = create_engine(DB_URL)
    
    # Query que faz os JOINS necessários para pegar os nomes em vez de IDs
    query = """
    SELECT 
        c.name as "Empresa",
        s.name as "Squad",
        u.name as "Parceiro",
        u.created_at as "Data de Criação"
    FROM app_topamais_user u
    JOIN app_topamais_user_company uc ON u.id = uc.user_id
    JOIN app_topamais_company c ON uc.company_id = c.id
    LEFT JOIN app_topamais_user_squad us ON u.id = us.user_id
    LEFT JOIN app_topamais_squad s ON us.squad_id = s.id
    ORDER BY u.created_at DESC
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

# 3. Interface do Streamlit
st.title("🚀 Ativação de Parceiros")

try:
    # Carregando os dados
    df_final = load_data_from_db()

    # Formatação da data para o padrão BR (DD/MM/AAAA)
    df_final['Data de Criação'] = pd.to_datetime(df_final['Data de Criação']).dt.strftime('%d/%m/%Y %H:%M')

    # --- Filtros no Topo ---
    col1, col2 = st.columns(2)
    with col1:
        lista_empresas = sorted(df_final['Empresa'].unique())
        empresa_selecionada = st.multiselect("Filtrar por Empresa", options=lista_empresas)
        
    with col2:
        # Remove nulos para o filtro de squad
        lista_squads = sorted(df_final['Squad'].dropna().unique())
        squad_selecionado = st.multiselect("Filtrar por Squad", options=lista_squads)

    # Aplicando filtros
    if empresa_selecionada:
        df_final = df_final[df_final['Empresa'].isin(empresa_selecionada)]
    if squad_selecionado:
        df_final = df_final[df_final['Squad'].isin(squad_selecionado)]

    # --- Exibição da Tabela Principal ---
    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Data de Criação": st.column_config.TextColumn("Data de Cadastro")
        }
    )

    # --- Resumo Lateral (Sidebar) ---
    st.sidebar.header("Métricas Atuais")
    st.sidebar.metric("Total de Parceiros", len(df_final))
    
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.error(f"Erro ao conectar ou processar dados: {e}")
