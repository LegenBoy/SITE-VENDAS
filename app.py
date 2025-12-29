import streamlit as st
import pandas as pd
from datetime import date
import time
import os

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(
    page_title="Sistema MetaVendas",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PARA ESTILIZAR (DEIXAR BONITO) ---
st.markdown("""
<style>
    /* Estilo do container de Login */
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    .stButton > button {
        border-radius: 20px;
        font-weight: bold;
        border: none;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    /* Centralizar títulos */
    h1 {
        text-align: center; 
        color: #2E86C1;
    }
</style>
""", unsafe_allow_html=True)

# --- BACKEND (Gerenciamento de Dados e Sessão) ---
ARQUIVO_DADOS = 'vendas.csv'

def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        return pd.DataFrame(columns=["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor"])
    return pd.read_csv(ARQUIVO_DADOS)

def salvar_dados(nova_venda):
    df = carregar_dados()
    nova_linha = pd.DataFrame([nova_venda])
    df_final = pd.concat([df, nova_linha], ignore_index=True)
    df_final.to_csv(ARQUIVO_DADOS, index=False)

# Usuários (Em produção, isso viria de um banco seguro)
USUARIOS = {
    "admin": "admin123",  
    "joao": "1234",       
    "maria": "1234"      
}

def autenticar(usuario, senha):
    if usuario in USUARIOS and USUARIOS[usuario] == senha:
        return True
    return False

# --- FRONTEND: TELA DE LOGIN ---
def tela_login():
    st.markdown("<br><br>", unsafe_allow_html=True) # Espaçamento
    col1, col2, col3 = st.columns([1, 2, 1]) # Coluna do meio maior para centralizar
    
    with col2:
        st.markdown("# 🚀 MetaVendas")
        st.markdown("### Acesso Restrito")
        
        with st.container(border=True):
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário...")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha...")
            
            if st.button("ENTRAR", use_container_width=True):
                if autenticar(usuario, senha):
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = usuario
                    st.session_state['funcao'] = "admin" if usuario == "admin" else "vendedor"
                    st.toast("Login realizado com sucesso!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# --- FRONTEND: SISTEMA PRINCIPAL ---
def sistema_principal():
    # Sidebar (Menu Lateral)
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title(f"Olá, {st.session_state['usuario'].capitalize()}")
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        st.divider()
        if st.button("Sair do Sistema", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Controle")

    # Carrega dados
    df = carregar_dados()
    
    # Filtra dados baseados no perfil
    if st.session_state['funcao'] == 'vendedor':
        df_exibicao = df[df['Vendedor'] == st.session_state['usuario']]
    else:
        df_exibicao = df

    # --- MÉTRICAS (CARTÕES NO TOPO) ---
    total_vendido = df_exibicao['Valor'].sum() if not df_exibicao.empty else 0
    total_pedidos = len(df_exibicao)
    ticket_medio = total_vendido / total_pedidos if total_pedidos > 0 else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("💰 Total Vendido", f"R$ {total_vendido:,.2f}")
    col_m2.metric("📦 Pedidos Realizados", total_pedidos)
    col_m3.metric("📈 Ticket Médio", f"R$ {ticket_medio:,.2f}")

    st.divider()

    # --- ABAS DE NAVEGAÇÃO ---
    tab1, tab2 = st.tabs(["📝 Lançar Venda", "📋 Relatório Detalhado"])

    with tab1:
        st.subheader("Novo Pedido")
        with st.form("form_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            data = c1.date_input("Data", date.today())
            pedido = c2.text_input("Nº Pedido")
            
            c3, c4 = st.columns(2)
            valor = c3.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            retira = c4.checkbox("Retira Posterior?")
            
            botao_salvar = st.form_submit_button("Confirmar Venda", type="primary")

            if botao_salvar:
                if pedido and valor > 0:
                    nova_venda = {
                        "Data": data,
                        "Pedido": pedido,
                        "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não",
                        "Valor": valor
                    }
                    salvar_dados(nova_venda)
                    st.success("Venda registrada com sucesso!")
                    time.sleep(1)
                    st.rerun() # Atualiza a tela para mudar os números
                else:
                    st.warning("Preencha o número do pedido e o valor corretamente.")

    with tab2:
        st.subheader("Base de Dados")
        if not df_exibicao.empty:
            st.dataframe(
                df_exibicao, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Data": st.column_config.DateColumn(format="DD/MM/YYYY")
                }
            )
        else:
            st.info("Nenhum dado encontrado.")

# --- CONTROLE DE FLUXO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if st.session_state['logado']:
    sistema_principal()
else:
    tela_login()