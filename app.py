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

# --- 2. FUNÇÕES DE BANCO DE DADOS (APENAS SUPABASE) ---

def carregar_vendas_supabase():
    try:
        conn = get_connection()
        # O pandas consegue ler direto do banco SQL
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
        cur.execute(query, (
            nova['data'], 
            nova['pedido'], 
            nova['vendedor'], 
            nova['retira_posterior'], 
            nova['valor'], 
            nova['pedido_origem']
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 3. UTILITÁRIOS ---

def converter_valor_br_para_float(txt):
    if not txt: return 0.0
    # Remove R$, espaços e ajusta vírgula/ponto
    v = str(txt).replace("R$", "").strip()
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except:
        return 0.0

# --- 4. INTERFACE DO SISTEMA ---

st.set_page_config(page_title="MetaVendas Supabase", page_icon="🚀")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    # TELA DE LOGIN SIMPLES
    st.title("🔐 Acesso ao Sistema")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and s == "123": # Altere para seu uso
            st.session_state.update({'logado': True, 'usuario': u})
            st.rerun()
else:
    # SISTEMA PRINCIPAL
    st.sidebar.title(f"Usuário: {st.session_state['usuario']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    tab1, tab2 = st.tabs(["📝 Lançar Venda", "📋 Ver Relatório"])

    with tab1:
        st.subheader("Novo Registro")
        with st.container(border=True):
            data_venda = st.date_input("Data", date.today())
            # KEYs são essenciais para o "Reset" do formulário
            n_pedido = st.text_input("Número do Pedido", key="form_pedido")
            valor_input = st.text_input("Valor (Ex: 1.874,97)", key="form_valor")
            is_retira = st.toggle("Retira Posterior?")
            vinculo = st.text_input("Pedido de Origem", key="form_origem") if is_retira else "-"

            if st.button("💾 SALVAR NO SUPABASE", type="primary", use_container_width=True):
                v_float = converter_valor_br_para_float(valor_input)
                
                if n_pedido and v_float > 0:
                    dados = {
                        'data': data_venda,
                        'pedido': n_pedido,
                        'vendedor': st.session_state['usuario'],
                        'retira_posterior': "Sim" if is_retira else "Não",
                        'valor': v_float,
                        'pedido_origem': vinculo
                    }
                    
                    if salvar_venda_supabase(dados):
                        # LIMPA OS CAMPOS PARA O PRÓXIMO LANÇAMENTO
                        st.session_state["form_pedido"] = ""
                        st.session_state["form_valor"] = ""
                        if "form_origem" in st.session_state: st.session_state["form_origem"] = ""
                        
                        st.success("✅ Venda salva com sucesso no banco de dados!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("⚠️ Preencha o pedido e um valor válido.")

    with tab2:
        st.subheader("Vendas Registradas")
        df_vendas = carregar_vendas_supabase()
        
        if not df_vendas.empty:
            # Resumo rápido
            total = df_vendas['valor'].sum()
            st.metric("Total Acumulado", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            # Tabela de dados
            st.dataframe(df_vendas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda encontrada no Supabase.")
