import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# --- 1. CONFIGURAÇÃO DE CONEXÃO (SUPABASE) ---
# Substitua pela sua URI que você copiou do Supabase
DB_URL = "postgresql://postgres:[SUA_SENHA]@db.xyz.supabase.co:5432/postgres"

def get_connection():
    return psycopg2.connect(DB_URL)

# --- 2. FUNÇÕES DE BANCO DE DADOS ---

def verificar_login(usuario, senha):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha))
        user = cur.fetchone()
        conn.close()
        return user
    except: return None

def carregar_vendas_supabase():
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def salvar_venda_supabase(nova):
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
    except: return False

def atualizar_status_venda(id_venda, novo_status):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE vendas SET retira_posterior = %s WHERE id = %s", (novo_status, id_venda))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- 3. UTILITÁRIOS ---

def converter_valor_br_para_float(txt):
    if not txt: return 0.0
    v = str(txt).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

# --- 4. INTERFACE DO SISTEMA ---

st.set_page_config(page_title="MetaVendas Cloud", page_icon="🚀", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Acesso ao Sistema")
    with st.container(border=True):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            user = verificar_login(u, s)
            if user:
                st.session_state.update({
                    'logado': True, 
                    'usuario': user['usuario'], 
                    'nome': user['nome'], 
                    'funcao': user['funcao']
                })
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # BARRA LATERAL
    st.sidebar.title(f"👤 {st.session_state['nome']}")
    if st.sidebar.button("Sair", type="primary"):
        st.session_state['logado'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📝 Lançar Venda", "📋 Relatório", "📦 Retira Posterior"])

    # --- ABA 1: LANÇAR ---
    with tab1:
        st.subheader("Novo Registro")
        with st.container(border=True):
            data_venda = st.date_input("Data", date.today())
            
            # Avisar se o pedido já existe em tempo real
            n_pedido = st.text_input("Número do Pedido", key="form_pedido")
            df_check = carregar_vendas_supabase()
            if n_pedido and not df_check.empty:
                if n_pedido in df_check['pedido'].astype(str).tolist():
                    st.warning(f"⚠️ Atenção: O pedido {n_pedido} já foi lançado!")

            # Campo de valor limpo (sem automação que atrapalha)
            valor_input = st.text_input("Valor (Ex: 1874,97)", key="form_valor")
            
            is_retira = st.toggle("É Retira Posterior?")
            vinculo = st.text_input("Pedido de Origem", key="form_origem") if is_retira else "-"

            if st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True):
                v_float = converter_valor_br_para_float(valor_input)
                
                if n_pedido and v_float > 0:
                    dados = {
                        'data': data_venda,
                        'pedido': n_pedido,
                        'vendedor': st.session_state['nome'],
                        'retira_posterior': "Sim" if is_retira else "Não",
                        'valor': v_float,
                        'pedido_origem': vinculo
                    }
                    
                    if salvar_venda_supabase(dados):
                        # LIMPANDO OS CAMPOS APÓS SUCESSO
                        st.session_state["form_pedido"] = ""
                        st.session_state["form_valor"] = ""
                        if "form_origem" in st.session_state: st.session_state["form_origem"] = ""
                        
                        st.success("✅ Venda salva com sucesso!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("⚠️ Erro: Preencha o número do pedido e um valor válido.")

    # --- ABA 2: RELATÓRIO ---
    with tab2:
        st.subheader("Vendas Registradas")
        df_vendas = carregar_vendas_supabase()
        
        if not df_vendas.empty:
            # Filtro básico por vendedor (Admin vê tudo, Vendedor vê o seu)
            if st.session_state['funcao'] != 'admin':
                df_vendas = df_vendas[df_vendas['vendedor'] == st.session_state['nome']]

            total = df_vendas['valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_vendas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda encontrada.")

    # --- ABA 3: RETIRA POSTERIOR ---
    with tab3:
        st.subheader("Controle de Entregas")
        df_retira = carregar_vendas_supabase()
        if not df_retira.empty:
            # Filtra apenas o que é Retira e ainda não foi entregue
            pendentes = df_retira[df_retira['retira_posterior'] == 'Sim']
            
            if not pendentes.empty:
                for _, row in pendentes.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.write(f"**Pedido: {row['pedido']}**")
                        c1.caption(f"Vendedor: {row['vendedor']}")
                        c2.write(f"Origem: {row['pedido_origem']}")
                        if c3.button("✅ Marcar Entregue", key=f"ent_{row['id']}"):
                            if atualizar_status_venda(row['id'], 'Entregue'):
                                st.rerun()
            else:
                st.success("Tudo entregue! Nenhuma retirada pendente.")
