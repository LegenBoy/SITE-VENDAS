import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# --- 1. CONFIGURAÇÃO DA PÁGINA (MOBILE FRIENDLY) ---
st.set_page_config(
    page_title="MetaVendas App",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed" # Menu fechado para ganhar espaço no celular
)

# --- 2. CSS PARA VISUAL DE APP ---
st.markdown("""
<style>
    /* Borda arredondada suave e sombras estilo App */
    .stButton > button { 
        border-radius: 20px; 
        font-weight: bold; 
        height: 3em; /* Botão mais alto para dedo */
    }
    
    /* Foto Redonda */
    div[data-testid="stSidebarUserContent"] img {
        border-radius: 50% !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
        border: 3px solid #2E86C1;
    }

    /* Estilo do Card de Venda */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f9f9f9; /* Fundo claro para o card (modo light) */
        border-radius: 15px;
        margin-bottom: 10px;
    }
    /* Ajuste para modo escuro automático */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #262730;
        }
    }
    
    /* Título do Pedido no Card */
    .card-title {
        font-size: 18px;
        font-weight: bold;
        color: #2E86C1;
    }
    .card-valor {
        font-size: 20px;
        font-weight: bold;
        color: #28a745;
        text-align: right;
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
    except Exception: return None

# --- 4. FUNÇÕES DE BANCO DE DADOS ---
def carregar_vendas():
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        colunas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
        if df.empty: return pd.DataFrame(columns=colunas)
        df['Pedido'] = df['Pedido'].astype(str)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
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
        st.error(f"Erro: {e}")
        return False

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

def deletar_venda_sheet(numero_pedido):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        cell = ws.find(str(numero_pedido))
        ws.delete_rows(cell.row)
        return True
    except: return False

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
    except: return False, "Erro"

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
        st.markdown("<h1 style='text-align: center;'>📱 MetaVendas</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.button("ENTRAR", use_container_width=True):
                dados = autenticar(u, s)
                if dados is not None:
                    st.session_state.update({'logado': True, 'usuario': dados["Usuario"], 'nome': dados["Nome"], 'funcao': dados["Funcao"], 'foto': dados["Foto_URL"]})
                    st.rerun()
                else: st.error("Incorreto.")

# --- 6. MODAL EDIÇÃO ---
@st.dialog("✏️ Editar Venda")
def modal_editar_venda(pedido_selecionado, dados_atuais, lista_usuarios):
    with st.form("form_edicao_modal"):
        c1, c2 = st.columns(2)
        try: val_data = pd.to_datetime(dados_atuais['Data'], dayfirst=True).date() if isinstance(dados_atuais['Data'], str) else dados_atuais['Data']
        except: val_data = date.today()
        
        nova_data = c1.date_input("Data", value=val_data)
        novo_pedido = c2.text_input("Nº Pedido", value=dados_atuais['Pedido'])
        novo_valor = st.number_input("Valor R$", value=float(dados_atuais['Valor']), min_value=0.0)
        
        is_retira = True if dados_atuais['Retira_Posterior'] == "Sim" else False
        novo_retira = st.toggle("Retira Posterior?", value=is_retira)
        val_origem = dados_atuais['Pedido_Origem'] if dados_atuais['Pedido_Origem'] else ""
        novo_origem = st.text_input("Vínculo", value=val_origem)
        
        if st.session_state['funcao'] == 'admin':
            users = lista_usuarios['Usuario'].unique()
            idx = 0
            if dados_atuais['Vendedor'] in users: idx = list(users).index(dados_atuais['Vendedor'])
            novo_vendedor = st.selectbox("Vendedor", users, index=idx)
        else:
            novo_vendedor = st.text_input("Vendedor", value=dados_atuais['Vendedor'], disabled=True)
        
        if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
            update = {"Data": nova_data, "Pedido": novo_pedido, "Vendedor": novo_vendedor, "Valor": novo_valor,
                      "Retira_Posterior": "Sim" if novo_retira else "Não", "Pedido_Origem": novo_origem if novo_retira else "-"}
            with st.spinner("..."):
                if atualizar_venda(pedido_selecionado, update): st.success("Ok!"); time.sleep(1); st.rerun()

    st.markdown("---")
    if st.button("🗑️ Excluir Venda", use_container_width=True):
        if deletar_venda_sheet(pedido_selecionado): st.success("Apagado!"); time.sleep(1); st.rerun()

# --- 7. SISTEMA PRINCIPAL ---
def sistema_principal():
    with st.sidebar:
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        st.image(foto, width=100)
        st.markdown(f"**{st.session_state['nome']}**")
        st.caption(f"{st.session_state['funcao'].upper()}")
        st.divider()
        if st.button("🔄 Atualizar", use_container_width=True): st.rerun()
        if st.button("Sair", type="primary", use_container_width=True):
            st.session_state['logado'] = False; st.rerun()

    # Título menor para caber no celular
    st.markdown("### 🚀 Painel MetaVendas")
    
    with st.spinner("..."):
        df_vendas = carregar_vendas()
        df_usuarios = carregar_usuarios()

    if st.session_state['funcao'] == 'admin': df_completo = df_vendas
    else: df_completo = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    # Abas com ícones para economizar espaço
    abas = ["📝 Lançar", "📋 Vendas"]
    if st.session_state['funcao'] == 'admin': abas.append("⚙️ Equipe")
    tabs = st.tabs(abas)

    # ABA 1: LANÇAR (Mobile Friendly)
    with tabs[0]:
        data = st.date_input("Data", date.today())
        pedido = st.text_input("Nº Pedido")
        valor = st.number_input("Valor R$", min_value=0.0, format="%.2f")
        retira = st.toggle("É Retira Posterior?")
        origem = st.text_input("Vínculo (Pedido Origem)") if retira else "-"

        if st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True):
            if pedido and valor > 0:
                nova = {"Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não", "Valor": valor, "Pedido_Origem": origem}
                if salvar_venda(nova): st.success("Salvo!"); time.sleep(1); st.rerun()
            else: st.error("Preencha Valor e Pedido")

    # ABA 2: LISTA DE CARDS (Estilo iFood/Uber)
    with tabs[1]:
        # Filtros Compactos
        with st.expander("🔍 Filtros de Busca"):
            f_txt = st.text_input("Buscar Pedido")
            lista_vendedores = df_completo['Vendedor'].unique().tolist()
            if st.session_state['funcao'] == 'admin': f_vend = st.multiselect("Vendedor", options=lista_vendedores)
            else: f_vend = [st.session_state['usuario']]

        df_filtrado = df_completo.copy()
        if f_txt: df_filtrado = df_filtrado[df_filtrado['Pedido'].str.contains(f_txt, case=False)]
        if f_vend and st.session_state['funcao'] == 'admin': df_filtrado = df_filtrado[df_filtrado['Vendedor'].isin(f_vend)]
        
        # Ordenar: Mais recente primeiro
        if not df_filtrado.empty:
            df_filtrado = df_filtrado.sort_index(ascending=False)
            
            st.markdown(f"**{len(df_filtrado)} vendas encontradas**")
            
            # --- LOOP DE CARDS ---
            for index, row in df_filtrado.iterrows():
                # Cria um CONTAINER com borda (Parece um cartão)
                with st.container(border=True):
                    # Linha 1: Pedido e Valor
                    c_top1, c_top2 = st.columns([2, 1])
                    c_top1.markdown(f"<div class='card-title'>📦 {row['Pedido']}</div>", unsafe_allow_html=True)
                    c_top2.markdown(f"<div class='card-valor'>R$ {row['Valor']:.2f}</div>", unsafe_allow_html=True)
                    
                    # Linha 2: Detalhes
                    c_mid1, c_mid2, c_mid3 = st.columns([1, 1, 1])
                    c_mid1.caption(f"📅 {row['Data']}")
                    c_mid2.caption(f"👤 {row['Vendedor']}")
                    
                    # Ícone de Retira
                    if row['Retira_Posterior'] == "Sim":
                        c_mid3.markdown("⚠️ **Retira**")
                    else:
                        c_mid3.markdown("✅ **Normal**")
                    
                    # Se tiver vínculo
                    if row['Pedido_Origem'] and row['Pedido_Origem'] != "-":
                        st.caption(f"🔗 Vínculo: {row['Pedido_Origem']}")
                    
                    # Botão de Editar (Largura total para facilitar o clique no celular)
                    if st.button("✏️ Editar / Detalhes", key=f"btn_{row['Pedido']}", use_container_width=True):
                        modal_editar_venda(row['Pedido'], row, df_usuarios)
        else:
            st.info("Nenhuma venda encontrada.")

    # ABA 3: ADMIN
    if st.session_state['funcao'] == 'admin':
        with tabs[2]:
            st.write("Cadastro Rápido")
            with st.form("novo_user"):
                u = st.text_input("Usuário"); s = st.text_input("Senha")
                n = st.text_input("Nome"); r = st.selectbox("Função", ["vendedor", "admin"])
                f = st.file_uploader("Foto")
                if st.form_submit_button("Salvar", use_container_width=True):
                    url = upload_imagem(f) if f else ""
                    ok, m = criar_usuario({"Usuario": u, "Senha": s, "Nome": n, "Funcao": r, "Foto_URL": url})
                    if ok: st.success(m)

# --- 8. INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if st.session_state['logado']: sistema_principal()
else: tela_login()
