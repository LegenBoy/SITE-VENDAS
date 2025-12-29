import streamlit as st
import pandas as pd
from datetime import date
import psycopg2 # Biblioteca para conectar no PostgreSQL
import time

# --- CONFIGURAÇÃO DE CONEXÃO ---
# Pegue esses dados no seu painel do Supabase (Project Settings > Database)
DB_CONFIG = "postgresql://postgres:[SUA_SENHA]@db.xyz.supabase.co:5432/postgres"

def get_connection():
    return psycopg2.connect(DB_CONFIG)

# --- 1. FUNÇÕES DE BANCO DE DADOS (AGORA INSTANTÂNEAS) ---

def carregar_vendas():
    try:
        conn = get_connection()
        query = "SELECT * FROM vendas ORDER BY id DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

def salvar_venda(nova):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """INSERT INTO vendas (data, pedido, vendedor, retira_posterior, valor, pedido_origem) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cur.execute(query, (nova['data'], nova['pedido'], nova['vendedor'], 
                            nova['retira_posterior'], nova['valor'], nova['pedido_origem']))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except: return False

# --- 2. LOGICA DO SISTEMA ---

def converter_para_float(valor_texto):
    if not valor_texto: return 0.0
    v = str(valor_texto).replace("R$", "").strip()
    if "," in v: v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

def processar_salvamento(data, pedido, valor_txt, retira, origem, usuario_atual):
    valor_final = converter_para_float(valor_txt)
    if pedido and valor_final > 0:
        nova = {
            'data': data, 'pedido': pedido, 'vendedor': usuario_atual,
            'retira_posterior': "Sim" if retira else "Não",
            'valor': valor_final, 'pedido_origem': origem
        }
        if salvar_venda(nova):
            # LIMPANDO CAMPOS (Atendendo seu pedido)
            st.session_state["input_pedido"] = ""
            st.session_state["input_valor"] = ""
            st.session_state["input_origem"] = ""
            st.toast("✅ Registrado no Banco de Dados!")
    else:
        st.error("Dados inválidos.")

# --- 3. INTERFACE (Simplificada e limpa) ---

if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("📱 Login Sistema")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        # Aqui você faria a consulta na tabela 'usuarios'
        if u == "admin" and s == "123": # Exemplo simples
            st.session_state.update({'logado': True, 'usuario': u, 'nome': 'Admin', 'funcao': 'admin'})
            st.rerun()
else:
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    
    tab1, tab2 = st.tabs(["📝 Lançar", "📋 Relatório"])
    
    with tab1:
        data = st.date_input("Data", date.today())
        # Campos com KEYS para limpeza automática
        ped = st.text_input("Pedido", key="input_pedido")
        val = st.text_input("Valor", key="input_valor")
        ret = st.toggle("Retira?")
        ori = st.text_input("Vínculo", key="input_origem") if ret else "-"
        
        st.button("💾 REGISTRAR", type="primary", use_container_width=True,
                  on_click=processar_salvamento, args=(data, ped, val, ret, ori, st.session_state['usuario']))

    with tab2:
        df = carregar_vendas()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
