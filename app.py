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
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DE USUÁRIOS E FOTOS ---
USUARIOS = {
    "admin": "admin123",  
    "joao": "1234",       
    "maria": "1234"      
}

FOTOS_PERFIL = {
    "admin": "https://cdn-icons-png.flaticon.com/512/9703/9703596.png",
    "joao": "https://cdn-icons-png.flaticon.com/512/4128/4128176.png", 
    "maria": "https://cdn-icons-png.flaticon.com/512/4128/4128244.png"
}

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB").sheet1 

def carregar_dados():
    try:
        sheet = conectar_gsheets()
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        # Atualizei as colunas esperadas com a nova coluna
        colunas_esperadas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
        if df.empty:
            return pd.DataFrame(columns=colunas_esperadas)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def salvar_dados(nova_venda):
    try:
        sheet = conectar_gsheets()
        # Ordem exata das colunas na planilha
        linha = [
            str(nova_venda["Data"]),
            str(nova_venda["Pedido"]),
            nova_venda["Vendedor"],
            nova_venda["Retira_Posterior"],
            float(nova_venda["Valor"]),
            str(nova_venda["Pedido_Origem"]) # Nova Coluna Salva
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
    
    with st.sidebar:
        foto_url = FOTOS_PERFIL.get(usuario_atual, "https://cdn-icons-png.flaticon.com/512/149/149071.png")
        st.image(foto_url, width=120)
        st.title(f"Olá, {usuario_atual.capitalize()}!")
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        st.divider()
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Vendas")

    with st.spinner("Sincronizando..."):
        df = carregar_dados()
    
    if st.session_state['funcao'] == 'vendedor':
        df_exibicao = df[df['Vendedor'] == usuario_atual]
    else:
        df_exibicao = df

    # Tratamento numérico
    if not df_exibicao.empty and 'Valor' in df_exibicao.columns:
        df_exibicao['Valor'] = pd.to_numeric(df_exibicao['Valor'], errors='coerce').fillna(0)
        
    total_vendido = df_exibicao['Valor'].sum() if not df_exibicao.empty else 0
    total_pedidos = len(df_exibicao)
    
    c1, c2 = st.columns(2)
    c1.metric("💰 Total Vendido", f"R$ {total_vendido:,.2f}")
    c2.metric("📦 Pedidos", total_pedidos)

    st.divider()

    tab1, tab2 = st.tabs(["📝 Lançar Venda", "📋 Relatório"])

    # --- LÓGICA DE INPUT CONDICIONAL (SEM st.form RÍGIDO) ---
    with tab1:
        st.info("Preencha os dados da venda abaixo:")
        
        col_a, col_b = st.columns(2)
        data = col_a.date_input("Data", date.today())
        pedido = col_b.text_input("Número do Pedido Atual")
        
        col_c, col_d = st.columns(2)
        valor = col_c.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        
        # O CHECKBOX QUE FAZ MÁGICA
        # Quando clicar aqui, o Streamlit recarrega e mostra o campo IF abaixo
        retira = col_d.toggle("É Retira Posterior?") 
        
        pedido_origem = ""
        
        if retira:
            st.warning("⚠️ Você marcou Retira Posterior.")
            # Esse campo só aparece se o toggle estiver ligado
            pedido_origem = st.text_input("Cole aqui o Nº do Pedido de Origem (Vinculado):")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botão de Salvar fora de form para permitir a dinâmica acima
        if st.button("💾 Salvar Venda", type="primary", use_container_width=True):
            # Validações
            erro = False
            if not pedido:
                st.toast("Faltou o número do pedido!", icon="❌")
                erro = True
            if valor <= 0:
                st.toast("O valor deve ser maior que zero!", icon="❌")
                erro = True
            if retira and not pedido_origem:
                st.toast("Para Retira Posterior, é OBRIGATÓRIO informar o pedido de origem!", icon="❌")
                erro = True
            
            if not erro:
                nova_venda = {
                    "Data": data,
                    "Pedido": pedido,
                    "Vendedor": usuario_atual,
                    "Retira_Posterior": "Sim" if retira else "Não",
                    "Valor": valor,
                    "Pedido_Origem": pedido_origem if retira else "-" # Salva traço se não for retira
                }
                
                with st.spinner("Salvando no Google Sheets..."):
                    if salvar_dados(nova_venda):
                        st.balloons()
                        st.success("Venda registrada com sucesso!")
                        time.sleep(1.5)
                        st.rerun()

    with tab2:
        if not df_exibicao.empty:
            # Reordenar colunas para ficar bonito
            colunas_ordem = ["Data", "Pedido", "Valor", "Retira_Posterior", "Pedido_Origem", "Vendedor"]
            # Filtra apenas colunas que existem para evitar erro
            cols_existentes = [c for c in colunas_ordem if c in df_exibicao.columns]
            
            st.dataframe(
                df_exibicao[cols_existentes], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Nenhuma venda encontrada.")

# --- LOOP PRINCIPAL ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if st.session_state['logado']:
    sistema_principal()
else:
    tela_login()
