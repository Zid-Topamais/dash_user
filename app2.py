import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Ativação de Parceiros", layout="wide")

## 1. Carregamento dos Dados
# Considerando que os CSVs estão no mesmo diretório
df_user = pd.read_csv('meu_banco.xlsx - app_topamais_user.csv')
df_company = pd.read_csv('meu_banco.xlsx - app_topamais_company.csv')
df_squad = pd.read_csv('meu_banco.xlsx - app_topamais_squad.csv')
df_user_company = pd.read_csv('meu_banco.xlsx - app_topamais_user_company.csv')
df_user_squad = pd.read_csv('meu_banco.xlsx - app_topamais_user_squad.csv')

## 2. Processamento (Joins)
# Cruzando Usuário com Empresa
df_merge = df_user_company.merge(df_company[['id', 'name']], left_on='company_id', right_on='id', suffixes=('', '_company'))
df_merge = df_merge.merge(df_user[['id', 'name', 'created_at']], on='user_id')

# Cruzando com Squad
df_merge = df_merge.merge(df_user_squad, on='user_id', how='left')
df_merge = df_merge.merge(df_squad[['id', 'name']], left_on='squad_id', right_on='id', how='left', suffixes=('_co', '_sq'))

## 3. Limpeza e Organização
# Selecionando e renomeando as colunas na sequência exata pedida
df_final = df_merge[[
    'name_co',   # Empresa (Company Name)
    'name_sq',   # Squad (Squad Name)
    'name',      # Parceiro (User Name)
    'created_at' # Data de Criação
]].copy()

df_final.columns = ['Empresa', 'Squad', 'Parceiro', 'Data de Criação']
df_final['Data de Criação'] = pd.to_datetime(df_final['Data de Criação']).dt.strftime('%d/%m/%Y %H:%M')

## 4. Interface Streamlit
st.title("🚀 Ativação de Parceiros")
st.markdown("Relatório detalhado de entrada de novos parceiros por estrutura.")

# Filtros rápidos (opcional)
col1, col2 = st.columns(2)
with col1:
    empresa_filter = st.multiselect("Filtrar Empresa", options=df_final['Empresa'].unique())
with col2:
    squad_filter = st.multiselect("Filtrar Squad", options=df_final['Squad'].unique())

if empresa_filter:
    df_final = df_final[df_final['Empresa'].isin(empresa_filter)]
if squad_filter:
    df_final = df_final[df_final['Squad'].isin(squad_filter)]

# Exibição da Tabela
st.dataframe(df_final, use_container_width=True, hide_index=True)

# Métrica simples de resumo
st.sidebar.metric("Total de Parceiros", len(df_final))
