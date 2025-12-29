import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema MetaVendas",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .stTextInput > div > div > input { border-radius: 10px; }
    .stButton > button { border-radius: 20px; font-weight: bold; }
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    img.perfil-foto { border-radius: 50%; border: 3px solid #2E86C1; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE USUÁRIOS E FOTOS ---
USUARIOS = {
    "admin": "admin123",  
    "joao": "1234",       
    "maria": "1234"      
}

# Coloque aqui links públicos para as fotos (ex: GitHub, Linkedin, Imgur)
# Se não tiver foto, use um link genérico
FOTOS_PERFIL = {
    "admin": "https://cdn-icons-png.flaticon.com/512/9703/9703596.png",
    "joao": "https://cdn-icons-png.flaticon.com/512/4128/4128176.png", 
    "maria": "https://cdn-icons-png.flaticon.com/512/4128/4128244.png"
}

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_gsheets():
    """Conecta ao Google Sheets usando as credenciais do st.secrets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Pega as credenciais dos segredos do Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    # ABRE A PLANILHA PELO NOME (Tem que ser o nome exato que você criou)
    sheet = client.open("SistemaMetas_DB").sheet1 
    return sheet

def carregar_dados():
    try:
        sheet = conectar_gsheets()
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        # Garante que as colunas existam mesmo se a planilha estiver vazia
        colunas_esperadas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor"]
        if df.empty:
            return pd.DataFrame(columns=colunas_esperadas)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

def salvar_dados(nova_venda):
    try:
        sheet = conectar_gsheets()
        # Prepara a linha na ordem correta das colunas
        linha = [
            str(nova_venda["Data"]),
            str(nova_venda["Pedido"]),
            nova_venda["Vendedor"],
            nova_venda["Retira_Posterior"],
            float(nova_venda["Valor"])
        ]
        sheet.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- AUTENTICAÇÃO ---
def autenticar(usuario, senha):
    if usuario in USUARIOS and USUARIOS[usuario] == senha:
        return True
    return False

# --- TELA DE LOGIN ---
def tela_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 🚀 MetaVendas Cloud")
        with st.container(border=True):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            
            if st.button("ENTRAR", use_container_width=True):
                if autenticar(usuario, senha):
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = usuario
                    st.session_state['funcao'] = "admin" if usuario == "admin" else "vendedor"
                    st.rerun()
                else:
                    st.error("Dados incorretos.")

# --- SISTEMA PRINCIPAL ---
def sistema_principal():
    usuario_atual = st.session_state['usuario']
    
    # --- BARRA LATERAL (SIDEBAR) COM FOTO ---
    with st.sidebar:
        # Exibe a foto de perfil
        foto_url = FOTOS_PERFIL.get(usuario_atual, "https://cdn-icons-png.flaticon.com/512/149/149071.png")
        st.image(foto_url, width=120)
        
        st.title(f"Olá, {usuario_atual.capitalize()}!")
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        st.divider()
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Vendas")

    # Carrega dados do Google Sheets (pode demorar uns 2 segundos)
    with st.spinner("Sincronizando com Google Sheets..."):
        df = carregar_dados()
    
    # Filtro de permissão
    if st.session_state['funcao'] == 'vendedor':
        df_exibicao = df[df['Vendedor'] == usuario_atual]
    else:
        df_exibicao = df

    # --- MÉTRICAS ---
    # Tratamento de erro caso a coluna venha como texto do sheets
    if not df_exibicao.empty:
        # Converte para numérico forçado, pois Sheets as vezes manda texto "R$ 100"
        df_exibicao['Valor'] = pd.to_numeric(df_exibicao['Valor'], errors='coerce').fillna(0)
        
    total_vendido = df_exibicao['Valor'].sum() if not df_exibicao.empty else 0
    total_pedidos = len(df_exibicao)
    
    c1, c2 = st.columns(2)
    c1.metric("💰 Total Vendido", f"R$ {total_vendido:,.2f}")
    c2.metric("📦 Pedidos", total_pedidos)

    st.divider()

    # --- ABAS ---
    tab1, tab2 = st.tabs(["📝 Lançar Venda", "📋 Relatório"])

    with tab1:
        with st.form("form_venda", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            data = col_a.date_input("Data", date.today())
            pedido = col_b.text_input("Número do Pedido")
            
            col_c, col_d = st.columns(2)
            valor = col_c.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            retira = col_d.checkbox("Retira Posterior?")
            
            if st.form_submit_button("💾 Salvar no Google Sheets"):
                if pedido and valor > 0:
                    nova_venda = {
                        "Data": data,
                        "Pedido": pedido,
                        "Vendedor": usuario_atual,
                        "Retira_Posterior": "Sim" if retira else "Não",
                        "Valor": valor
                    }
                    if salvar_dados(nova_venda):
                        st.success("Salvo na nuvem com sucesso!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Preencha os dados corretamente.")

    with tab2:
        if not df_exibicao.empty:
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda encontrada.")

# --- LOOP PRINCIPAL ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if st.session_state['logado']:
    sistema_principal()
else:
    tela_login()
