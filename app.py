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

def converter_para_float(valor_texto):
    """Converte o texto digitado em número real para o banco de dados"""
    if not valor_texto: return 0.0
    v = str(valor_texto).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

# --- CALLBACK DE SALVAMENTO (AGORA COM LIMPEZA DE CAMPOS) ---
def processar_salvamento(data, pedido, valor_txt, retira, origem, usuario_atual):
    valor_final = converter_para_float(valor_txt)
    
    if pedido and valor_final > 0:
        nova = {
            "Data": data, 
            "Pedido": pedido, 
            "Vendedor": usuario_atual,
            "Retira_Posterior": "Sim" if retira else "Não", 
            "Valor": valor_final,
            "Pedido_Origem": origem
        }
        
        if salvar_venda(nova): 
            # LIMPEZA DOS CAMPOS: Reseta as chaves do session_state
            st.session_state["input_pedido"] = ""
            st.session_state["input_valor"] = ""
            st.session_state["input_origem"] = ""
            
            st.toast(f"✅ Venda Salva!", icon="🚀")
            time.sleep(1)
    else:
        st.error("Preencha o Número do Pedido e o Valor corretamente.")

# --- 4. FUNÇÕES DE BANCO DE DADOS ---
def carregar_vendas():
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        if df.empty: return pd.DataFrame(columns=["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"])
        
        df['Pedido'] = df['Pedido'].astype(str)
        # Limpeza para garantir que o dashboard mostre números certos
        df['Valor'] = df['Valor'].apply(lambda x: float(str(x).replace('.','').replace(',','.')) if isinstance(x, str) and ',' in x else float(x))
        return df
    except: return pd.DataFrame()

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [str(nova_venda["Data"]), str(nova_venda["Pedido"]), nova_venda["Vendedor"], 
                 nova_venda["Retira_Posterior"], nova_venda["Valor"], str(nova_venda["Pedido_Origem"])]
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
    try: val_data = pd.to_datetime(dados_atuais['Data'], dayfirst=True).date() if isinstance(dados_atuais['Data'], str) else dados_atuais['Data']
    except: val_data = date.today()
    
    nova_data = st.date_input("Data", value=val_data)
    novo_pedido = st.text_input("Nº Pedido", value=dados_atuais['Pedido'])
    
    # Na edição, mostramos o valor atual como texto simples para você alterar
    valor_atual_str = str(dados_atuais['Valor']).replace('.',',')
    novo_valor_txt = st.text_input("Valor (Ex: 1500,50)", value=valor_atual_str)
    
    is_retira = True if dados_atuais['Retira_Posterior'] == "Sim" else False
    novo_retira = st.toggle("Retira Posterior?", value=is_retira)
    val_origem = dados_atuais['Pedido_Origem'] if dados_atuais['Pedido_Origem'] else ""
    novo_origem = st.text_input("Vínculo", value=val_origem)
    
    if st.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
        v_final = converter_para_float(novo_valor_txt)
        update = {"Data": nova_data, "Pedido": novo_pedido, "Vendedor": dados_atuais['Vendedor'], "Valor": v_final,
                  "Retira_Posterior": "Sim" if novo_retira else "Não", "Pedido_Origem": novo_origem if novo_retira else "-"}
        if atualizar_venda(pedido_selecionado, update): 
            st.success("Atualizado!")
            time.sleep(1); st.rerun()

    if st.button("🗑️ Excluir Venda", use_container_width=True):
        if deletar_venda_sheet(pedido_selecionado): 
            st.success("Apagado!"); time.sleep(1); st.rerun()

# --- 7. SISTEMA PRINCIPAL ---
def sistema_principal():
    with st.sidebar:
        foto = st.session_state['foto'] if st.session_state['foto'] else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        st.image(foto, width=100)
        st.markdown(f"**{st.session_state['nome']}**")
        st.divider()
        if st.button("🔄 Atualizar", use_container_width=True): st.rerun()
        if st.button("Sair", type="primary", use_container_width=True):
            st.session_state['logado'] = False; st.rerun()

    st.markdown("### 🚀 Painel MetaVendas")
    df_vendas = carregar_vendas()
    
    if st.session_state['funcao'] == 'admin': df_completo = df_vendas
    else: df_completo = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    tabs = st.tabs(["📝 Lançar", "📋 Vendas"])

    # ABA 1: LANÇAR (SIMPLIFICADA)
    with tabs[0]:
        data = st.date_input("Data", date.today())
        
        # Uso de chaves (keys) para permitir a limpeza automática
        pedido = st.text_input("Nº Pedido", key="input_pedido")
        
        if pedido and not df_vendas.empty:
            if pedido in df_vendas['Pedido'].astype(str).tolist():
                st.warning(f"⚠️ Pedido {pedido} já existe!")
        
        valor_txt = st.text_input("Valor (Ex: 1874,97)", key="input_valor")
        
        retira = st.toggle("É Retira Posterior?")
        origem = st.text_input("Vínculo (Pedido Origem)", key="input_origem") if retira else "-"

        st.button(
            "💾 REGISTRAR VENDA", 
            type="primary", 
            use_container_width=True,
            on_click=processar_salvamento,
            args=(data, pedido, valor_txt, retira, origem, st.session_state['usuario'])
        )

    # ABA 2: VENDAS
    with tabs[1]:
        if not df_completo.empty:
            df_filtrado = df_completo.sort_index(ascending=False)
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    c1.markdown(f"<div class='card-title'>📦 {row['Pedido']}</div>", unsafe_allow_html=True)
                    valor_fmt = f"R$ {float(row['Valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    c2.markdown(f"<div class='card-valor'>{valor_fmt}</div>", unsafe_allow_html=True)
                    st.caption(f"📅 {row['Data']} | 👤 {row['Vendedor']}")
                    if st.button("✏️ Detalhes", key=f"btn_{index}", use_container_width=True):
                        modal_editar_venda(row['Pedido'], row, None)
        else: st.info("Sem vendas.")

# --- 8. INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if st.session_state['logado']: sistema_principal()
else: tela_login()
