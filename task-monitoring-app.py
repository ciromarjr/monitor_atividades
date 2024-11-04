import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from hashlib import sha256
import time
import calendar
from PIL import Image
import io
import base64

# Configuração do tema e estilo
def configure_page():
    st.set_page_config(
        page_title="Sistema de Monitoramento",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personalizado
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stButton button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: #4CAF50;
            color: white;
        }
        .stTextInput > div > div > input {
            border-radius: 5px;
        }
        .status-card {
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        }
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        .stTab {
            background-color: #ffffff;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

# Configuração inicial do banco de dados
def init_db():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    # Tabela de usuários com campos adicionais
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL,
                  full_name TEXT,
                  email TEXT,
                  department TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de atividades com campos adicionais
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  activity TEXT NOT NULL,
                  description TEXT,
                  status TEXT NOT NULL,
                  priority TEXT,
                  category TEXT,
                  start_time TIMESTAMP,
                  end_time TIMESTAMP,
                  estimated_hours FLOAT,
                  actual_hours FLOAT,
                  comments TEXT,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Tabela de departamentos
    c.execute('''CREATE TABLE IF NOT EXISTS departments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  description TEXT)''')
    
    conn.commit()
    conn.close()

def create_activity_card(activity):
    status_colors = {
        'em_andamento': 'blue',
        'concluida': 'green',
        'pendente': 'orange',
        'atrasada': 'red'
    }
    
    color = status_colors.get(activity['status'], 'gray')
    
    return f"""
        <div class="status-card" style="border-left: 5px solid {color}">
            <h3>{activity['activity']}</h3>
            <p><strong>Status:</strong> {activity['status'].title()}</p>
            <p><strong>Responsável:</strong> {activity['username']}</p>
            <p><strong>Início:</strong> {activity['start_time']}</p>
            <p><strong>Prioridade:</strong> {activity['priority']}</p>
        </div>
    """

def show_user_profile():
    st.sidebar.title("Perfil do Usuário")
    
    # Adicionar avatar do usuário (placeholder)
    st.sidebar.image("https://via.placeholder.com/150", width=150)
    
    user_info = get_user_info(st.session_state.user['id'])
    st.sidebar.write(f"**Nome:** {user_info['full_name']}")
    st.sidebar.write(f"**Departamento:** {user_info['department']}")
    st.sidebar.write(f"**Função:** {user_info['role'].title()}")
    
    if st.sidebar.button("📝 Editar Perfil"):
        show_edit_profile_modal()
    
    st.sidebar.divider()
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.experimental_rerun()

def show_admin_interface():
    st.title("🎯 Dashboard Administrativo")
    
    # Menu superior com métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        show_metric_card("Total de Atividades", get_total_activities(), "📊")
    
    with col2:
        show_metric_card("Atividades Hoje", get_activities_today(), "📅")
    
    with col3:
        show_metric_card("Taxa de Conclusão", f"{get_completion_rate():.1f}%", "✅")
    
    with col4:
        show_metric_card("Usuários Ativos", get_active_users_count(), "👥")

    # Tabs principais
    tabs = st.tabs(["📋 Dashboard", "👥 Usuários", "📊 Relatórios", "⚙️ Configurações"])
    
    with tabs[0]:
        show_admin_dashboard()
    
    with tabs[1]:
        show_user_management()
    
    with tabs[2]:
        show_reports()
    
    with tabs[3]:
        show_settings()

def show_metric_card(title, value, icon):
    st.markdown(f"""
        <div class="metric-card">
            <h3>{icon} {title}</h3>
            <h2>{value}</h2>
        </div>
    """, unsafe_allow_html=True)

def show_admin_dashboard():
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_activities_timeline()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_department_performance()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_productivity_metrics()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_status_distribution()
        st.markdown('</div>', unsafe_allow_html=True)

def show_activities_timeline():
    st.subheader("Timeline de Atividades")
    
    # Dados de exemplo para o gráfico de timeline
    df = get_activities_timeline_data()
    
    fig = px.timeline(df, x_start='start_time', x_end='end_time', y='activity',
                     color='status', title='Timeline de Atividades')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def show_department_performance():
    st.subheader("Performance por Departamento")
    
    # Dados de exemplo para o gráfico de departamentos
    df = get_department_performance_data()
    
    fig = px.bar(df, x='department', y='completion_rate',
                 title='Taxa de Conclusão por Departamento')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def show_productivity_metrics():
    st.subheader("Métricas de Produtividade")
    
    # Dados de exemplo para o gráfico de produtividade
    df = get_productivity_data()
    
    fig = px.line(df, x='date', y='tasks_completed',
                  title='Produtividade ao Longo do Tempo')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def show_status_distribution():
    st.subheader("Distribuição de Status")
    
    # Dados de exemplo para o gráfico de distribuição
    df = get_status_distribution_data()
    
    fig = px.pie(df, values='count', names='status',
                 title='Distribuição de Status das Atividades')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def show_user_interface():
    st.title(f"👋 Bem-vindo(a), {get_user_info(st.session_state.user['id'])['full_name']}")
    
    # Menu rápido
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Nova Atividade"):
            show_new_activity_modal()
    with col2:
        if st.button("📋 Minhas Atividades"):
            show_user_activities(st.session_state.user['id'])
    with col3:
        if st.button("📊 Meu Dashboard"):
            show_user_dashboard()
    with col4:
        if st.button("⚙️ Configurações"):
            show_user_settings()

    # Atividades em andamento
    st.subheader("📌 Atividades em Andamento")
    show_ongoing_activities()
    
    # Dashboard pessoal
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_personal_productivity()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        show_personal_status_distribution()
        st.markdown('</div>', unsafe_allow_html=True)

def show_supervisor_interface():
    st.title("🔍 Dashboard de Supervisão")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        department = st.selectbox("Departamento", get_departments())
    with col2:
        status = st.multiselect("Status", ["Em andamento", "Concluída", "Pendente", "Atrasada"])
    with col3:
        date_range = st.date_input("Período", [datetime.now() - timedelta(days=30), datetime.now()])
    
    # Métricas principais
    show_supervisor_metrics()
    
    # Atividades em tempo real
    st.subheader("🔄 Atividades em Tempo Real")
    show_realtime_activities()
    
    # Gráficos e análises
    col1, col2 = st.columns(2)
    with col1:
        show_team_performance()
    with col2:
        show_workload_distribution()

# Funções auxiliares adicionais
def get_departments():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT name FROM departments')
    departments = [row[0] for row in c.fetchall()]
    conn.close()
    return departments

def get_user_info(user_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT username, full_name, email, department, role 
                 FROM users WHERE id = ?''', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'username': result[0],
            'full_name': result[1],
            'email': result[2],
            'department': result[3],
            'role': result[4]
        }
    return None

def get_active_users_count():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(DISTINCT user_id) FROM activities 
                 WHERE date(start_time) = date('now')''')
    result = c.fetchone()[0]
    conn.close()
    return result

# Função principal
def main():
    configure_page()
    init_db()
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        show_login_page()
    else:
        show_user_profile()
        
        if st.session_state.user['role'] == 'admin':
            show_admin_interface()
        elif st.session_state.user['role'] == 'supervisor':
            show_supervisor_interface()
        else:
            show_user_interface()

def show_login_page():
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: auto;
            padding: 2rem;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            user = login_user(username, password)
            if user:
                st.session_state.user = user
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha inválidos")
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
