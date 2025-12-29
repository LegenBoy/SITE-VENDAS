import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MetaVendas System", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .stTextInput > div > div > input { border-radius: 10px; }
    .stButton > button { border-radius: 20px; font-weight: bold; }
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS (GOOGLE SHEETS) ---
def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB")

# --- FUNÇÕES DE VENDAS ---
def carregar_vendas():
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1 # Primeira aba (Vendas)
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        colunas_esperadas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
        if df.empty: return pd.DataFrame(columns=colunas_esperadas)
        return df
    except Exception as e:
        return pd.DataFrame()

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [
            str(nova_venda["Data"]), str(nova_venda["Pedido"]),
            nova_venda["Vendedor"], nova_venda["Retira_Posterior"],
            float(nova_venda["Valor"]), str(nova_venda["Pedido_Origem"])
        ]
        ws.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- FUNÇÕES DE USUÁRIOS (NOVO!) ---
def carregar_usuarios():
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios") # Segunda aba
        dados = ws.get_all_records()
        return pd.DataFrame(dados)
    except:
        return pd.DataFrame(columns=["Usuario", "Senha", "Nome", "Funcao", "Foto_URL"])

def criar_usuario(novo_user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        # Verifica se já existe
        users_existentes = ws.col_values(1)
        if novo_user["Usuario"] in users_existentes:
            return False, "Usuário já existe!"
        
        linha = [novo_user["Usuario"], novo_user["Senha"], novo_user["Nome"], novo_user["Funcao"], novo_user["Foto_URL"]]
        ws.append_row(linha)
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, str(e)

def deletar_usuario(usuario_para_deletar):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        cell = ws.find(usuario_para_deletar)
        ws.delete_rows(cell.row)
        return True
    except Exception as e:
        return False

# --- LOGIN ---
def autenticar(usuario, senha):
    df_users = carregar_usuarios()
    if df_users.empty: return None
    
    # Filtra usuário
    user_encontrado = df_users[df_users["Usuario"] == usuario]
    
    if not user_encontrado.empty:
        senha_real = str(user_encontrado.iloc[0]["Senha"]) # Converte para string para garantir
        if str(senha) == senha_real:
            return user_encontrado.iloc[0] # Retorna os dados do usuário
    return None

# --- TELAS ---
def tela_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔐 Login MetaVendas")
        with st.container(border=True):
            usr = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            if st.button("ENTRAR", use_container_width=True):
                dados_user = autenticar(usr, pwd)
                if dados_user is not None:
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = dados_user["Usuario"]
                    st.session_state['nome'] = dados_user["Nome"]
                    st.session_state['funcao'] = dados_user["Funcao"]
                    st.session_state['foto'] = dados_user["Foto_URL"]
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

def sistema_principal():
    # SIDEBAR
    with st.sidebar:
        # Foto padrão se não tiver URL
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        st.image(foto, width=100)
        st.title(f"{st.session_state['nome']}")
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Controle")
    
    # Carregar Vendas
    df_vendas = carregar_vendas()
    
    # Se for vendedor, filtra. Se for admin, vê tudo.
    if st.session_state['funcao'] == 'admin':
        df_exibicao = df_vendas
    else:
        df_exibicao = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    # ABAS
    abas = ["📝 Lançar Venda", "📋 Relatório"]
    if st.session_state['funcao'] == 'admin':
        abas.append("⚙️ Gerenciar Usuários") # Aba extra só para admin
    
    tabs = st.tabs(abas)

    # --- ABA 1: LANÇAR VENDA ---
    with tabs[0]:
        st.info("Preencha os dados da venda:")
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", date.today())
        pedido = c2.text_input("Nº Pedido")
        
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor R$", min_value=0.0, format="%.2f")
        
        # --- LÓGICA RETIRA POSTERIOR ---
        retira = c4.toggle("É Retira Posterior?")
        pedido_origem = ""
        
        if retira:
            st.warning("⚠️ Retira Posterior Selecionado")
            pedido_origem = st.text_input("DIGITE O PEDIDO DE RETIRA (VÍNCULO):", placeholder="Ex: 12345")
        
        if st.button("Salvar Venda", type="primary"):
            if not pedido or valor <= 0:
                st.error("Preencha pedido e valor.")
            elif retira and not pedido_origem:
                st.error("Para retira posterior, informe o pedido de vínculo!")
            else:
                nova = {
                    "Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                    "Retira_Posterior": "Sim" if retira else "Não",
                    "Valor": valor, "Pedido_Origem": pedido_origem if retira else "-"
                }
                if salvar_venda(nova):
                    st.success("Venda salva!")
                    time.sleep(1)
                    st.rerun()

    # --- ABA 2: RELATÓRIO ---
    with tabs[1]:
        # Converter valor para número para somar corretamente
        if not df_exibicao.empty:
            df_exibicao['Valor'] = pd.to_numeric(df_exibicao['Valor'], errors='coerce').fillna(0)
            
            total = df_exibicao['Valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.info("Sem vendas.")

    # --- ABA 3: GESTÃO DE USUÁRIOS (SÓ ADMIN) ---
    if st.session_state['funcao'] == 'admin':
        with tabs[2]:
            st.header("Gestão de Equipe")
            
            # Formulário de Cadastro
            with st.expander("➕ Cadastrar Novo Usuário", expanded=False):
                with st.form("novo_user"):
                    u_user = st.text_input("Usuário (Login)")
                    u_pass = st.text_input("Senha")
                    u_nome = st.text_input("Nome Completo")
                    u_role = st.selectbox("Função", ["vendedor", "admin"])
                    u_foto = st.text_input("Link da Foto (Opcional)")
                    
                    if st.form_submit_button("Cadastrar"):
                        novo = {"Usuario": u_user, "Senha": u_pass, "Nome": u_nome, "Funcao": u_role, "Foto_URL": u_foto}
                        ok, msg = criar_usuario(novo)
                        if ok: st.success(msg); time.sleep(1); st.rerun()
                        else: st.error(msg)
            
            st.divider()
            
            # Lista de Usuários e Exclusão
            df_users = carregar_usuarios()
            if not df_users.empty:
                st.subheader("Usuários Ativos")
                st.dataframe(df_users[["Usuario", "Nome", "Funcao"]], use_container_width=True)
                
                # Excluir Usuário
                st.write("🗑️ **Excluir Usuário:**")
                col_del1, col_del2 = st.columns([3, 1])
                user_to_del = col_del1.selectbox("Selecione para excluir", df_users["Usuario"].unique())
                
                if col_del2.button("Deletar"):
                    if user_to_del == "admin": # Proteção básica
                        st.error("Não é possível deletar o admin principal.")
                    else:
                        if deletar_usuario(user_to_del):
                            st.success(f"{user_to_del} removido.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Erro ao deletar.")

# --- INÍCIO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if st.session_state['logado']:
    sistema_principal()
else:
    tela_login()
