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

# Configuração inicial do banco de dados e criação do usuário admin
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
                  last_login TIMESTAMP,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  status TEXT DEFAULT 'active')''')
    
    # Tabela de atividades com campos adicionais
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  activity TEXT NOT NULL,
                  description TEXT,
                  status TEXT NOT NULL DEFAULT 'pendente',
                  priority TEXT DEFAULT 'Média',
                  category TEXT,
                  start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  end_time TIMESTAMP,
                  estimated_hours FLOAT DEFAULT 1.0,
                  actual_hours FLOAT,
                  comments TEXT,
                  attachments TEXT,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Tabela de departamentos
    c.execute('''CREATE TABLE IF NOT EXISTS departments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  description TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de logs do sistema
    c.execute('''CREATE TABLE IF NOT EXISTS system_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  details TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Criar usuário admin se não existir
    create_admin_user(c)
    
    # Criar departamentos padrão
    create_default_departments(c)
    
    conn.commit()
    conn.close()
def check_database():
    """Verifica se o banco de dados existe e está consistente"""
    try:
        conn = sqlite3.connect('team_activities.db')
        c = conn.cursor()
        
        # Verifica se as tabelas existem
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        
        required_tables = ['users', 'activities', 'departments', 'system_logs']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"Tabelas faltando: {missing_tables}")
            return False
            
        return True
        
    except sqlite3.Error as e:
        print(f"Erro ao verificar banco de dados: {e}")
        return False
    finally:
        conn.close()
def create_admin_user(cursor):
    # Verifica se o usuário admin já existe
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        # Criar usuário admin com senha admin
        hashed_password = sha256('admin'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password, role, full_name, email, department, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', hashed_password, 'admin', 'Administrador', 'admin@empresa.com', 'TI', datetime.now()))

def create_default_departments(cursor):
    departments = [
        ('TI', 'Tecnologia da Informação'),
        ('RH', 'Recursos Humanos'),
        ('Financeiro', 'Departamento Financeiro'),
        ('Comercial', 'Departamento Comercial'),
        ('Operações', 'Departamento de Operações')
    ]
    
    for dept_name, dept_desc in departments:
        cursor.execute('INSERT OR IGNORE INTO departments (name, description) VALUES (?, ?)',
                      (dept_name, dept_desc))
# Função corrigida para criar atividades
def create_activity(user_id, activity, description, priority, category, estimated_hours, comments, start_date=None, status='em_andamento'):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Se start_date não for fornecido, usa a data atual
        if not start_date:
            start_date = datetime.now()
            
        c.execute('''INSERT INTO activities 
                     (user_id, activity, description, status, priority, category, 
                      start_time, estimated_hours, comments, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, activity, description, status, priority, category,
                   start_date, estimated_hours, comments, datetime.now()))
        
        activity_id = c.lastrowid
        conn.commit()
        
        # Log da criação da atividade
        log_system_action(user_id, "create_activity", f"Nova atividade criada: {activity}")
        
        return activity_id
        
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Erro ao criar atividade: {str(e)}")
    finally:
        conn.close()

# Nova função para adicionar tags às atividades
def add_activity_tags(activity_id, tags):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Criar tabela de tags se não existir
        c.execute('''CREATE TABLE IF NOT EXISTS activity_tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      activity_id INTEGER,
                      tag TEXT,
                      FOREIGN KEY (activity_id) REFERENCES activities(id))''')
        
        # Adicionar tags
        for tag in tags:
            c.execute('INSERT INTO activity_tags (activity_id, tag) VALUES (?, ?)',
                     (activity_id, tag))
        
        conn.commit()
    finally:
        conn.close()

# Nova função para gerenciar dependências entre atividades
def manage_activity_dependencies(activity_id, dependent_on=None, required_for=None):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Criar tabela de dependências se não existir
        c.execute('''CREATE TABLE IF NOT EXISTS activity_dependencies
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      activity_id INTEGER,
                      depends_on INTEGER,
                      FOREIGN KEY (activity_id) REFERENCES activities(id),
                      FOREIGN KEY (depends_on) REFERENCES activities(id))''')
        
        if dependent_on:
            for dep_id in dependent_on:
                c.execute('INSERT INTO activity_dependencies (activity_id, depends_on) VALUES (?, ?)',
                         (activity_id, dep_id))
        
        if required_for:
            for req_id in required_for:
                c.execute('INSERT INTO activity_dependencies (activity_id, depends_on) VALUES (?, ?)',
                         (req_id, activity_id))
        
        conn.commit()
    finally:
        conn.close()

