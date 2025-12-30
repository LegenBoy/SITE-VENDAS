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
    [data-testid="stSidebar"] [data-testid="stImage"] img {
        border-radius: 50%; object-fit: cover;
        aspect-ratio: 1 / 1; border: 3px solid #2E86C1;
        display: block; margin-left: auto; margin-right: auto;
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

# --- CONVERSÃO DE VALOR ---
def converter_para_float(valor_texto):
    if not valor_texto: return 0.0
    # Remove R$, pontos de milhar e troca vírgula por ponto
    v = str(valor_texto).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

# --- 4. FUNÇÕES DE BANCO DE DADOS (GOOGLE SHEETS) ---
def carregar_vendas():
    colunas = ["Data", "Pedido", "Vendedor", "Retira_Posterior", "Valor", "Pedido_Origem"]
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        if df.empty: return pd.DataFrame(columns=colunas)
        df['Pedido'] = df['Pedido'].astype(str)
        # Garante que o valor lido do Sheets seja tratado como número
        df['Valor'] = df['Valor'].apply(lambda x: converter_para_float(x))
        return df
    except: return pd.DataFrame(columns=colunas)

def salvar_venda(nova_venda):
    try:
        sh = conectar_gsheets()
        ws = sh.sheet1
        linha = [
            str(nova_venda["Data"]), 
            str(nova_venda["Pedido"]), 
            nova_venda["Vendedor"], 
            nova_venda["Retira_Posterior"], 
            nova_venda["Valor"], 
            str(nova_venda["Pedido_Origem"])
        ]
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

def carregar_usuarios():
    try:
        sh = conectar_gsheets()
        ws = sh.worksheet("Usuarios")
        return pd.DataFrame(ws.get_all_records())
    except: return pd.DataFrame(columns=["Usuario", "Senha", "Nome", "Funcao", "Foto_URL"])

# --- FUNÇÃO EXTRA: ALTERAR STATUS RETIRA ---
def alterar_status_retira(pedido, dados_row, novo_status):
    dados_novos = dados_row.to_dict()
    dados_novos['Retira_Posterior'] = novo_status
    if atualizar_venda(pedido, dados_novos):
        st.toast(f"Status atualizado para: {novo_status}")

# --- CALLBACK DE SALVAMENTO COM LIMPEZA ---
def processar_salvamento():
    # Coleta dados dos inputs via session_state
    data = st.session_state.form_data
    pedido = st.session_state.form_pedido
    valor_txt = st.session_state.form_valor
    retira = st.session_state.form_retira
    origem = st.session_state.form_origem if retira else "-"
    usuario_atual = st.session_state['usuario_nome_sistema']
    
    if st.session_state.get('funcao') == 'admin' and st.session_state.get('form_vendedor'):
        usuario_atual = st.session_state['form_vendedor']

    valor_final = converter_para_float(valor_txt)
    
    if pedido and valor_final > 0:
        nova = {
            "Data": data, "Pedido": pedido, "Vendedor": usuario_atual,
            "Retira_Posterior": "Sim" if retira else "Não", 
            "Valor": valor_final, "Pedido_Origem": origem
        }
        
        if salvar_venda(nova):
            # LIMPA OS CAMPOS APÓS SALVAR
            st.session_state.form_pedido = ""
            st.session_state.form_valor = ""
            st.session_state.form_origem = ""
            st.session_state.form_retira = False
            st.toast("✅ Venda salva com sucesso!", icon="🚀")
            time.sleep(1)
    else:
        st.error("Preencha o Pedido e o Valor corretamente.")

# --- 5. LOGIN ---
def autenticar(usuario, senha):
    df = carregar_usuarios()
    if df.empty: return None
    user_row = df[df["Usuario"] == usuario]
    if not user_row.empty and str(user_row.iloc[0]["Senha"]) == str(senha):
        return user_row.iloc[0]
    return None

# --- 6. INTERFACE PRINCIPAL ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login MetaVendas")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("ENTRAR", use_container_width=True):
        dados = autenticar(u, s)
        if dados is not None:
            foto_url = dados["Foto_URL"] if "Foto_URL" in dados else ""
            st.session_state.update({'logado': True, 'usuario': dados["Usuario"], 'usuario_nome_sistema': dados["Nome"], 'funcao': dados["Funcao"], 'foto_url': foto_url})
            st.rerun()
        else: st.error("Incorreto.")
else:
    if st.session_state.get('foto_url'):
        st.sidebar.image(st.session_state['foto_url'], width=150)
    st.sidebar.title(f"👤 {st.session_state['usuario_nome_sistema']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📝 Lançar Venda", "📋 Ver Relatório", "📦 Retira Posterior"])

    with tab1:
        st.subheader("Novo Lançamento")
        with st.container(border=True):
            st.date_input("Data", date.today(), key="form_data")
            
            if st.session_state['funcao'] == 'admin':
                df_u = carregar_usuarios()
                lista_nomes = df_u['Nome'].tolist() if not df_u.empty else [st.session_state['usuario_nome_sistema']]
                st.selectbox("Vendedor", lista_nomes, key="form_vendedor")
            
            st.text_input("Nº Pedido", key="form_pedido")
            st.text_input("Valor (Ex: 1874,97)", key="form_valor")
            st.toggle("Retira Posterior?", key="form_retira")
            
            # Campo origem só aparece se o toggle for verdadeiro
            if st.session_state.form_retira:
                st.text_input("Vínculo (Pedido Origem)", key="form_origem")
            
            st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True, on_click=processar_salvamento)

    with tab2:
        st.subheader("Histórico de Vendas")
        df_vendas = carregar_vendas()
        if not df_vendas.empty:
            # Filtro por vendedor (Admin vê tudo)
            if st.session_state['funcao'] != 'admin':
                df_vendas = df_vendas[df_vendas['Vendedor'] == st.session_state['usuario_nome_sistema']]
            
            total = df_vendas['Valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_vendas, use_container_width=True, hide_index=True)
            
            # --- ÁREA DE EDIÇÃO (TRANSFERÊNCIA) ---
            if st.session_state['funcao'] == 'admin':
                st.divider()
                st.markdown("### ✏️ Editar / Transferir Venda")
                pedidos_lista = df_vendas['Pedido'].unique().tolist()
                pedido_selecionado = st.selectbox("Selecione o Pedido para Editar", [""] + pedidos_lista)
                
                if pedido_selecionado:
                    row = df_vendas[df_vendas['Pedido'] == pedido_selecionado].iloc[0]
                    with st.form("form_editar"):
                        c1, c2 = st.columns(2)
                        n_data = c1.text_input("Data (YYYY-MM-DD)", value=row['Data'])
                        
                        # Admin pode trocar o vendedor
                        df_u = carregar_usuarios()
                        lista_nomes = df_u['Nome'].tolist() if not df_u.empty else [row['Vendedor']]
                        idx_v = lista_nomes.index(row['Vendedor']) if row['Vendedor'] in lista_nomes else 0
                        n_vendedor = c2.selectbox("Vendedor", lista_nomes, index=idx_v)
                        
                        n_valor = c1.text_input("Valor", value=row['Valor'])
                        n_retira = c2.selectbox("Retira?", ["Sim", "Não", "Entregue"], index=["Sim", "Não", "Entregue"].index(row['Retira_Posterior']))
                        n_origem = st.text_input("Origem", value=row['Pedido_Origem'])
                        
                        if st.form_submit_button("💾 Salvar Alterações"):
                            dados_up = {
                                "Data": n_data, "Pedido": pedido_selecionado, "Vendedor": n_vendedor,
                                "Retira_Posterior": n_retira, "Valor": converter_para_float(n_valor), "Pedido_Origem": n_origem
                            }
                            if atualizar_venda(pedido_selecionado, dados_up):
                                st.success("Atualizado!")
                                time.sleep(1)
                                st.rerun()
        else:
            st.info("Nenhuma venda encontrada.")

    with tab3:
        st.subheader("Controle de Entregas (Retira)")
        df_all = carregar_vendas()
        if not df_all.empty:
            # Admin vê tudo, Vendedor vê só as suas (ou tudo se preferir)
            if st.session_state['funcao'] != 'admin':
                df_retira = df_all[(df_all['Vendedor'] == st.session_state['usuario_nome_sistema']) & (df_all['Retira_Posterior'].isin(['Sim', 'Entregue']))]
            else:
                df_retira = df_all[df_all['Retira_Posterior'].isin(['Sim', 'Entregue'])]
            
            if not df_retira.empty:
                pendentes = df_retira[df_retira['Retira_Posterior'] == 'Sim']
                entregues = df_retira[df_retira['Retira_Posterior'] == 'Entregue']
                
                st.markdown(f"**⏳ Pendentes ({len(pendentes)})**")
                for i, r in pendentes.iterrows():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"📦 **{r['Pedido']}** - {r['Vendedor']}")
                    c2.write(f"📅 {r['Data']}")
                    if c3.button("✅ Entregar", key=f"btn_ent_{r['Pedido']}"):
                        alterar_status_retira(r['Pedido'], r, "Entregue")
                        time.sleep(0.5); st.rerun()
                
                st.divider()
                with st.expander(f"✅ Histórico de Entregues ({len(entregues)})"):
                    for i, r in entregues.iterrows():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"📦 {r['Pedido']} - {r['Vendedor']}")
                        c2.caption("Entregue")
                        if c3.button("↩️ Desfazer", key=f"btn_des_{r['Pedido']}"):
                            alterar_status_retira(r['Pedido'], r, "Sim")
                            time.sleep(0.5); st.rerun()
            else:
                st.info("Nenhum item para retirada.")
        else:
            st.info("Sem dados.")
