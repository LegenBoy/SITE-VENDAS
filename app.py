import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MetaVendas System", page_icon="🚀", layout="wide")

# --- CSS PERSONALIZADO (ATUALIZADO PARA FOTO REDONDA) ---
st.markdown("""
<style>
    /* Estilo dos inputs e botões */
    .stTextInput > div > div > input { border-radius: 10px; }
    .stButton > button { border-radius: 20px; font-weight: bold; }
    
    /* Ajuste do topo da barra lateral */
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    
    /* --- O SEGREDO DA FOTO REDONDA --- */
    /* Isso mira especificamente na imagem dentro da barra lateral */
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important; /* Força o círculo */
        object-fit: cover !important;   /* Corta a imagem para não esticar */
        aspect-ratio: 1 / 1 !important; /* Garante que altura = largura (círculo perfeito) */
        border: 3px solid #2E86C1;      /* Uma borda azul bonita (opcional) */
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB")

# --- FUNÇÃO DE UPLOAD PARA IMGBB ---
def upload_imagem(arquivo):
    try:
        api_key = st.secrets["imgbb"]["key"]
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key}
        files = {"image": arquivo.getvalue()}
        response = requests.post(url, data=payload, files=files)
        dados = response.json()
        if dados["success"]: return dados["data"]["url"]
        else: return None
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return None

# --- FUNÇÕES DE VENDAS ---
def carregar_vendas():
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        colunas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
        if df.empty: return pd.DataFrame(columns=colunas)
        return df
    except: return pd.DataFrame()

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [str(nova_venda["Data"]), str(nova_venda["Pedido"]), nova_venda["Vendedor"], 
                 nova_venda["Retira_Posterior"], float(nova_venda["Valor"]), str(nova_venda["Pedido_Origem"])]
        ws.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- FUNÇÕES DE USUÁRIOS ---
def carregar_usuarios():
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        return pd.DataFrame(ws.get_all_records())
    except: return pd.DataFrame(columns=["Usuario", "Senha", "Nome", "Funcao", "Foto_URL"])

def criar_usuario(novo_user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        users = ws.col_values(1)
        if novo_user["Usuario"] in users: return False, "Usuário já existe!"
        linha = [novo_user["Usuario"], novo_user["Senha"], novo_user["Nome"], novo_user["Funcao"], novo_user["Foto_URL"]]
        ws.append_row(linha)
        return True, "Criado com sucesso!"
    except Exception as e: return False, str(e)

def deletar_usuario(user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        cell = ws.find(user)
        ws.delete_rows(cell.row)
        return True
    except: return False

# --- LOGIN ---
def autenticar(usuario, senha):
    df = carregar_usuarios()
    if df.empty: return None
    user = df[df["Usuario"] == usuario]
    if not user.empty and str(user.iloc[0]["Senha"]) == str(senha):
        return user.iloc[0]
    return None

# --- TELA LOGIN ---
def tela_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔐 Login MetaVendas")
        with st.container(border=True):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.button("ENTRAR", use_container_width=True):
                dados = autenticar(u, s)
                if dados is not None:
                    st.session_state.update({'logado': True, 'usuario': dados["Usuario"], 
                                           'nome': dados["Nome"], 'funcao': dados["Funcao"], 
                                           'foto': dados["Foto_URL"]})
                    st.rerun()
                else: st.error("Dados inválidos.")

# --- SISTEMA PRINCIPAL ---
def sistema_principal():
    with st.sidebar:
        # Use uma foto genérica se o usuário não tiver uma
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        # O CSS lá em cima vai transformar isso em um círculo
        st.image(foto, width=120) 
        
        st.title(st.session_state['nome'])
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Controle")
    df_vendas = carregar_vendas()
    
    if st.session_state['funcao'] == 'admin': df_view = df_vendas
    else: df_view = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    abas = ["📝 Lançar Venda", "📋 Relatório"]
    if st.session_state['funcao'] == 'admin': abas.append("⚙️ Equipe")
    tabs = st.tabs(abas)

    # ABA 1: VENDA
    with tabs[0]:
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", date.today())
        pedido = c2.text_input("Nº Pedido")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor R$", min_value=0.0, format="%.2f")
        retira = c4.toggle("É Retira Posterior?")
        
        pedido_origem = ""
        if retira:
            st.warning("⚠️ Retira Posterior")
            pedido_origem = st.text_input("DIGITE O PEDIDO DE RETIRA (VÍNCULO):")

        if st.button("Salvar Venda", type="primary"):
            if pedido and valor > 0 and (not retira or pedido_origem):
                nova = {"Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não", "Valor": valor, 
                        "Pedido_Origem": pedido_origem if retira else "-"}
                if salvar_venda(nova):
                    st.success("Sucesso!"); time.sleep(1); st.rerun()
            else: st.error("Preencha todos os campos obrigatórios.")

    # ABA 2: RELATÓRIO
    with tabs[1]:
        if not df_view.empty:
            df_view['Valor'] = pd.to_numeric(df_view['Valor'], errors='coerce').fillna(0)
            st.metric("Total", f"R$ {df_view['Valor'].sum():,.2f}")
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else: st.info("Sem dados.")

    # ABA 3: GESTÃO (COM UPLOAD)
    if st.session_state['funcao'] == 'admin':
        with tabs[2]:
            st.header("Cadastrar Equipe")
            with st.form("novo_user", clear_on_submit=True):
                u_user = st.text_input("Usuário (Login)")
                u_pass = st.text_input("Senha")
                u_nome = st.text_input("Nome Completo")
                u_role = st.selectbox("Função", ["vendedor", "admin"])
                arquivo_foto = st.file_uploader("Foto de Perfil (Opcional)", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("Cadastrar"):
                    url_foto = ""
                    if arquivo_foto:
                        with st.spinner("Enviando foto..."):
                            url_foto = upload_imagem(arquivo_foto)
                            if not url_foto: st.error("Erro no upload da imagem.")
                    
                    novo = {"Usuario": u_user, "Senha": u_pass, "Nome": u_nome, "Funcao": u_role, "Foto_URL": url_foto}
                    ok, msg = criar_usuario(novo)
                    if ok: st.success(msg); time.sleep(1); st.rerun()
                    else: st.error(msg)
            
            st.divider()
            df_users = carregar_usuarios()
            if not df_users.empty:
                st.dataframe(df_users[["Usuario", "Nome", "Funcao", "Foto_URL"]], use_container_width=True)
                c_del1, c_del2 = st.columns([3,1])
                user_del = c_del1.selectbox("Excluir Usuário", df_users["Usuario"].unique())
                if c_del2.button("Deletar"):
                    if user_del != "admin" and deletar_usuario(user_del):
                        st.success("Removido!"); time.sleep(1); st.rerun()
                    else: st.error("Erro ou admin protegido.")

if 'logado' not in st.session_state: st.session_state['logado'] = False
if st.session_state['logado']: sistema_principal()
else: tela_login()
