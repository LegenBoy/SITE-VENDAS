import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MetaVendas App",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS PARA VISUAL ---
st.markdown("""
<style>
    .stButton > button { border-radius: 20px; font-weight: bold; height: 3em; }
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important; object-fit: cover !important;
        aspect-ratio: 1 / 1 !important; border: 3px solid #2E86C1;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f9f9f9; border-radius: 15px; margin-bottom: 10px;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #262730;
        }
    }
    .card-title { font-size: 18px; font-weight: bold; color: #2E86C1; }
    .card-valor { font-size: 20px; font-weight: bold; color: #28a745; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- 3. CONEXÃO E FUNÇÕES ÚTEIS ---
def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB")

# --- CONVERSÃO DE VALOR ---
def converter_para_float(valor_texto):
    if not valor_texto: return 0.0
    # Remove R$, pontos de milhar e troca vírgula por ponto
    v = str(valor_texto).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

# --- 4. FUNÇÕES DE BANCO DE DADOS (GOOGLE SHEETS) ---
def carregar_vendas():
    colunas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        if df.empty: return pd.DataFrame(columns=colunas)
        df['Pedido'] = df['Pedido'].astype(str)
        # Garante que o valor lido do Sheets seja tratado como número
        df['Valor'] = df['Valor'].apply(lambda x: converter_para_float(x))
        return df
    except: return pd.DataFrame(columns=colunas)

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [
            str(nova_venda["Data"]), 
            str(nova_venda["Pedido"]), 
            nova_venda["Vendedor"], 
            nova_venda["Retira_Posterior"], 
            nova_venda["Valor"], 
            str(nova_venda["Pedido_Origem"])
        ]
        ws.append_row(linha)
        return True
    except: return False

def atualizar_venda(id_original, dados_novos):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        cell = ws.find(str(id_original))
        linha_num = cell.row
        nova_linha = [str(dados_novos["Data"]), str(dados_novos["Pedido"]), dados_novos["Vendedor"],
                      dados_novos["Retira_Posterior"], float(dados_novos["Valor"]), str(dados_novos["Pedido_Origem"])]
        ws.update(f"A{linha_num}:F{linha_num}", [nova_linha])
        return True
    except: return False

def carregar_usuarios():
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        return pd.DataFrame(ws.get_all_records())
    except: return pd.DataFrame(columns=["Usuario", "Senha", "Nome", "Funcao", "Foto_URL"])

# --- CALLBACK DE SALVAMENTO COM LIMPEZA ---
def processar_salvamento():
    # Coleta dados dos inputs via session_state
    data = st.session_state.form_data
    pedido = st.session_state.form_pedido
    valor_txt = st.session_state.form_valor
    retira = st.session_state.form_retira
    origem = st.session_state.form_origem if retira else "-"
    usuario_atual = st.session_state['usuario_nome_sistema']

    valor_final = converter_para_float(valor_txt)
    
    if pedido and valor_final > 0:
        nova = {
            "Data": data, "Pedido": pedido, "Vendedor": usuario_atual,
            "Retira_Posterior": "Sim" if retira else "Não", 
            "Valor": valor_final, "Pedido_Origem": origem
        }
        
        if salvar_venda(nova):
            # LIMPA OS CAMPOS APÓS SALVAR
            st.session_state.form_pedido = ""
            st.session_state.form_valor = ""
            st.session_state.form_origem = ""
            st.session_state.form_retira = False
            st.toast("✅ Venda salva com sucesso!", icon="🚀")
            time.sleep(1)
    else:
        st.error("Preencha o Pedido e o Valor corretamente.")

# --- 5. LOGIN ---
def autenticar(usuario, senha):
    df = carregar_usuarios()
    if df.empty: return None
    user_row = df[df["Usuario"] == usuario]
    if not user_row.empty and str(user_row.iloc[0]["Senha"]) == str(senha):
        return user_row.iloc[0]
    return None

# --- 6. INTERFACE PRINCIPAL ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login MetaVendas")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("ENTRAR", use_container_width=True):
        dados = autenticar(u, s)
        if dados is not None:
            st.session_state.update({'logado': True, 'usuario': dados["Usuario"], 'usuario_nome_sistema': dados["Nome"], 'funcao': dados["Funcao"]})
            st.rerun()
        else: st.error("Incorreto.")
else:
    st.sidebar.title(f"👤 {st.session_state['usuario_nome_sistema']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    tab1, tab2 = st.tabs(["📝 Lançar Venda", "📋 Ver Relatório"])

    with tab1:
        st.subheader("Novo Lançamento")
        with st.container(border=True):
            st.date_input("Data", date.today(), key="form_data")
            st.text_input("Nº Pedido", key="form_pedido")
            st.text_input("Valor (Ex: 1874,97)", key="form_valor")
            st.toggle("Retira Posterior?", key="form_retira")
            
            # Campo origem só aparece se o toggle for verdadeiro
            if st.session_state.form_retira:
                st.text_input("Vínculo (Pedido Origem)", key="form_origem")
            
            st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True, on_click=processar_salvamento)

    with tab2:
        st.subheader("Histórico de Vendas")
        df_vendas = carregar_vendas()
        if not df_vendas.empty:
            # Filtro por vendedor (Admin vê tudo)
            if st.session_state['funcao'] != 'admin':
                df_vendas = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario_nome_sistema']]
            
            total = df_vendas['Valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_vendas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda encontrada.")
