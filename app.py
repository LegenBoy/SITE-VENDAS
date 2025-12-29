import streamlit as st
import pandas as pd
from datetime import date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="MetaVendas System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS PERSONALIZADO (Visual Bonito) ---
st.markdown("""
<style>
    /* Estilo dos inputs e botões */
    .stTextInput > div > div > input { border-radius: 10px; }
    .stButton > button { border-radius: 20px; font-weight: bold; }
    
    /* Ajuste do topo da barra lateral */
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    
    /* FOTO REDONDA NA BARRA LATERAL */
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
        border: 3px solid #2E86C1;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. CONEXÃO E FUNÇÕES DE BACKEND ---

def conectar_gsheets():
    """Conecta ao Google Sheets usando Secrets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB")

def upload_imagem(arquivo):
    """Sobe imagem para o ImgBB e retorna o link"""
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
        st.error(f"Erro no upload da imagem: {e}")
        return None

# --- 4. FUNÇÕES DE BANCO DE DADOS (VENDAS E USUÁRIOS) ---

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
        linha = [
            str(nova_venda["Data"]), 
            str(nova_venda["Pedido"]), 
            nova_venda["Vendedor"], 
            nova_venda["Retira_Posterior"], 
            float(nova_venda["Valor"]), 
            str(nova_venda["Pedido_Origem"])
        ]
        ws.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def carregar_usuarios():
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        return pd.DataFrame(ws.get_all_records())
    except: 
        # Retorna estrutura vazia se der erro
        return pd.DataFrame(columns=["Usuario", "Senha", "Nome", "Funcao", "Foto_URL"])

def criar_usuario(novo_user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        users = ws.col_values(1) # Coluna A (Usuarios)
        if novo_user["Usuario"] in users: 
            return False, "Usuário já existe!"
        
        linha = [
            novo_user["Usuario"], 
            novo_user["Senha"], 
            novo_user["Nome"], 
            novo_user["Funcao"], 
            novo_user["Foto_URL"]
        ]
        ws.append_row(linha)
        return True, "Usuário criado com sucesso!"
    except Exception as e: return False, str(e)

def deletar_usuario(user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        cell = ws.find(user)
        ws.delete_rows(cell.row)
        return True
    except: return False

# --- 5. SISTEMA DE LOGIN ---

def autenticar(usuario, senha):
    df = carregar_usuarios()
    if df.empty: return None
    
    # Busca usuário
    user_row = df[df["Usuario"] == usuario]
    
    # Verifica senha
    if not user_row.empty and str(user_row.iloc[0]["Senha"]) == str(senha):
        return user_row.iloc[0]
    return None

def tela_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🔐 MetaVendas</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.button("ENTRAR", use_container_width=True):
                dados = autenticar(u, s)
                if dados is not None:
                    # Salva tudo na sessão
                    st.session_state.update({
                        'logado': True, 
                        'usuario': dados["Usuario"], 
                        'nome': dados["Nome"], 
                        'funcao': dados["Funcao"], 
                        'foto': dados["Foto_URL"]
                    })
                    st.rerun()
                else: 
                    st.error("Usuário ou senha incorretos.")

# --- 6. SISTEMA PRINCIPAL (DASHBOARD) ---

def sistema_principal():
    # --- BARRA LATERAL ---
    with st.sidebar:
        # Foto (redonda pelo CSS)
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        st.image(foto, width=120)
        
        st.title(st.session_state['nome'])
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        
        st.divider()
        
        # BOTÃO DE ATUALIZAR (NOVO)
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.rerun()
            
        st.divider()
        
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    # --- ÁREA PRINCIPAL ---
    st.title("📊 Painel de Controle")
    
    # Carrega dados com Spinner
    with st.spinner("Sincronizando com a nuvem..."):
        df_vendas = carregar_vendas()
    
    # Filtro de permissão
    if st.session_state['funcao'] == 'admin': 
        df_view = df_vendas
    else: 
        df_view = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    # Abas
    abas = ["📝 Lançar Venda", "📋 Relatório de Vendas"]
    if st.session_state['funcao'] == 'admin': 
        abas.append("⚙️ Gestão de Equipe")
    
    tabs = st.tabs(abas)

    # --- ABA 1: NOVA VENDA ---
    with tabs[0]:
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", date.today())
        pedido = c2.text_input("Nº Pedido")
        
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor R$", min_value=0.0, format="%.2f")
        
        # Toggle de Retira Posterior
        retira = c4.toggle("É Retira Posterior?")
        
        pedido_origem = ""
        if retira:
            st.warning("⚠️ Você marcou 'Retira Posterior'. Informe o vínculo abaixo:")
            pedido_origem = st.text_input("DIGITE O NÚMERO DO PEDIDO DE ORIGEM:")

        if st.button("💾 Salvar Venda", type="primary"):
            # Validações
            erro = False
            if not pedido: st.error("Faltou o número do pedido."); erro=True
            if valor <= 0: st.error("O valor deve ser maior que zero."); erro=True
            if retira and not pedido_origem: st.error("Informe o pedido de origem!"); erro=True
            
            if not erro:
                nova = {
                    "Data": data, 
                    "Pedido": pedido, 
                    "Vendedor": st.session_state['usuario'],
                    "Retira_Posterior": "Sim" if retira else "Não", 
                    "Valor": valor, 
                    "Pedido_Origem": pedido_origem if retira else "-"
                }
                if salvar_venda(nova):
                    st.success("Venda registrada com sucesso!")
                    time.sleep(1)
                    st.rerun()

    # --- ABA 2: RELATÓRIO ---
    with tabs[1]:
        # Botão de atualizar extra dentro da aba
        c_refresh, _ = st.columns([1, 6])
        if c_refresh.button("🔄 Recarregar Tabela"):
            st.rerun()

        if not df_view.empty:
            # Tratamento de número
            df_view['Valor'] = pd.to_numeric(df_view['Valor'], errors='coerce').fillna(0)
            
            # Métricas no topo
            total = df_view['Valor'].sum()
            qtd = len(df_view)
            
            m1, m2 = st.columns(2)
            m1.metric("Total Vendido", f"R$ {total:,.2f}")
            m2.metric("Quantidade de Vendas", qtd)
            
            st.divider()
            
            # Tabela
            st.dataframe(
                df_view, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f")
                }
            )
        else: 
            st.info("Nenhuma venda encontrada para este perfil.")

    # --- ABA 3: ADMIN (EQUIPE) ---
    if st.session_state['funcao'] == 'admin':
        with tabs[2]:
            st.subheader("Cadastrar Novo Vendedor")
            with st.form("novo_user", clear_on_submit=True):
                u_user = st.text_input("Usuário (Login)")
                u_pass = st.text_input("Senha")
                u_nome = st.text_input("Nome Completo")
                u_role = st.selectbox("Função", ["vendedor", "admin"])
                
                # Upload de Arquivo
                arquivo_foto = st.file_uploader("Foto de Perfil (Opcional)", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("Cadastrar Usuário"):
                    url_foto = ""
                    if arquivo_foto:
                        with st.spinner("Enviando foto para o servidor..."):
                            url_foto = upload_imagem(arquivo_foto)
                            if not url_foto: st.warning("Erro no upload da foto. Usuário será criado sem ela.")
                    
                    novo = {
                        "Usuario": u_user, 
                        "Senha": u_pass, 
                        "Nome": u_nome, 
                        "Funcao": u_role, 
                        "Foto_URL": url_foto
                    }
                    ok, msg = criar_usuario(novo)
                    if ok: 
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else: 
                        st.error(msg)
            
            st.divider()
            
            st.subheader("Usuários Ativos")
            df_users = carregar_usuarios()
            if not df_users.empty:
                st.dataframe(df_users[["Usuario", "Nome", "Funcao", "Foto_URL"]], use_container_width=True)
                
                st.write("---")
                c_del1, c_del2 = st.columns([3,1])
                user_del = c_del1.selectbox("Selecione usuário para excluir:", df_users["Usuario"].unique())
                
                if c_del2.button("🗑️ Deletar Usuário"):
                    if user_del == "admin":
                        st.error("O admin principal não pode ser deletado.")
                    elif user_del == st.session_state['usuario']:
                        st.error("Você não pode deletar a si mesmo enquanto logado.")
                    else:
                        if deletar_usuario(user_del):
                            st.success(f"Usuário {user_del} removido.")
                            time.sleep(1)
                            st.rerun()
                        else: st.error("Erro ao deletar.")

# --- 7. CONTROLE DE FLUXO ---
if 'logado' not in st.session_state: 
    st.session_state['logado'] = False

if st.session_state['logado']:
    sistema_principal()
else:
    tela_login()
