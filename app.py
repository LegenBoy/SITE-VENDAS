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
    
    /* Foto Redonda */
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
        border: 3px solid #2E86C1;
    }

    /* Estilo para a Tabela Customizada */
    .tabela-header {
        font-weight: bold;
        border-bottom: 2px solid #444;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .tabela-row {
        border-bottom: 1px solid #333;
        padding-top: 10px;
        padding-bottom: 10px;
        align-items: center;
    }
    .tabela-row:hover {
        background-color: #262730; /* Efeito hover na linha */
        border-radius: 5px;
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
        # Garante tipos corretos
        df['Pedido'] = df['Pedido'].astype(str)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        # Garante formato de data
        try:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True).dt.date
        except:
            pass # Se der erro, deixa como string mesmo
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
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        cell = ws.find(str(id_original))
        linha_num = cell.row
        nova_linha = [
            str(dados_novos["Data"]),
            str(dados_novos["Pedido"]),
            dados_novos["Vendedor"],
            dados_novos["Retira_Posterior"],
            float(dados_novos["Valor"]),
            str(dados_novos["Pedido_Origem"])
        ]
        ws.update(f"A{linha_num}:F{linha_num}", [nova_linha])
        return True
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

# --- 6. MODAL DE EDIÇÃO (NOVO!) ---
@st.dialog("✏️ Editar Venda")
def modal_editar_venda(pedido_selecionado, dados_atuais, lista_usuarios):
    """
    Esta função cria uma janela pop-up (Modal) sobre o app.
    """
    with st.form("form_edicao_modal"):
        c1, c2 = st.columns(2)
        
        # Tenta converter data, se falhar usa hoje
        try: 
            if isinstance(dados_atuais['Data'], str):
                val_data = datetime.strptime(dados_atuais['Data'], '%Y-%m-%d').date()
            else:
                val_data = dados_atuais['Data']
        except: 
            val_data = date.today()

        nova_data = c1.date_input("Data", value=val_data)
        novo_pedido = c2.text_input("Nº Pedido", value=dados_atuais['Pedido'])
        
        c3, c4 = st.columns(2)
        novo_valor = c3.number_input("Valor", value=float(dados_atuais['Valor']), min_value=0.0)
        
        is_retira = True if dados_atuais['Retira_Posterior'] == "Sim" else False
        novo_retira = c4.toggle("Retira Posterior?", value=is_retira)
        
        val_origem = dados_atuais['Pedido_Origem'] if dados_atuais['Pedido_Origem'] else ""
        novo_origem = st.text_input("Pedido de Origem", value=val_origem)
        
        # Se for admin, pode trocar o dono da venda
        if st.session_state['funcao'] == 'admin':
            users = lista_usuarios['Usuario'].unique()
            idx = 0
            if dados_atuais['Vendedor'] in users:
                idx = list(users).index(dados_atuais['Vendedor'])
            novo_vendedor = st.selectbox("Vendedor", users, index=idx)
        else:
            novo_vendedor = st.text_input("Vendedor", value=dados_atuais['Vendedor'], disabled=True)
        
        # Botões de Ação
        col_save, col_del = st.columns([2, 1])
        
        salvou = col_save.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
        # Deletar precisa ser um botão fora ou com logica especial, 
        # mas dentro de form o submit é o principal. Vamos focar em salvar aqui.
        
        if salvou:
            dados_update = {
                "Data": nova_data, "Pedido": novo_pedido, "Vendedor": novo_vendedor,
                "Valor": novo_valor, "Retira_Posterior": "Sim" if novo_retira else "Não",
                "Pedido_Origem": novo_origem if novo_retira else "-"
            }
            with st.spinner("Atualizando..."):
                if atualizar_venda(pedido_selecionado, dados_update):
                    st.success("Atualizado!")
                    time.sleep(1)
                    st.rerun()

    # Botão de deletar fora do form para evitar conflito de submit
    st.markdown("---")
    if st.button("🗑️ Excluir esta venda permanentemente", type="primary"):
        with st.spinner("Excluindo..."):
            if deletar_venda_sheet(pedido_selecionado):
                st.success("Venda excluída!")
                time.sleep(1)
                st.rerun()


