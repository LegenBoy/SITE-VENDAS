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

# --- MÁGICA DE FORMATAÇÃO AUTOMÁTICA ---
def formatar_input_br():
    """
    Função chamada automaticamente quando o usuário aperta Enter no campo de valor.
    Ela pega o que foi digitado (ex: 1874,50) e transforma em visual (1.874,50)
    """
    # Verifica qual campo chamou a função (temos um no Lançar e um no Editar)
    if "valor_pendente" in st.session_state:
        chave = "valor_pendente"
    elif "valor_editar_pendente" in st.session_state:
        chave = "valor_editar_pendente"
    else:
        return

    valor_digitado = st.session_state[chave]
    if not valor_digitado: return

    try:
        # Limpeza: Tira R$, espaços e pontos antigos
        v = str(valor_digitado).replace("R$", "").strip()
        if "." in v and "," in v: v = v.replace(".", "") # Tira o ponto de milhar se o usuario digitou
        
        # Troca virgula por ponto para o Python entender matematica
        v_float = float(v.replace(",", "."))
        
        # Formata de volta para BR (1.000,00)
        # {:,.2f} gera 1,000.00 -> trocamos os sinais
        novo_valor = f"{v_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Atualiza o campo na tela
        st.session_state[chave] = novo_valor
    except ValueError:
        pass # Se digitou letra, não faz nada

def converter_para_float(valor_texto):
    """Converte o texto formatado (1.000,00) para float (1000.00) para salvar"""
    if not valor_texto: return 0.0
    v = str(valor_texto).replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

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
        
        # Valor formatado para edição
        valor_inicial = f"{float(dados_atuais['Valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        novo_valor_txt = st.text_input("Valor (R$)", value=valor_inicial)
        
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
            # Converte
            v_final = converter_para_float(novo_valor_txt)
            update = {"Data": nova_data, "Pedido": novo_pedido, "Vendedor": novo_vendedor, "Valor": v_final,
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

    st.markdown("### 🚀 Painel MetaVendas")
    with st.spinner("..."):
        df_vendas = carregar_vendas()
        df_usuarios = carregar_usuarios()

    if st.session_state['funcao'] == 'admin': df_completo = df_vendas
    else: df_completo = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario']]

    abas = ["📝 Lançar", "📋 Vendas"]
    if st.session_state['funcao'] == 'admin': abas.append("⚙️ Equipe")
    tabs = st.tabs(abas)

    # ABA 1: LANÇAR (COM FORMATAÇÃO AUTOMATICA)
    with tabs[0]:
        data = st.date_input("Data", date.today())
        pedido = st.text_input("Nº Pedido")
        
        # --- CAMPO COM FORMATAÇÃO ---
        # key="valor_pendente" liga ao on_change
        valor_txt = st.text_input(
            "Valor R$", 
            key="valor_pendente", 
            on_change=formatar_input_br, 
            placeholder="0,00"
        )
        
        retira = st.toggle("É Retira Posterior?")
        origem = st.text_input("Vínculo (Pedido Origem)") if retira else "-"

        if st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True):
            valor_final = converter_para_float(valor_txt)
            
            if pedido and valor_final > 0:
                nova = {"Data": data, "Pedido": pedido, "Vendedor": st.session_state['usuario'],
                        "Retira_Posterior": "Sim" if retira else "Não", "Valor": valor_final, "Pedido_Origem": origem}
                if salvar_venda(nova): 
                    # Limpa o campo após salvar
                    st.session_state["valor_pendente"] = "" 
                    st.success("Salvo!"); time.sleep(1); st.rerun()
            else: st.error("Valor inválido ou Pedido vazio.")

    # ABA 2: LISTA DE CARDS
    with tabs[1]:
        with st.expander("🔍 Filtros de Busca"):
            f_txt = st.text_input("Buscar Pedido")
            lista_vendedores = df_completo['Vendedor'].unique().tolist()
            if st.session_state['funcao'] == 'admin': f_vend = st.multiselect("Vendedor", options=lista_vendedores)
            else: f_vend = [st.session_state['usuario']]

        df_filtrado = df_completo.copy()
        if f_txt: df_filtrado = df_filtrado[df_filtrado['Pedido'].str.contains(f_txt, case=False)]
        if f_vend and st.session_state['funcao'] == 'admin': df_filtrado = df_filtrado[df_filtrado['Vendedor'].isin(f_vend)]
        
        if not df_filtrado.empty:
            df_filtrado = df_filtrado.sort_index(ascending=False)
            st.markdown(f"**{len(df_filtrado)} vendas encontradas**")
            
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    c_top1, c_top2 = st.columns([2, 1])
                    c_top1.markdown(f"<div class='card-title'>📦 {row['Pedido']}</div>", unsafe_allow_html=True)
                    
                    # Formatação visual bonita
                    valor_fmt = f"{row['Valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    c_top2.markdown(f"<div class='card-valor'>R$ {valor_fmt}</div>", unsafe_allow_html=True)
                    
                    c_mid1, c_mid2, c_mid3 = st.columns([1, 1, 1])
                    c_mid1.caption(f"📅 {row['Data']}")
                    c_mid2.caption(f"👤 {row['Vendedor']}")
                    
                    if row['Retira_Posterior'] == "Sim": c_mid3.markdown("⚠️ **Retira**")
                    else: c_mid3.markdown("✅ **Normal**")
                    
                    if row['Pedido_Origem'] and row['Pedido_Origem'] != "-":
                        st.caption(f"🔗 Vínculo: {row['Pedido_Origem']}")
                    
                    if st.button("✏️ Editar", key=f"btn_{row['Pedido']}", use_container_width=True):
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