# Nova função para adicionar comentários/histórico às atividades
def add_activity_comment(activity_id, user_id, comment):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Criar tabela de comentários se não existir
        c.execute('''CREATE TABLE IF NOT EXISTS activity_comments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      activity_id INTEGER,
                      user_id INTEGER,
                      comment TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (activity_id) REFERENCES activities(id),
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        c.execute('''INSERT INTO activity_comments 
                     (activity_id, user_id, comment)
                     VALUES (?, ?, ?)''',
                  (activity_id, user_id, comment))
        
        conn.commit()
    finally:
        conn.close()

# Nova função para rastrear tempo gasto em atividades
def track_activity_time(activity_id, user_id, hours_spent, description=None):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Criar tabela de registro de tempo se não existir
        c.execute('''CREATE TABLE IF NOT EXISTS time_tracking
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      activity_id INTEGER,
                      user_id INTEGER,
                      hours_spent FLOAT,
                      description TEXT,
                      tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (activity_id) REFERENCES activities(id),
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        c.execute('''INSERT INTO time_tracking 
                     (activity_id, user_id, hours_spent, description)
                     VALUES (?, ?, ?, ?)''',
                  (activity_id, user_id, hours_spent, description))
        
        # Atualizar total de horas na atividade
        c.execute('''UPDATE activities 
                     SET actual_hours = (
                         SELECT SUM(hours_spent) 
                         FROM time_tracking 
                         WHERE activity_id = ?
                     )
                     WHERE id = ?''',
                  (activity_id, activity_id))
        
        conn.commit()
    finally:
        conn.close()
def create_activity(user_id, activity, description, priority, category, estimated_hours, comments):
    """
    Cria uma nova atividade no sistema
    
    Parâmetros:
    - user_id: ID do usuário responsável
    - activity: Título da atividade
    - description: Descrição da atividade
    - priority: Prioridade (Baixa, Média, Alta, Urgente)
    - category: Categoria da atividade
    - estimated_hours: Horas estimadas
    - comments: Comentários
    """
    if not activity or not description:
        st.error("Título e descrição são obrigatórios")
        return None
        
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        start_time = datetime.now()
            
        c.execute('''INSERT INTO activities 
                     (user_id, activity, description, status, priority, category, 
                      start_time, estimated_hours, comments, last_updated)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, activity, description, 'em_andamento', priority, category,
                   start_time, estimated_hours, comments, datetime.now()))
        
        activity_id = c.lastrowid
        conn.commit()
        
        # Log da criação da atividade
        log_system_action(user_id, "create_activity", f"Nova atividade criada: {activity}")
        
        return activity_id
        
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"Erro ao criar atividade: {str(e)}")
        return None
    finally:
        conn.close()

def show_new_activity_form(user_id):
    st.subheader("➕ Nova Atividade")
    
    with st.form("new_activity_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            activity = st.text_input("Título da Atividade*", key="activity_title")
            description = st.text_area("Descrição*", key="activity_desc")
            priority = st.selectbox("Prioridade", 
                                  ["Baixa", "Média", "Alta", "Urgente"],
                                  key="activity_priority")
        
        with col2:
            category = st.selectbox("Categoria", 
                                  ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"],
                                  key="activity_category")
            estimated_hours = st.number_input("Horas Estimadas", 
                                           min_value=0.5, 
                                           value=1.0,
                                           key="activity_hours")
        
        comments = st.text_area("Comentários", key="activity_comments")
        
        if st.form_submit_button("Criar Atividade"):
            if activity and description:
                activity_id = create_activity(
                    user_id,
                    activity,
                    description,
                    priority,
                    category,
                    estimated_hours,
                    comments
                )
                
                if activity_id:
                    st.success("Atividade criada com sucesso!")
                    time.sleep(1)
                    st.experimental_rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios")

def show_admin_new_activity():
    st.subheader("Nova Atividade")
    
    with st.form("new_activity_admin_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            responsible = st.selectbox("Responsável*", get_all_users_names())
            activity = st.text_input("Título da Atividade*")
            description = st.text_area("Descrição*")
            priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
        
        with col2:
            category = st.selectbox("Categoria", ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"])
            estimated_hours = st.number_input("Horas Estimadas", min_value=0.5, value=1.0)
        
        comments = st.text_area("Comentários")
        
        if st.form_submit_button("Criar Atividade"):
            if not activity or not description:
                st.error("Por favor, preencha todos os campos obrigatórios")
                return
                
            user_id = get_user_id_by_name(responsible)
            if not user_id:
                st.error("Usuário responsável não encontrado")
                return
                
            activity_id = create_activity(
                user_id,
                activity,
                description,
                priority,
                category,
                estimated_hours,
                comments
            )
            
            if activity_id:
                st.success("Atividade criada com sucesso!")
                time.sleep(1)
                st.experimental_rerun()
# Nova função para definir lembretes/notificações
def set_activity_reminder(activity_id, user_id, reminder_date, reminder_type='email'):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    try:
        # Criar tabela de lembretes se não existir
        c.execute('''CREATE TABLE IF NOT EXISTS activity_reminders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      activity_id INTEGER,
                      user_id INTEGER,
                      reminder_date TIMESTAMP,
                      reminder_type TEXT,
                      sent BOOLEAN DEFAULT FALSE,
                      FOREIGN KEY (activity_id) REFERENCES activities(id),
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        c.execute('''INSERT INTO activity_reminders 
                     (activity_id, user_id, reminder_date, reminder_type)
                     VALUES (?, ?, ?, ?)''',
                  (activity_id, user_id, reminder_date, reminder_type))
        
        conn.commit()
    finally:
        conn.close()

# Função melhorada para mostrar formulário de nova atividade
def show_new_activity_form(user_id):
    st.subheader("➕ Nova Atividade")
    
    with st.form("new_activity_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            activity = st.text_input("Título da Atividade*", key="activity_title")
            description = st.text_area("Descrição*", key="activity_desc")
            priority = st.selectbox("Prioridade", 
                                  ["Baixa", "Média", "Alta", "Urgente"],
                                  key="activity_priority")
        
        with col2:
            category = st.selectbox("Categoria", 
                                  ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"],
                                  key="activity_category")
            estimated_hours = st.number_input("Horas Estimadas", 
                                           min_value=0.5, 
                                           value=1.0,
                                           key="activity_hours")
            start_date = st.date_input("Data de Início", key="activity_start")
        
        comments = st.text_area("Comentários", key="activity_comments")
        
        if st.form_submit_button("Criar Atividade"):
            if activity and description:
                activity_id = create_activity(
                    user_id=user_id,
                    activity=activity,
                    description=description,
                    priority=priority,
                    category=category,
                    estimated_hours=estimated_hours,
                    comments=comments,
                    start_date=start_date
                )
                
                if activity_id:
                    st.success("Atividade criada com sucesso!")
                    time.sleep(1)  # Pequena pausa para mostrar a mensagem
                    st.experimental_rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios")

# Função auxiliar para obter atividades disponíveis para dependências
def get_available_activities():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT id, activity FROM activities WHERE status != "concluida"')
    activities = c.fetchall()
    conn.close()
    return [(str(id), title) for id, title in activities]

def log_system_action(user_id, action, details):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''INSERT INTO system_logs (user_id, action, details, timestamp)
                 VALUES (?, ?, ?, ?)''', (user_id, action, details, datetime.now()))
    conn.commit()
    conn.close()

def show_admin_interface():
    st.title("🎯 Dashboard Administrativo")
    
    # Menu lateral para navegação
    menu = st.sidebar.selectbox(
        "Menu",
        ["Dashboard", "Usuários", "Atividades", "Departamentos", "Relatórios", "Configurações"]
    )
    
    if menu == "Dashboard":
        show_admin_dashboard()
    elif menu == "Usuários":
        show_admin_users()
    elif menu == "Atividades":
        show_admin_activities()
    elif menu == "Departamentos":
        show_department_management()
    elif menu == "Relatórios":
        show_reports()
    elif menu == "Configurações":
        show_settings()
# Função show_new_activity_form atualizada
def show_new_activity_form(user_id):
    st.subheader("➕ Nova Atividade")
    
    with st.form("new_activity_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            activity = st.text_input("Título da Atividade*")
            description = st.text_area("Descrição")
            priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
        
        with col2:
            category = st.selectbox("Categoria", ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"])
            estimated_hours = st.number_input("Horas Estimadas", min_value=0.5, value=1.0)
            start_date = st.date_input("Data de Início")
        
        comments = st.text_area("Comentários")
        
        if st.form_submit_button("Criar Atividade"):
            if not activity:
                st.error("Por favor, preencha o título da atividade")
                return
                
            activity_id = create_activity(
                user_id=user_id,
                activity=activity,
                description=description,
                priority=priority,
                category=category,
                estimated_hours=estimated_hours,
                comments=comments,
                start_date=start_date
            )
            
            if activity_id:
                st.success("Atividade criada com sucesso!")
                st.experimental_rerun()
def show_admin_users():
    st.title("👥 Gestão de Usuários")
    
    # Tabs para diferentes ações
    tab1, tab2, tab3 = st.tabs(["Lista de Usuários", "Novo Usuário", "Logs de Acesso"])
    
    with tab1:
        show_users_list()
    with tab2:
        show_new_user_form()
    with tab3:
        show_access_logs()

def show_admin_activities():
    st.title("📋 Gestão de Atividades")
    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3 = st.tabs(["Todas as Atividades", "Nova Atividade", "Métricas"])
    
    with tab1:
        show_all_activities()
    with tab2:
        show_admin_new_activity()
    with tab3:
        show_activities_metrics()

def show_all_activities():
    st.subheader("Todas as Atividades")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        dept_filter = st.selectbox("Departamento", ["Todos"] + get_departments())
    with col2:
        status_filter = st.selectbox(
            "Status", 
            ["Todos", "Em Andamento", "Concluídas", "Pendentes"]
        )
    with col3:
        user_filter = st.selectbox("Usuário", ["Todos"] + get_all_users_names())
    
    activities = get_filtered_activities(dept_filter, status_filter, user_filter)
    
    for activity in activities:
        with st.expander(f"{activity['activity']} - {activity['status'].title()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Responsável:** {activity['full_name']}")
                st.write(f"**Descrição:** {activity['description']}")
                st.write(f"**Prioridade:** {activity['priority']}")
                st.write(f"**Categoria:** {activity['category']}")
            
            with col2:
                st.write(f"**Início:** {activity['start_time']}")
                st.write(f"**Horas Estimadas:** {activity['estimated_hours']}")
                if activity['status'] == 'concluida':
                    st.write(f"**Horas Reais:** {activity['actual_hours']}")
                st.write(f"**Última Atualização:** {activity['last_updated']}")
            
            # Ações
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ Editar", key=f"edit_act_{activity['id']}"):
                    show_edit_activity_modal(activity)
            with col2:
                if activity['status'] != 'concluida':
                    if st.button("✅ Concluir", key=f"complete_act_{activity['id']}"):
                        complete_activity(activity['id'])
                        st.experimental_rerun()
            with col3:
                if st.button("🗑️ Excluir", key=f"del_act_{activity['id']}"):
                    delete_activity(activity['id'])
                    st.experimental_rerun()

# Função melhorada para mostrar formulário de nova atividade (admin)
def show_admin_new_activity():
    st.subheader("Nova Atividade")
    
    with st.form("new_activity_admin_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            responsible = st.selectbox("Responsável*", get_all_users_names())
            activity = st.text_input("Título da Atividade*")
            description = st.text_area("Descrição*")
            priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
        
        with col2:
            category = st.selectbox("Categoria", ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"])
            estimated_hours = st.number_input("Horas Estimadas", min_value=0.5, value=1.0)
            start_date = st.date_input("Data de Início")
            status = st.selectbox("Status", ["pendente", "em_andamento", "concluida"])
        
        comments = st.text_area("Comentários")
        
        if st.form_submit_button("Criar Atividade"):
            if not activity or not description:
                st.error("Por favor, preencha todos os campos obrigatórios")
                return
                
            user_id = get_user_id_by_name(responsible)
            if not user_id:
                st.error("Usuário responsável não encontrado")
                return
                
            activity_id = create_activity(
                user_id=user_id,
                activity=activity,
                description=description,
                priority=priority,
                category=category,
                estimated_hours=estimated_hours,
                comments=comments,
                start_date=start_date,
                status=status
            )
            
            if activity_id:
                st.success("Atividade criada com sucesso!")
                time.sleep(1)  # Pequena pausa para mostrar a mensagem
                st.experimental_rerun()

def show_activities_metrics():
    st.subheader("📊 Métricas de Atividades")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_metric_card("Total de Atividades", get_total_activities(), "📊")
    with col2:
        show_metric_card("Concluídas Hoje", get_completed_today_count(), "✅")
    with col3:
        show_metric_card("Em Andamento", get_total_ongoing_activities(), "🔄")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_productivity_metrics()
    with col2:
        show_status_distribution()

# Funções auxiliares
def get_all_users_names():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT full_name FROM users WHERE status="active" ORDER BY full_name')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_user_id_by_name(full_name):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE full_name=?', (full_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_filtered_activities(dept_filter, status_filter, user_filter):
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            a.*,
            u.full_name
        FROM activities a
        JOIN users u ON a.user_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if dept_filter != "Todos":
        query += " AND u.department=?"
        params.append(dept_filter)
    
    if status_filter != "Todos":
        query += " AND a.status=?"
        params.append(status_filter.lower().replace(" ", "_"))
    
    if user_filter != "Todos":
        query += " AND u.full_name=?"
        params.append(user_filter)
    
    query += " ORDER BY a.start_time DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df.to_dict('records')

def delete_activity(activity_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('DELETE FROM activities WHERE id=?', (activity_id,))
    conn.commit()
    conn.close()

def show_edit_activity_modal(activity):
    st.subheader(f"✏️ Editar Atividade: {activity['activity']}")
    
    with st.form(f"edit_activity_form_{activity['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_activity = st.text_input("Título", value=activity['activity'])
            description = st.text_area("Descrição", value=activity['description'])
            priority = st.selectbox("Prioridade", 
                                  ["Baixa", "Média", "Alta", "Urgente"],
                                  index=["Baixa", "Média", "Alta", "Urgente"].index(activity['priority']))
        
        with col2:
            category = st.selectbox("Categoria",
                                  ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"],
                                  index=["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"].index(activity['category']))
            status = st.selectbox("Status",
                                ["pendente", "em_andamento", "concluida"],
                                index=["pendente", "em_andamento", "concluida"].index(activity['status']))
            estimated_hours = st.number_input("Horas Estimadas", 
                                           min_value=0.5,
                                           value=float(activity['estimated_hours']))
        
        comments = st.text_area("Comentários", value=activity['comments'])
        
        if st.form_submit_button("Salvar Alterações"):
            update_activity(activity['id'], new_activity, description, priority,
                          category, status, estimated_hours, comments)
            st.success("Atividade atualizada com sucesso!")
            st.experimental_rerun()

def update_activity(activity_id, activity_name, description, priority, category, 
                   status, estimated_hours, comments):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    c.execute('''UPDATE activities 
                 SET activity=?, description=?, priority=?, category=?,
                     status=?, estimated_hours=?, comments=?, last_updated=?
                 WHERE id=?''',
              (activity_name, description, priority, category, status,
               estimated_hours, comments, datetime.now(), activity_id))
    
    conn.commit()
    conn.close()

def get_total_ongoing_activities():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM activities WHERE status='em_andamento'")
    result = c.fetchone()[0]
    conn.close()
    return result

def show_user_management():
    st.subheader("👥 Gerenciamento de Usuários")
    
    # Tabs para diferentes ações
    user_tabs = st.tabs(["Lista de Usuários", "Novo Usuário", "Logs de Acesso"])
    
    with user_tabs[0]:
        show_user_list()
    
    with user_tabs[1]:
        show_new_user_form()
    
    with user_tabs[2]:
        show_access_logs()

def show_user_list():
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        dept_filter = st.selectbox("Departamento", ["Todos"] + get_departments())
    with col2:
        status_filter = st.selectbox("Status", ["Todos", "Ativo", "Inativo"])
    with col3:
        search = st.text_input("Buscar usuário")
    
    # Lista de usuários
    users = get_filtered_users(dept_filter, status_filter, search)
    
    for user in users:
        with st.expander(f"{user['full_name']} ({user['username']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Email:** {user['email']}")
                st.write(f"**Departamento:** {user['department']}")
            
            with col2:
                st.write(f"**Função:** {user['role']}")
                st.write(f"**Status:** {user['status']}")
            
            with col3:
                if st.button("✏️ Editar", key=f"edit_{user['id']}"):
                    show_edit_user_modal(user)
                if st.button("🗑️ Desativar" if user['status'] == 'active' else "✅ Ativar", 
                            key=f"toggle_{user['id']}"):
                    toggle_user_status(user['id'])

def show_new_user_form():
    st.subheader("➕ Cadastrar Novo Usuário")
    
    with st.form("new_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Nome de usuário*")
            password = st.text_input("Senha*", type="password")
            full_name = st.text_input("Nome completo*")
        
        with col2:
            email = st.text_input("Email*")
            department = st.selectbox("Departamento*", get_departments())
            role = st.selectbox("Função*", ["comum", "supervisor", "admin"])
        
        if st.form_submit_button("Cadastrar Usuário"):
            if create_user(username, password, role, full_name, email, department):
                st.success("Usuário cadastrado com sucesso!")
                log_system_action(st.session_state.user['id'], 
                                "create_user", 
                                f"Novo usuário criado: {username}")
            else:
                st.error("Erro ao cadastrar usuário. Verifique se o nome de usuário já existe.")

def create_user(username, password, role, full_name, email, department):
    try:
        conn = sqlite3.connect('team_activities.db')
        c = conn.cursor()
        hashed_password = sha256(password.encode()).hexdigest()
        
        c.execute('''
            INSERT INTO users (username, password, role, full_name, email, department, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, hashed_password, role, full_name, email, department, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def show_department_management():
    st.subheader("🏢 Gerenciamento de Departamentos")
    
    # Novo departamento
    with st.expander("➕ Adicionar Novo Departamento"):
        with st.form("new_dept_form"):
            dept_name = st.text_input("Nome do Departamento")
            dept_desc = st.text_area("Descrição")
            if st.form_submit_button("Adicionar"):
                add_department(dept_name, dept_desc)
    
    # Lista de departamentos
    departments = get_all_departments()
    for dept in departments:
        with st.expander(f"📁 {dept['name']}"):
            st.write(f"**Descrição:** {dept['description']}")
            st.write(f"**Total de Usuários:** {dept['user_count']}")
            st.write(f"**Atividades em Andamento:** {dept['active_tasks']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Editar", key=f"edit_dept_{dept['id']}"):
                    show_edit_department_modal(dept)
            with col2:
                if st.button("🗑️ Excluir", key=f"del_dept_{dept['id']}"):
                    delete_department(dept['id'])
def reset_database():
    """Remove o banco de dados existente para uma nova inicialização"""
    import os
    try:
        if os.path.exists('team_activities.db'):
            os.remove('team_activities.db')
            print("Banco de dados resetado com sucesso!")
            return True
    except Exception as e:
        print(f"Erro ao resetar banco de dados: {e}")
        return False

def show_productivity_metrics():
    """Mostra métricas de produtividade"""
    st.subheader("Métricas de Produtividade")
    
    # Dados de produtividade
    prod_data = get_productivity_data()
    
    # Criar gráfico
    fig = px.line(prod_data, 
                  x='date', 
                  y='tasks_completed',
                  title='Atividades Concluídas por Dia')
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Atividades Concluídas",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def get_user_info(user_id):
    """Obtém informações detalhadas do usuário"""
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    try:
        c.execute('''
            SELECT 
                username,
                full_name,
                email,
                department,
                role,
                last_login,
                created_at,
                status
            FROM users 
            WHERE id = ?
        ''', (user_id,))
        
        result = c.fetchone()
        if result:
            return {
                'username': result[0],
                'full_name': result[1] or 'Não informado',
                'email': result[2] or 'Não informado',
                'department': result[3] or 'Não informado',
                'role': result[4],
                'last_login': result[5],
                'created_at': result[6],
                'status': result[7]
            }
        return None
    finally:
        conn.close()
# Função principal
def main():
    # Configuração inicial
    configure_page()
    # Verifica e inicializa o banco de dados
    if not check_database():
        st.error("Erro no banco de dados. Recriando...")
        reset_database()
    init_db()
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Verificação de sessão
    if st.session_state.user is None:
        show_login_page()
    else:
        # Atualizar último acesso
        update_last_login(st.session_state.user['id'])
        
        # Mostrar interface apropriada
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
# Funções de autenticação e usuário
def login_user(username, password):
    """Função de login com tratamento de erros melhorado"""
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    try:
        hashed_password = sha256(password.encode()).hexdigest()
        
        # Primeiro verifica se o usuário existe
        c.execute('SELECT id, role, status FROM users WHERE username=?', (username,))
        user_data = c.fetchone()
        
        if not user_data:
            return None
            
        user_id, role, status = user_data
        
        # Verifica senha e status
        c.execute('SELECT id FROM users WHERE username=? AND password=?',
                 (username, hashed_password))
        
        if c.fetchone() and status == 'active':
            return {'id': user_id, 'role': role}
        return None
        
    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        return None
    finally:
        conn.close()

def update_last_login(user_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('UPDATE users SET last_login=? WHERE id=?', (datetime.now(), user_id))
    conn.commit()
    conn.close()

def get_filtered_users(dept_filter, status_filter, search):
    conn = sqlite3.connect('team_activities.db')
    query = '''SELECT id, username, full_name, email, department, role, status 
               FROM users WHERE 1=1'''
    params = []
    
    if dept_filter != "Todos":
        query += " AND department=?"
        params.append(dept_filter)
    
    if status_filter != "Todos":
        query += " AND status=?"
        params.append(status_filter.lower())
    
    if search:
        query += " AND (username LIKE ? OR full_name LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df.to_dict('records')

def toggle_user_status(user_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('UPDATE users SET status = CASE WHEN status="active" THEN "inactive" ELSE "active" END WHERE id=?', 
              (user_id,))
    conn.commit()
    conn.close()

# Funções de departamento
def get_all_departments():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    # Busca departamentos com contagem de usuários e atividades
    query = '''
        SELECT 
            d.id,
            d.name,
            d.description,
            COUNT(DISTINCT u.id) as user_count,
            COUNT(DISTINCT CASE WHEN a.status='em_andamento' THEN a.id END) as active_tasks
        FROM departments d
        LEFT JOIN users u ON u.department = d.name
        LEFT JOIN activities a ON a.user_id = u.id
        GROUP BY d.id, d.name, d.description
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.to_dict('records')

def add_department(name, description):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO departments (name, description) VALUES (?, ?)',
                 (name, description))
        conn.commit()
        st.success(f"Departamento {name} criado com sucesso!")
    except sqlite3.IntegrityError:
        st.error("Departamento já existe!")
    finally:
        conn.close()

def delete_department(dept_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    # Verificar se há usuários no departamento
    c.execute('''SELECT COUNT(*) FROM users 
                 WHERE department=(SELECT name FROM departments WHERE id=?)''',
              (dept_id,))
    
    if c.fetchone()[0] > 0:
        st.error("Não é possível excluir departamento com usuários!")
        return
    
    c.execute('DELETE FROM departments WHERE id=?', (dept_id,))
    conn.commit()
    conn.close()
    st.success("Departamento excluído com sucesso!")

# Funções de métricas e estatísticas
def get_total_activities():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM activities')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_activities_today():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    today = datetime.now().date()
    c.execute('SELECT COUNT(*) FROM activities WHERE DATE(start_time)=?',
              (today,))
    result = c.fetchone()[0]
    conn.close()
    return result

def get_completion_rate():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT 
                 CAST(SUM(CASE WHEN status='concluida' THEN 1 ELSE 0 END) AS FLOAT) / 
                 COUNT(*) * 100 
                 FROM activities''')
    result = c.fetchone()[0] or 0
    conn.close()
    return result

def get_active_users_count():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(DISTINCT user_id) FROM activities 
                 WHERE DATE(start_time)=DATE('now') 
                 AND status='em_andamento' ''')
    result = c.fetchone()[0]
    conn.close()
    return result

# Funções de visualização de dados
def get_activities_timeline_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            a.activity,
            a.start_time,
            COALESCE(a.end_time, datetime('now')) as end_time,
            a.status,
            u.full_name as user
        FROM activities a
        JOIN users u ON a.user_id = u.id
        WHERE a.start_time >= datetime('now', '-30 days')
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_department_performance_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            u.department,
            COUNT(CASE WHEN a.status='concluida' THEN 1 END) * 100.0 / COUNT(*) as completion_rate
        FROM activities a
        JOIN users u ON a.user_id = u.id
        GROUP BY u.department
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_productivity_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            DATE(start_time) as date,
            COUNT(*) as tasks_completed
        FROM activities
        WHERE status='concluida'
        AND start_time >= datetime('now', '-30 days')
        GROUP BY DATE(start_time)
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_status_distribution_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            status,
            COUNT(*) as count
        FROM activities
        GROUP BY status
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
# Funções para atividades do usuário
def show_new_activity_form(user_id):
    st.subheader("➕ Nova Atividade")
    
    with st.form("new_activity_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            activity = st.text_input("Título da Atividade*")
            description = st.text_area("Descrição")
            priority = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Urgente"])
        
        with col2:
            category = st.selectbox("Categoria", ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"])
            estimated_hours = st.number_input("Horas Estimadas", min_value=0.5, value=1.0)
            comments = st.text_area("Comentários")
        
        if st.form_submit_button("Iniciar Atividade"):
            create_activity(user_id, activity, description, priority, category, estimated_hours, comments)
            st.success("Atividade criada com sucesso!")
            st.experimental_rerun()

def create_activity(user_id, activity, description, priority, category, estimated_hours, comments):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO activities 
                 (user_id, activity, description, status, priority, category, 
                  start_time, estimated_hours, comments, last_updated)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, activity, description, 'em_andamento', priority, category,
               datetime.now(), estimated_hours, comments, datetime.now()))
    
    conn.commit()
    conn.close()
    
    log_system_action(user_id, "create_activity", f"Nova atividade criada: {activity}")

def show_user_activities(user_id):
    st.subheader("📋 Minhas Atividades")
    
    # Filtros
    status_filter = st.selectbox("Filtrar por Status", 
                               ["Todas", "Em Andamento", "Concluídas", "Pendentes"])
    
    # Buscar atividades
    activities = get_user_active_activities(user_id, status_filter)
    
    # Exibir atividades
    for activity in activities:
        with st.expander(f"{activity['activity']} - {activity['status'].title()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Descrição:** {activity['description']}")
                st.write(f"**Prioridade:** {activity['priority']}")
                st.write(f"**Categoria:** {activity['category']}")
            
            with col2:
                st.write(f"**Início:** {activity['start_time']}")
                st.write(f"**Horas Estimadas:** {activity['estimated_hours']}")
                if activity['status'] == 'concluida':
                    st.write(f"**Horas Reais:** {activity['actual_hours']}")
            
            # Ações
            if activity['status'] != 'concluida':
                if st.button("✅ Concluir", key=f"complete_{activity['id']}"):
                    complete_activity(activity['id'])
                    st.experimental_rerun()
def show_users_list():
    st.subheader("Lista de Usuários")

    # Get users and display in a data frame
    users = get_filtered_users(dept_filter="Todos", status_filter="Todos", search="")
    if users:
        st.table(pd.DataFrame(users))
    else:
        st.write("No users found.")



def complete_activity(activity_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    # Atualizar status e registrar tempo real
    end_time = datetime.now()
    c.execute('''UPDATE activities 
                 SET status='concluida', 
                     end_time=?, 
                     actual_hours=ROUND(
                         (JULIANDAY(?) - JULIANDAY(start_time)) * 24, 2),
                     last_updated=?
                 WHERE id=?''', 
              (end_time, end_time, end_time, activity_id))
    
    conn.commit()
    conn.close()

def show_user_dashboard(user_id):
    st.subheader("📊 Meu Dashboard")
    
    # Métricas pessoais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_metric_card("Atividades Hoje", get_user_activities_today(user_id), "📅")
    with col2:
        show_metric_card("Em Andamento", get_user_active_activities(user_id), "🔄")
    with col3:
        show_metric_card("Taxa de Conclusão", f"{get_user_completion_rate(user_id):.1f}%", "✅")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        show_user_productivity_chart(user_id)
    with col2:
        show_user_status_distribution(user_id)

def show_user_productivity_chart(user_id):
    st.subheader("Produtividade")
    df = get_user_productivity_data(user_id)
    fig = px.line(df, x='date', y='completed',
                  title='Atividades Concluídas por Dia')
    st.plotly_chart(fig)

def show_user_status_distribution(user_id):
    st.subheader("Status das Atividades")
    df = get_user_status_distribution(user_id)
    fig = px.pie(df, values='count', names='status',
                 title='Distribuição por Status')
    st.plotly_chart(fig)
def show_user_interface():
    st.title("📋 Minhas Atividades")
    user_id = st.session_state.user['id']
    
    # Quick Actions: Add New Activity or View Dashboard
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nova Atividade"):
            show_new_activity_form(user_id)
    with col2:
        if st.button("📊 Meu Dashboard"):
            show_user_dashboard(user_id)
    
    # Display User's Activities
    show_user_activities(user_id)
def show_realtime_activities():
    st.subheader("🔄 Atividades em Tempo Real")
    
    # Buscar atividades em andamento
    activities = get_realtime_activities()
    
    # Exibir em cards
    for activity in activities:
        time_running = datetime.now() - datetime.strptime(activity['start_time'], 
                                                        '%Y-%m-%d %H:%M:%S')
        hours_running = time_running.total_seconds() / 3600
        
        with st.container():
            st.markdown(f"""
                <div class="status-card">
                    <h3>{activity['activity']}</h3>
                    <p><strong>Responsável:</strong> {activity['full_name']}</p>
                    <p><strong>Tempo Decorrido:</strong> {hours_running:.1f} horas</p>
                    <p><strong>Prioridade:</strong> {activity['priority']}</p>
                </div>
            """, unsafe_allow_html=True)

def show_team_performance():
    st.subheader("📈 Performance da Equipe")
    df = get_team_performance_data()
    fig = px.bar(df, x='user', y='completion_rate',
                 title='Taxa de Conclusão por Membro')
    st.plotly_chart(fig)

def show_team_workload():
    st.subheader("⚖️ Distribuição de Carga")
    df = get_team_workload_data()
    fig = px.pie(df, values='activities', names='user',
                 title='Distribuição de Atividades')
    st.plotly_chart(fig)

# Funções auxiliares de dados
def get_user_activities_today(user_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM activities 
                 WHERE user_id=? AND DATE(start_time)=DATE('now')''',
              (user_id,))
    result = c.fetchone()[0]
    conn.close()
    return result

def get_user_active_activities(user_id, status_filter="Todas"):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    query = '''SELECT * FROM activities WHERE user_id=?'''
    params = [user_id]
    
    # Aplicar o filtro de status, se necessário
    if status_filter != "Todas":
        query += " AND status=?"
        params.append(status_filter.lower().replace(" ", "_"))
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df.to_dict('records')

def show_user_activities(user_id):
    st.subheader("📋 Minhas Atividades")

    # Filter Options for Status
    status_filter = st.selectbox("Filtrar por Status", ["Todas", "Em Andamento", "Concluídas", "Pendentes"])
    
    # Fetch and Display Activities
    activities = get_user_active_activities(user_id, status_filter)
    for activity in activities:
        with st.expander(f"{activity['activity']} - {activity['status'].title()}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Descrição:** {activity['description']}")
                st.write(f"**Prioridade:** {activity['priority']}")
                st.write(f"**Categoria:** {activity['category']}")
                st.write(f"**Comentários:** {activity['comments']}")
            
            with col2:
                st.write(f"**Início:** {activity['start_time']}")
                st.write(f"**Horas Estimadas:** {activity['estimated_hours']}")
                if activity['status'] == 'concluida':
                    st.write(f"**Horas Reais:** {activity['actual_hours']}")
                st.write(f"**Última Atualização:** {activity['last_updated']}")
            
            # Action Buttons for Editing or Completing Activity
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Editar", key=f"edit_act_{activity['id']}"):
                    show_user_edit_activity_modal(activity)
            with col2:
                if activity['status'] != 'concluida':
                    if st.button("✅ Concluir", key=f"complete_act_{activity['id']}"):
                        complete_activity(activity['id'])
                        st.experimental_rerun()
def show_user_edit_activity_modal(activity):
    """Displays a modal for the user to edit their activity."""
    st.subheader(f"✏️ Editar Atividade: {activity['activity']}")
    
    with st.form(f"edit_activity_form_{activity['id']}"):
        col1, col2 = st.columns(2)

        with col1:
            new_activity = st.text_input("Título", value=activity['activity'])
            description = st.text_area("Descrição", value=activity['description'])
            priority = st.selectbox(
                "Prioridade", 
                ["Baixa", "Média", "Alta", "Urgente"], 
                index=["Baixa", "Média", "Alta", "Urgente"].index(activity['priority'])
            )
        
        with col2:
            category = st.selectbox(
                "Categoria",
                ["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"],
                index=["Desenvolvimento", "Manutenção", "Suporte", "Reunião", "Outro"].index(activity['category'])
            )
            estimated_hours = st.number_input("Horas Estimadas", min_value=0.5, value=float(activity['estimated_hours']))
        
        comments = st.text_area("Comentários", value=activity['comments'])
        
        if st.form_submit_button("Salvar Alterações"):
            update_activity(
                activity['id'], new_activity, description, priority,
                category, activity['status'], estimated_hours, comments
            )
            st.success("Atividade atualizada com sucesso!")
            st.experimental_rerun()
def get_user_completion_rate(user_id):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT 
                 CAST(SUM(CASE WHEN status='concluida' THEN 1 ELSE 0 END) AS FLOAT) / 
                 COUNT(*) * 100 
                 FROM activities
                 WHERE user_id=?''',
              (user_id,))
    result = c.fetchone()[0] or 0
    conn.close()
    return result

def get_user_productivity_data(user_id):
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            DATE(start_time) as date,
            COUNT(*) as completed
        FROM activities
        WHERE user_id=? AND status='concluida'
        AND start_time >= datetime('now', '-30 days')
        GROUP BY DATE(start_time)
    '''
    df = pd.read_sql_query(query, conn, params=[user_id])
    conn.close()
    return df

def get_user_status_distribution(user_id):
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT status, COUNT(*) as count
        FROM activities
        WHERE user_id=?
        GROUP BY status
    '''
    df = pd.read_sql_query(query, conn, params=[user_id])
    conn.close()
    return df

def get_realtime_activities():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            a.*,
            u.full_name
        FROM activities a
        JOIN users u ON a.user_id = u.id
        WHERE a.status = 'em_andamento'
        ORDER BY a.start_time DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.to_dict('records')

def get_team_performance_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            u.full_name as user,
            COUNT(CASE WHEN a.status='concluida' THEN 1 END) * 100.0 / COUNT(*) as completion_rate
        FROM users u
        LEFT JOIN activities a ON u.id = a.user_id
        GROUP BY u.id, u.full_name
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_team_workload_data():
    conn = sqlite3.connect('team_activities.db')
    query = '''
        SELECT 
            u.full_name as user,
            COUNT(a.id) as activities
        FROM users u
        LEFT JOIN activities a ON u.id = a.user_id
        WHERE a.status = 'em_andamento'
        GROUP BY u.id, u.full_name
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
# Funções de interface do usuário
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
    df = get_activities_timeline_data()
    fig = px.timeline(df, x_start='start_time', x_end='end_time',
                     y='activity', color='status', hover_data=['user'])
    st.plotly_chart(fig)

def show_department_performance():
    st.subheader("Performance por Departamento")
    df = get_department_performance_data()
    fig = px.bar(df, x='department', y='completion_rate',
                 title='Taxa de Conclusão por Departamento')
    st.plotly_chart(fig)

def show_productivity_metrics():
    st.subheader("Métricas de Produtividade")
    df = get_productivity_data()
    fig = px.line(df, x='date', y='tasks_completed',
                  title='Atividades Concluídas por Dia')
    st.plotly_chart(fig)

def show_status_distribution():
    st.subheader("Distribuição de Status")
    df = get_status_distribution_data()
    fig = px.pie(df, values='count', names='status',
                 title='Distribuição de Status das Atividades')
    st.plotly_chart(fig)

def show_reports():
    st.subheader("📊 Relatórios")
    report_type = st.selectbox("Tipo de Relatório", [
        "Atividades por Período",
        "Performance por Usuário",
        "Análise de Departamentos",
        "Tempo Médio de Conclusão"
    ])
    
    # Implementar geração de relatórios específicos aqui
    st.info("Funcionalidade de relatórios em desenvolvimento")

def show_settings():
    st.subheader("⚙️ Configurações do Sistema")
    
    with st.expander("🔒 Segurança"):
        st.checkbox("Ativar autenticação em dois fatores")
        st.number_input("Tempo de expiração da sessão (minutos)", min_value=5)
    
    with st.expander("📧 Notificações"):
        st.checkbox("Enviar e-mail para atividades atrasadas")
        st.checkbox("Notificar supervisor sobre novas atividades")
    
    with st.expander("🎨 Personalização"):
        st.color_picker("Cor principal", "#4CAF50")
        st.selectbox("Tema", ["Claro", "Escuro", "Sistema"])
# Funções de Modal
def show_edit_user_modal(user):
    st.subheader(f"✏️ Editar Usuário: {user['username']}")
    
    with st.form(f"edit_user_form_{user['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Nome completo", value=user['full_name'])
            email = st.text_input("Email", value=user['email'])
        
        with col2:
            department = st.selectbox("Departamento", get_departments(), 
                                    index=get_departments().index(user['department']))
            role = st.selectbox("Função", ["comum", "supervisor", "admin"],
                              index=["comum", "supervisor", "admin"].index(user['role']))
        
        new_password = st.text_input("Nova senha (deixe em branco para manter a atual)", type="password")
        
        if st.form_submit_button("Salvar Alterações"):
            update_user(user['id'], full_name, email, department, role, new_password)
            st.success("Usuário atualizado com sucesso!")
            st.experimental_rerun()

def show_edit_department_modal(dept):
    st.subheader(f"✏️ Editar Departamento: {dept['name']}")
    
    with st.form(f"edit_dept_form_{dept['id']}"):
        name = st.text_input("Nome do Departamento", value=dept['name'])
        description = st.text_area("Descrição", value=dept['description'])
        
        if st.form_submit_button("Salvar Alterações"):
            update_department(dept['id'], name, description)
            st.success("Departamento atualizado com sucesso!")
            st.experimental_rerun()

# Funções de Interface
def show_user_profile():
    st.sidebar.title("Perfil do Usuário")
    user_info = get_user_info(st.session_state.user['id'])
    
    # Avatar placeholder
    st.sidebar.image("https://via.placeholder.com/150", width=150)
    
    st.sidebar.write(f"**Nome:** {user_info['full_name']}")
    st.sidebar.write(f"**Email:** {user_info['email']}")
    st.sidebar.write(f"**Departamento:** {user_info['department']}")
    st.sidebar.write(f"**Função:** {user_info['role'].title()}")
    
    st.sidebar.divider()
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.experimental_rerun()

def show_supervisor_interface():
    st.title("👥 Dashboard de Supervisão")
    
    # Métricas do supervisor
    col1, col2, col3 = st.columns(3)
    with col1:
        show_metric_card("Equipe Ativa", get_team_active_count(), "👥")
    with col2:
        show_metric_card("Atividades Pendentes", get_pending_activities_count(), "⏳")
    with col3:
        show_metric_card("Conclusões Hoje", get_completed_today_count(), "✅")
    
    # Monitoramento em tempo real
    st.subheader("🔄 Atividades em Tempo Real")
    show_realtime_activities()
    
    # Dashboard da equipe
    col1, col2 = st.columns(2)
    with col1:
        show_team_performance()
    with col2:
        show_team_workload()

def show_user_interface():
    st.title("📋 Minhas Atividades")
    user_id = st.session_state.user['id']
    
    # Ações rápidas
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nova Atividade"):
            show_new_activity_form(user_id)
    with col2:
        if st.button("📊 Meu Dashboard"):
            show_user_dashboard(user_id)
    
    # Lista de atividades do usuário
    show_user_activities(user_id)

def show_access_logs():
    st.subheader("📋 Logs de Acesso")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data Inicial")
    with col2:
        end_date = st.date_input("Data Final")
    
    # Buscar logs
    logs = get_access_logs(start_date, end_date)
    
    # Exibir logs em uma tabela
    if logs:
        st.dataframe(
            pd.DataFrame(logs, 
                        columns=['Usuário', 'Ação', 'Data/Hora'])
        )
    else:
        st.info("Nenhum log encontrado para o período selecionado.")

# Funções Auxiliares
def get_departments():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('SELECT name FROM departments ORDER BY name')
    departments = [row[0] for row in c.fetchall()]
    conn.close()
    return departments
# 1. Adicione a função get_user_info
def get_user_info(user_id):
    """Obtém informações do usuário pelo ID"""
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT username, full_name, email, department, role 
                     FROM users WHERE id = ?''', (user_id,))
        result = c.fetchone()
        
        if result:
            return {
                'username': result[0],
                'full_name': result[1] or 'Não informado',
                'email': result[2] or 'Não informado',
                'department': result[3] or 'Não informado',
                'role': result[4]
            }
        return None
    finally:
        conn.close()

def update_user(user_id, full_name, email, department, role, new_password=None):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    
    if new_password:
        hashed_password = sha256(new_password.encode()).hexdigest()
        c.execute('''UPDATE users 
                     SET full_name=?, email=?, department=?, role=?, password=?
                     WHERE id=?''', 
                 (full_name, email, department, role, hashed_password, user_id))
    else:
        c.execute('''UPDATE users 
                     SET full_name=?, email=?, department=?, role=?
                     WHERE id=?''', 
                 (full_name, email, department, role, user_id))
    
    conn.commit()
    conn.close()

def update_department(dept_id, name, description):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('UPDATE departments SET name=?, description=? WHERE id=?',
              (name, description, dept_id))
    conn.commit()
    conn.close()

def get_team_active_count():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(DISTINCT user_id) FROM activities 
                 WHERE status='em_andamento' AND DATE(start_time)=DATE('now')''')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_pending_activities_count():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM activities WHERE status='pendente'")
    result = c.fetchone()[0]
    conn.close()
    return result

def get_completed_today_count():
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM activities 
                 WHERE status='concluida' AND DATE(end_time)=DATE('now')''')
    result = c.fetchone()[0]
    conn.close()
    return result

def get_access_logs(start_date, end_date):
    conn = sqlite3.connect('team_activities.db')
    c = conn.cursor()
    c.execute('''SELECT u.username, l.action, l.timestamp
                 FROM system_logs l
                 JOIN users u ON l.user_id = u.id
                 WHERE DATE(l.timestamp) BETWEEN ? AND ?
                 ORDER BY l.timestamp DESC''',
              (start_date, end_date))
    logs = c.fetchall()
    conn.close()
    return logs
if __name__ == "__main__":
    main()