# --- 7. SISTEMA PRINCIPAL ---
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
        df_usuarios = carregar_usuarios()

    # Define qual DataFrame o usuário pode ver
    if st.session_state['funcao'] == 'admin': 
        df_completo = df_vendas
    else: 
        df_completo = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

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
        pedido_origem = st.text_input("PEDIDO DE VÍNCULO:") if retira else "-"

        if st.button("💾 Salvar Nova Venda", type="primary"):
            if pedido and valor > 0 and (not retira or (retira and pedido_origem != "")):
                nova = {"Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não", "Valor": valor, "Pedido_Origem": pedido_origem}
                if salvar_venda(nova): st.success("Salvo!"); time.sleep(1); st.rerun()
            else: st.error("Preencha corretamente.")

    # ABA 2: RELATÓRIO COM FILTROS E EDIÇÃO INLINE
    with tabs[1]:
        # --- 1. ÁREA DE FILTROS ---
        with st.container(border=True):
            st.markdown("🔍 **Filtros de Pesquisa**")
            col_f1, col_f2, col_f3 = st.columns(3)
            
            # Filtro Texto (Pedido)
            filtro_pedido = col_f1.text_input("Buscar Pedido", placeholder="Ex: 340...")
            
            # Filtro Vendedor (Se for admin vê todos, se não vê só o dele travado)
            lista_vendedores = df_completo['Vendedor'].unique().tolist()
            if st.session_state['funcao'] == 'admin':
                filtro_vendedor = col_f2.multiselect("Filtrar Vendedor", options=lista_vendedores)
            else:
                col_f2.text_input("Vendedor", value=st.session_state['usuario'], disabled=True)
                filtro_vendedor = [st.session_state['usuario']] # Força filtro
                
            # Filtro Data
            filtro_data = col_f3.date_input("Filtrar Data", value=[], help="Selecione início e fim ou deixe vazio para ver tudo")

        # --- 2. APLICAÇÃO DOS FILTROS ---
        df_filtrado = df_completo.copy()
        
        if filtro_pedido:
            df_filtrado = df_filtrado[df_filtrado['Pedido'].str.contains(filtro_pedido, case=False)]
        
        if filtro_vendedor and st.session_state['funcao'] == 'admin':
            df_filtrado = df_filtrado[df_filtrado['Vendedor'].isin(filtro_vendedor)]
            
        if len(filtro_data) == 2: # Intervalo de datas selecionado
            data_ini, data_fim = filtro_data
            # Converte coluna para date se não for
            df_filtrado['Data_Obj'] = pd.to_datetime(df_filtrado['Data']).dt.date
            df_filtrado = df_filtrado[(df_filtrado['Data_Obj'] >= data_ini) & (df_filtrado['Data_Obj'] <= data_fim)]

        # --- 3. EXIBIÇÃO DA TABELA CUSTOMIZADA (GRID) ---
        st.markdown(f"**Resultados Encontrados:** {len(df_filtrado)}")
        
        # Cabeçalho da Tabela
        # Definimos proporções das colunas: Data(1), Pedido(1.5), Vendedor(1.5), Valor(1), Retira(1), Origem(1), Botão(0.5)
        cols_spec = [1, 1.5, 1.5, 1, 1, 1.2, 0.5]
        
        c_h1, c_h2, c_h3, c_h4, c_h5, c_h6, c_h7 = st.columns(cols_spec)
        c_h1.markdown("**Data**")
        c_h2.markdown("**Pedido**")
        c_h3.markdown("**Vendedor**")
        c_h4.markdown("**Valor**")
        c_h5.markdown("**Retira?**")
        c_h6.markdown("**Origem**")
        c_h7.markdown("**Editar**")
        st.markdown("<div class='tabela-header'></div>", unsafe_allow_html=True)

        if not df_filtrado.empty:
            # Ordena por data decrescente (mais recentes primeiro)
            df_filtrado = df_filtrado.sort_index(ascending=False)
            
            # Loop para criar as linhas com botão
            for index, row in df_filtrado.iterrows():
                # Container para dar visual de linha
                with st.container():
                    c1, c2, c3, c4, c5, c6, c7 = st.columns(cols_spec)
                    
                    c1.write(row['Data'])
                    c2.write(row['Pedido'])
                    c3.write(row['Vendedor'])
                    c4.write(f"R$ {row['Valor']:.2f}")
                    
                    # Ícone visual para retira
                    retira_icon = "✅" if row['Retira_Posterior'] == "Sim" else "❌"
                    c5.write(retira_icon)
                    
                    c6.write(row['Pedido_Origem'])
                    
                    # O BOTÃO DE EDIÇÃO (CANETA)
                    # Usamos o ID do pedido como chave única
                    if c7.button("✏️", key=f"btn_{row['Pedido']}"):
                        modal_editar_venda(row['Pedido'], row, df_usuarios)
                    
                    st.markdown("<div class='tabela-row'></div>", unsafe_allow_html=True)
        else:
            st.info("Nenhum pedido encontrado com esses filtros.")


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

# --- 8. CONTROLE ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if st.session_state['logado']: sistema_principal()
else: tela_login()
