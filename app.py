import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# --- COLE SUA URL DO SUPABASE AQUI ---
DB_URL = "postgresql://postgres:[SUA_SENHA]@db.xyz.supabase.co:5432/postgres"

def get_connection():
    return psycopg2.connect(postgresql://postgres:!@#@Gabriel@@#!@db.buwezivkuvfkzyfozwnn.supabase.co:5432/postgres)

# --- FUNÇÕES DE BANCO ---
def carregar_vendas():
    try:
        conn = get_connection()
        query = "SELECT * FROM vendas ORDER BY id DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except: return pd.DataFrame()

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

def converter_valor(txt):
    if not txt: return 0.0
    v = str(txt).replace("R$", "").strip()
    if "," in v: v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except: return 0.0

# --- INTERFACE ---
st.set_page_config(page_title="MetaVendas Cloud", layout="wide")

if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("📱 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and s == "123": # Login simples inicial
            st.session_state.update({'logado': True, 'usuario': u, 'nome': 'Admin'})
            st.rerun()
else:
    tab1, tab2 = st.tabs(["📝 Lançar", "📋 Relatório"])
    
    with tab1:
        with st.container(border=True):
            data = st.date_input("Data", date.today())
            # KEYs permitem que o script limpe os campos após salvar
            ped = st.text_input("Nº Pedido", key="input_pedido")
            val = st.text_input("Valor (Ex: 1874,97)", key="input_valor")
            ret = st.toggle("Retira Posterior?")
            ori = st.text_input("Vínculo", key="input_origem") if ret else "-"
            
            if st.button("💾 REGISTRAR VENDA", type="primary", use_container_width=True):
                valor_final = converter_valor(val)
                if ped and valor_final > 0:
                    nova_venda = {
                        'data': data, 'pedido': ped, 'vendedor': st.session_state['usuario'],
                        'retira_posterior': "Sim" if ret else "Não",
                        'valor': valor_final, 'pedido_origem': ori
                    }
                    if salvar_venda(nova_venda):
                        # LIMPANDO CAMPOS AUTOMATICAMENTE
                        st.session_state["input_pedido"] = ""
                        st.session_state["input_valor"] = ""
                        if "input_origem" in st.session_state: st.session_state["input_origem"] = ""
                        st.toast("✅ Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()
                else: st.error("Verifique Pedido e Valor.")

    with tab2:
        df = carregar_vendas()
        if not df.empty:
            # Mostra o total para conferência rápida
            total = df['valor'].sum()
            st.metric("Total Vendido", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df, use_container_width=True)
