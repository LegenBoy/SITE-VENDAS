import streamlit as st
import pandas as pd
from datetime import datetime, date
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

# --- 2. CSS PERSONALIZADO ---
st.markdown("""
<style>
    .stTextInput > div > div > input { border-radius: 10px; }
    .stButton > button { border-radius: 20px; font-weight: bold; }
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
        border: 3px solid #2E86C1;
    }
    /* Destaque para área de edição */
    .area-edicao {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #d6d6d6;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. CONEXÃO E FUNÇÕES DE BACKEND ---

def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("SistemaMetas_DB")

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

# --- 4. FUNÇÕES DE BANCO DE DADOS ---

def carregar_vendas():
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        colunas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
        if df.empty: return pd.DataFrame(columns=colunas)
        # Garante que Pedido seja string para busca funcionar
        df['Pedido'] = df['Pedido'].astype(str)
        return df
    except: return pd.DataFrame()

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [
            str(nova_venda["Data"]), str(nova_venda["Pedido"]), nova_venda["Vendedor"], 
            nova_venda["Retira_Posterior"], float(nova_venda["Valor"]), str(nova_venda["Pedido_Origem"])
        ]
        ws.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def atualizar_venda(id_original, dados_novos):
    """
    Busca a linha pelo ID Original e atualiza todas as colunas.
    """
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        
        # Encontra a célula que contém o ID original
        cell = ws.find(str(id_original))
        linha_num = cell.row
        
        # Atualiza a linha inteira (Coluna 1 a 6)
        # Ordem: Data, Pedido, Vendedor, Retira, Valor, Origem
        nova_linha = [
            str(dados_novos["Data"]),
            str(dados_novos["Pedido"]), # Caso o usuário tenha mudado o número do pedido
            dados_novos["Vendedor"],
            dados_novos["Retira_Posterior"],
            float(dados_novos["Valor"]),
            str(dados_novos["Pedido_Origem"])
        ]
        
        # range de atualização: A{linha}:F{linha}
        ws.update(f"A{linha_num}:F{linha_num}", [nova_linha])
        return True
    except gspread.exceptions.CellNotFound:
        st.error("Erro: O pedido original não foi encontrado para atualização. Talvez tenha sido deletado.")
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False

def deletar_venda_sheet(numero_pedido):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        cell = ws.find(str(numero_pedido))
        ws.delete_rows(cell.row)
        return True
    except gspread.exceptions.CellNotFound:
        st.error("Pedido não encontrado.")
        return False
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

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
        ws.append_row([novo_user["Usuario"], novo_user["Senha"], novo_user["Nome"], novo_user["Funcao"], novo_user["Foto_URL"]])
        return True, "Sucesso!"
    except Exception as e: return False, str(e)

def deletar_usuario(user):
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        cell = ws.find(user)
        ws.delete_rows(cell.row)
        return True
    except: return False

# --- 5. LOGIN ---
def autenticar(usuario, senha):
    df = carregar_usuarios()
    if df.empty: return None
    user_row = df[df["Usuario"] == usuario]
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
                    st.session_state.update({
                        'logado': True, 'usuario': dados["Usuario"], 
                        'nome': dados["Nome"], 'funcao': dados["Funcao"], 
                        'foto': dados["Foto_URL"]
                    })
                    st.rerun()
                else: st.error("Incorreto.")

# --- 6. SISTEMA PRINCIPAL ---
def sistema_principal():
    with st.sidebar:
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        st.image(foto, width=120)
        st.title(st.session_state['nome'])
        st.caption(f"Perfil: {st.session_state['funcao'].upper()}")
        st.divider()
        if st.button("🔄 Atualizar Dados", use_container_width=True): st.rerun()
        st.divider()
        if st.button("Sair", type="primary"):
            st.session_state['logado'] = False
            st.rerun()

    st.title("📊 Painel de Controle")
    with st.spinner("Sincronizando..."):
        df_vendas = carregar_vendas()
        df_usuarios = carregar_usuarios() # Carrega usuários para o selectbox de edição

    # Filtragem de permissão
    if st.session_state['funcao'] == 'admin': df_view = df_vendas
    else: df_view = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    abas = ["📝 Lançar Venda", "📋 Relatório & Edição"]
    if st.session_state['funcao'] == 'admin': abas.append("⚙️ Equipe")
    tabs = st.tabs(abas)

    # ABA 1: NOVA VENDA
    with tabs[0]:
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", date.today())
        pedido = c2.text_input("Nº Pedido")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor R$", min_value=0.0, format="%.2f")
        retira = c4.toggle("É Retira Posterior?")
        pedido_origem = st.text_input("NÚMERO DO PEDIDO DE ORIGEM:") if retira else "-"

        if st.button("💾 Salvar Nova Venda", type="primary"):
            if pedido and valor > 0 and (not retira or (retira and pedido_origem != "")):
                nova = {"Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não", "Valor": valor, "Pedido_Origem": pedido_origem}
                if salvar_venda(nova): st.success("Salvo!"); time.sleep(1); st.rerun()
            else: st.error("Preencha corretamente.")

    # ABA 2: RELATÓRIO E EDIÇÃO
    with tabs[1]:
        c_refresh, _ = st.columns([1, 6])
        if c_refresh.button("🔄 Recarregar"): st.rerun()

        if not df_view.empty:
            df_view['Valor'] = pd.to_numeric(df_view['Valor'], errors='coerce').fillna(0)
            
            m1, m2 = st.columns(2)
            m1.metric("Total", f"R$ {df_view['Valor'].sum():,.2f}")
            m2.metric("Qtd", len(df_view))
            
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            # --- ZONA DE EDIÇÃO E EXCLUSÃO ---
            st.markdown("---")
            st.subheader("🔧 Gerenciar Vendas (Editar ou Excluir)")
            
            lista_pedidos = df_view['Pedido'].unique()
            
            if len(lista_pedidos) > 0:
                col_sel, col_btn_edit, col_btn_del = st.columns([2, 1, 1])
                pedido_selecionado = col_sel.selectbox("Selecione o Pedido:", lista_pedidos)
                
                # ESTADO DE EDIÇÃO (SESSION STATE)
                if 'editando_pedido' not in st.session_state:
                    st.session_state['editando_pedido'] = None

                # BOTÃO CARREGAR PARA EDIÇÃO
                if col_btn_edit.button("✏️ Editar Venda"):
                    st.session_state['editando_pedido'] = pedido_selecionado
                    st.rerun()
                
                # BOTÃO DELETAR
                if col_btn_del.button("🗑️ Apagar", type="primary"):
                    if deletar_venda_sheet(pedido_selecionado):
                        st.success("Apagado!"); time.sleep(1); st.rerun()

                # --- FORMULÁRIO DE EDIÇÃO (SÓ APARECE SE CLICAR EM EDITAR) ---
                if st.session_state['editando_pedido'] == pedido_selecionado:
                    st.info(f"Editando o Pedido: {pedido_selecionado}")
                    
                    # Busca dados atuais desse pedido no DataFrame
                    dados_atuais = df_view[df_view['Pedido'] == pedido_selecionado].iloc[0]
                    
                    with st.form("form_edicao"):
                        ce1, ce2 = st.columns(2)
                        
                        # Data
                        try: val_data = pd.to_datetime(dados_atuais['Data'], dayfirst=True).date()
                        except: val_data = date.today()
                        nova_data = ce1.date_input("Nova Data", value=val_data)
                        
                        # Pedido (Permite corrigir o número)
                        novo_pedido = ce2.text_input("Novo Nº Pedido", value=dados_atuais['Pedido'])
                        
                        ce3, ce4 = st.columns(2)
                        novo_valor = ce3.number_input("Novo Valor", value=float(dados_atuais['Valor']), min_value=0.0)
                        
                        # Retira Posterior
                        status_retira = True if dados_atuais['Retira_Posterior'] == "Sim" else False
                        novo_retira = ce4.toggle("Retira Posterior?", value=status_retira)
                        
                        # Pedido Origem
                        val_origem = dados_atuais['Pedido_Origem'] if dados_atuais['Pedido_Origem'] else ""
                        novo_origem = st.text_input("Pedido de Origem (Vínculo)", value=val_origem)
                        
                        # --- CAMPO VENDEDOR (ADMIN PODE TROCAR, VENDEDOR NÃO) ---
                        if st.session_state['funcao'] == 'admin':
                            # Admin vê uma lista de todos os usuários para transferir a venda
                            lista_vendedores = df_usuarios['Usuario'].unique()
                            # Tenta achar o índice atual
                            idx = 0
                            if dados_atuais['Vendedor'] in lista_vendedores:
                                idx = list(lista_vendedores).index(dados_atuais['Vendedor'])
                            novo_vendedor = st.selectbox("Vendedor Responsável", lista_vendedores, index=idx)
                        else:
                            # Vendedor vê o campo travado
                            novo_vendedor = st.text_input("Vendedor", value=dados_atuais['Vendedor'], disabled=True)

                        # BOTÃO SALVAR ALTERAÇÕES
                        if st.form_submit_button("💾 Salvar Alterações"):
                            dados_update = {
                                "Data": nova_data,
                                "Pedido": novo_pedido,
                                "Vendedor": novo_vendedor,
                                "Valor": novo_valor,
                                "Retira_Posterior": "Sim" if novo_retira else "Não",
                                "Pedido_Origem": novo_origem if novo_retira else "-"
                            }
                            
                            with st.spinner("Atualizando no Google Sheets..."):
                                if atualizar_venda(pedido_selecionado, dados_update): # Passa ID antigo e dados novos
                                    st.success("Venda atualizada com sucesso!")
                                    st.session_state['editando_pedido'] = None # Fecha o editor
                                    time.sleep(1)
                                    st.rerun()

            else: st.warning("Nenhuma venda disponível.")
        else: st.info("Sem dados.")

    # ABA 3: ADMIN
    if st.session_state['funcao'] == 'admin':
        with tabs[2]:
            st.header("Equipe")
            with st.form("novo_user"):
                u_user = st.text_input("Usuário")
                u_pass = st.text_input("Senha")
                u_nome = st.text_input("Nome")
                u_role = st.selectbox("Função", ["vendedor", "admin"])
                foto = st.file_uploader("Foto", type=["jpg", "png"])
                if st.form_submit_button("Cadastrar"):
                    url = upload_imagem(foto) if foto else ""
                    ok, msg = criar_usuario({"Usuario": u_user, "Senha": u_pass, "Nome": u_nome, "Funcao": u_role, "Foto_URL": url})
                    if ok: st.success(msg); time.sleep(1); st.rerun()
                    else: st.error(msg)
            
            st.divider()
            df_u = carregar_usuarios()
            if not df_u.empty:
                st.dataframe(df_u, use_container_width=True)
                d_user = st.selectbox("Deletar:", df_u["Usuario"].unique())
                if st.button("Deletar Usuário"):
                    if d_user!="admin" and deletar_usuario(d_user): st.rerun()

# --- 7. CONTROLE ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if st.session_state['logado']: sistema_principal()
else: tela_login()
