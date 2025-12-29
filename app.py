import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# --- 1. CONFIGURAÇÃO DE CONEXÃO (SUPABASE) ---
# TROQUE PELA SUA URL REAL DO SUPABASE
DB_URL = "postgresql://postgres:[SUA_SENHA]@db.xyz.supabase.co:5432/postgres"

def get_connection():
    return psycopg2.connect(DB_URL)

# --- 2. FUNÇÕES DE BANCO DE DADOS ---

def verificar_login_banco(usuario_digitado, senha_digitada):
    """Busca o usuário no banco e valida a senha ignorando espaços extras"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # TRAP: Usamos TRIM para garantir que espaços no BD não atrapalhem
        query = "SELECT * FROM usuarios WHERE TRIM(usuario) = %s"
        cur.execute(query, (usuario_digitado.strip(),))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if user_data and str(user_data['senha']).strip() == str(senha_digitada).strip():
            return user_data
        return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

def carregar_vendas_banco():
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def salvar_venda_banco(nova):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO vendas (data, pedido, vendedor, retira_posterior, valor, pedido_origem) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (nova['data'], nova['pedido'], nova['vendedor'], 
                            nova['retira_posterior'], nova['valor'], nova['pedido_origem']))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False

def atualizar_status_entrega(id_venda, status):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE vendas SET retira_posterior = %s WHERE id = %s", (status, id_venda))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# --- 3. UTILITÁRIOS ---

def tratar_valor_float(texto):
    if not texto: return 0.0
    v = str(texto).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except:
        return 0.0

# --- 4. INTERFACE ---

st.set_page_config(page_title="MetaVendas Cloud", page_icon="🚀", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Acesso ao Sistema")
    with st.container(border=True):
        u_in = st.text_input("Usuário").lower() # Forçamos minúsculo para evitar erro de caixa
        s_in = st.text_input("Senha", type="password")
        
        if st.button("Entrar", use_container_width=True):
            user = verificar_login_banco(u_in, s_in)
            if user:
                st.session_state.update({
                    'logado': True, 
                    'usuario': user['usuario'], 
                    'nome': user['nome'], 
                    'funcao': user['funcao']
                })
                st.success("Login realizado!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos no banco de dados.")
else:
    # --- SISTEMA LOGADO ---
    st.sidebar.title(f"👤 {st.session_state['nome']}")
    if st.sidebar.button("Sair", type="primary"):
        st.session_state['logado'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📝 Lançar Venda", "📋 Relatório", "📦 Retira Posterior"])

    # ABA 1: LANÇAR
    with tab1:
        st.subheader("Novo Registro")
        with st.container(border=True):
            data_v = st.date_input("Data", date.today())
            ped_v = st.text_input("Número do Pedido", key="f_pedido")
            
            # Validação de duplicidade
            df_v = carregar_vendas_banco()
            if ped_v and not df_v.empty:
                if str(ped_v) in df_v['pedido'].astype(str).tolist():
                    st.warning("⚠️ Pedido já cadastrado!")

            val_v = st.text_input("Valor (Ex: 1874,97)", key="f_valor")
            ret_v = st.toggle("Retira Posterior?")
            ori_v = st.text_input("Origem", key="f_origem") if ret_v else "-"

            if st.button("💾 REGISTRAR", type="primary", use_container_width=True):
                valor_f = tratar_valor_float(val_v)
                if ped_v and valor_f > 0:
                    dados_venda = {
                        'data': data_v, 'pedido': ped_v, 'vendedor': st.session_state['nome'],
                        'retira_posterior': "Sim" if ret_v else "Não",
                        'valor': valor_f, 'pedido_origem': ori_v
                    }
                    if salvar_venda_banco(dados_venda):
                        # LIMPEZA DOS CAMPOS
                        st.session_state["f_pedido"] = ""
                        st.session_state["f_valor"] = ""
                        if "f_origem" in st.session_state: st.session_state["f_origem"] = ""
                        st.success("✅ Salvo!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Preencha pedido e valor.")

    # ABA 2: RELATÓRIO
    with tab2:
        st.subheader("Histórico de Vendas")
        df_rel = carregar_vendas_banco()
        if not df_rel.empty:
            # Filtro por vendedor (Admin vê tudo)
            if st.session_state['funcao'] != 'admin':
                df_rel = df_rel[df_rel['vendedor'] == st.session_state['nome']]
            
            total = df_rel['valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_rel, use_container_width=True, hide_index=True)
        else:
            st.info("Nada encontrado.")

    # ABA 3: RETIRA
    with tab3:
        st.subheader("Pedidos para Retirada")
        df_ret = carregar_vendas_banco()
        if not df_ret.empty:
            pendentes = df_ret[df_ret['retira_posterior'] == 'Sim']
            if not pendentes.empty:
                for _, r in pendentes.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2,2,1])
                        c1.write(f"**Ped: {r['pedido']}**")
                        c1.caption(f"Vendedor: {r['vendedor']}")
                        c2.write(f"Origem: {r['pedido_origem']}")
                        if c3.button("✅ Entregue", key=f"btn_{r['id']}"):
                            if atualizar_status_entrega(r['id'], 'Entregue'):
                                st.rerun()
            else:
                st.success("Nenhuma entrega pendente.")
