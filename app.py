import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Kanban", page_icon="📊", layout="wide")

# --- Conexão Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- Funções Auxiliares ---

def get_members():
    response = supabase.table("members").select("*").order("name").execute()
    return pd.DataFrame(response.data)

def get_projects():
    response = supabase.table("projects").select("*").order("created_at").execute()
    return pd.DataFrame(response.data)

def get_tasks(project_id):
    response = supabase.table("tasks").select("*").eq("project_id", project_id).order("end_date").execute()
    return pd.DataFrame(response.data)

def update_full_task(task_id, title, desc, owner, start_d, end_d, progress):
    # Lógica de Status Automático baseada no progresso
    status = "Em Andamento"
    if progress == 100: status = "Concluído"
    elif progress == 0: status = "Não Iniciado"
    
    data = {
        "title": title,
        "description": desc,
        "owner_name": owner,
        "start_date": str(start_d),
        "end_date": str(end_d),
        "progress": progress,
        "status": status
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

# --- Interface Principal ---

# 1. Header e Identidade
col_logo, col_user = st.columns([3, 1])
with col_logo:
    st.title("📊 Gestão Visual de Projetos")

with col_user:
    members_df = get_members()
    member_names = ["Visitante"] + members_df["name"].tolist() if not members_df.empty else ["Visitante"]
    
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = "Visitante"
        
    selected_user = st.selectbox("Usuário Ativo", member_names, index=0)
    st.session_state["current_user"] = selected_user

st.divider()

# 2. Seleção de Projeto
projects_df = get_projects()

if projects_df.empty:
    st.warning("Nenhum projeto encontrado. Crie um novo no rodapé.")
    selected_project_name = None
else:
    col_sel, col_tv = st.columns([3, 1])
    with col_sel:
        project_names = projects_df["name"].tolist()
        selected_project_name = st.selectbox("📂 Selecione o Projeto", project_names)
        project_data = projects_df[projects_df["name"] == selected_project_name].iloc[0]
        project_id = int(project_data["id"])
        project_pin = project_data["pin_code"]
    
    with col_tv:
        # Modo TV
        if st.toggle("📺 Auto-Refresh (TV)"):
            time.sleep(30)
            st.rerun()

# 3. Lógica do Dashboard
if selected_project_name:
    tasks_df = get_tasks(project_id)
    
    # --- MÉTRICAS DE TOPO (DASHBOARD) ---
    if not tasks_df.empty:
        # Conversão de datas
        tasks_df['end_date'] = pd.to_datetime(tasks_df['end_date'], errors='coerce')
        
        # Cálculos
        total_tasks = len(tasks_df)
        completed_tasks = len(tasks_df[tasks_df['progress'] == 100])
        perc_conclusao = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Previsão de Término (Maior data final entre as tarefas)
        max_date = tasks_df['end_date'].max()
        forecast_str = max_date.strftime("%d/%m/%Y") if pd.notnull(max_date) else "Indefinido"
        
        # Exibição Visual
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Atividades", total_tasks)
        m2.metric("Concluído", f"{completed_tasks} ({int(perc_conclusao)}%)")
        m3.metric("Previsão Término Projeto", forecast_str, help="Baseado na data final da última tarefa")
        
        # Barra de progresso geral
        st.progress(int(tasks_df['progress'].mean()), text="Progresso Médio Geral")
        
    else:
        st.info("Projeto sem atividades cadastradas.")

    st.markdown("---")

    # --- KANBAN BOARD ---
    c_todo, c_doing, c_done = st.columns(3)
    cols = {"Não Iniciado": c_todo, "Em Andamento": c_doing, "Concluído": c_done}
    
    # Cabeçalhos
    c_todo.markdown("### 📝 A Fazer")
    c_doing.markdown("### 🔨 Em Execução")
    c_done.markdown("### ✅ Concluído")

    if not tasks_df.empty:
        # Ordena para mostrar tarefas mais urgentes primeiro
        tasks_df = tasks_df.sort_values(by="end_date", ascending=True)

        for index, task in tasks_df.iterrows():
            status = task["status"]
            if status not in cols: status = "Não Iniciado"
            
            with cols[status]:
                container = st.container(border=True)
                with container:
                    # Título e Responsável
                    st.markdown(f"**{task['title']}**")
                    st.caption(f"👤 {task['owner_name']}")
                    
                    # Data e Alerta
                    d_end_str = "S/ Data"
                    if pd.notnull(task["end_date"]):
                        d_end = task["end_date"].date()
                        d_end_str = d_end.strftime('%d/%m')
                        today = date.today()
                        
                        # Lógica visual de prazo
                        if d_end < today and task["progress"] < 100:
                            st.markdown(f"🔴 **Prazo: {d_end_str}**")
                        elif d_end == today and task["progress"] < 100:
                            st.markdown(f"🟠 **Prazo: Hoje**")
                        else:
                            st.markdown(f"📅 Prazo: {d_end_str}")

                    # Barra de progresso mini
                    st.progress(task["progress"])
                    
                    # --- POPOVER DE EDIÇÃO ---
                    # Botão para abrir o modal de edição
                    popover = st.popover("✏️ Editar / Detalhes", use_container_width=True)
                    
                    with popover:
                        st.markdown(f"### Editando: {task['title']}")
                        with st.form(key=f"form_edit_{task['id']}"):
                            ed_title = st.text_input("Título", value=task["title"])
                            ed_desc = st.text_area("Descrição", value=task["description"] if task["description"] else "")
                            
                            c_ed1, c_ed2 = st.columns(2)
                            
                            # Tenta converter strings de data para objeto date
                            try:
                                val_start = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
                            except: val_start = date.today()
                            
                            try:
                                val_end = task["end_date"].date() # Já convertemos pandas timestamp lá em cima
                            except: val_end = date.today()

                            ed_start = c_ed1.date_input("Início", value=val_start)
                            ed_end = c_ed2.date_input("Fim", value=val_end)
                            
                            # Selectbox com index correto
                            try:
                                owner_idx = member_names.index(task["owner_name"])
                            except: owner_idx = 0
                            ed_owner = st.selectbox("Responsável", member_names, index=owner_idx)
                            
                            ed_progress = st.slider("Progresso %", 0, 100, int(task["progress"]))
                            
                            if st.form_submit_button("💾 Salvar Alterações"):
                                update_full_task(task['id'], ed_title, ed_desc, ed_owner, ed_start, ed_end, ed_progress)
                                st.success("Atualizado!")
                                time.sleep(0.5)
                                st.rerun()

# --- ÁREA DE CRIAÇÃO E CONFIGURAÇÃO (RODAPÉ) ---
st.divider()
st.subheader("🛠️ Ferramentas")

tab1, tab2, tab3 = st.tabs(["➕ Nova Atividade", "⚙️ Editar Projeto (Admin)", "🆕 Novo Projeto"])

# ABA 1: NOVA TAREFA
with tab1:
    if selected_project_name:
        with st.form("new_task_form"):
            col_t1, col_t2 = st.columns([2, 1])
            nt_title = col_t1.text_input("Título da Atividade")
            nt_owner = col_t2.selectbox("Responsável", member_names, index=member_names.index(st.session_state["current_user"]) if st.session_state["current_user"] in member_names else 0)
            
            nt_desc = st.text_area("Descrição")
            
            c_d1, c_d2 = st.columns(2)
            nt_start = c_d1.date_input("Data Início", date.today())
            nt_end = c_d2.date_input("Data Prazo", date.today())
            
            if st.form_submit_button("Adicionar Tarefa"):
                data = {
                    "project_id": project_id,
                    "title": nt_title,
                    "description": nt_desc,
                    "start_date": str(nt_start),
                    "end_date": str(nt_end),
                    "owner_name": nt_owner,
                    "status": "Não Iniciado",
                    "progress": 0
                }
                supabase.table("tasks").insert(data).execute()
                st.success("Tarefa criada!")
                st.rerun()
    else:
        st.info("Selecione um projeto para criar tarefas.")

# ABA 2: EDITAR PROJETO (COM SENHA)
with tab2:
    if selected_project_name:
        st.markdown(f"**Editando configurações de: {selected_project_name}**")
        with st.form("edit_project_form"):
            new_proj_name = st.text_input("Nome do Projeto", value=project_data["name"])
            new_proj_desc = st.text_area("Descrição do Projeto", value=project_data["description"])
            
            auth_pin = st.text_input("🔒 Digite o PIN do Projeto para salvar alterações:", type="password")
            
            if st.form_submit_button("Atualizar Dados do Projeto"):
                if auth_pin == project_pin:
                    supabase.table("projects").update({
                        "name": new_proj_name,
                        "description": new_proj_desc
                    }).eq("id", project_id).execute()
                    st.success("Dados do projeto atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("PIN Incorreto! Alteração negada.")
    else:
        st.warning("Selecione um projeto.")

# ABA 3: NOVO PROJETO
with tab3:
    with st.form("create_proj_form"):
        cp_name = st.text_input("Nome do Novo Projeto")
        cp_desc = st.text_area("Descrição")
        cp_pin = st.text_input("Crie uma Senha (PIN) para este projeto:", max_chars=4, type="password")
        st.caption("Guarde este PIN. Ele será necessário para alterar dados do projeto no futuro.")
        
        if st.form_submit_button("Criar Projeto"):
            if cp_name and cp_pin:
                supabase.table("projects").insert({
                    "name": cp_name, 
                    "description": cp_desc,
                    "pin_code": cp_pin
                }).execute()
                st.success(f"Projeto {cp_name} criado!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nome e PIN são obrigatórios.")
