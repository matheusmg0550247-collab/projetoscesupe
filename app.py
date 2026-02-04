import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Kanban Setor", page_icon="📋", layout="wide")

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

def update_task_status(task_id, new_progress, new_status=None):
    # Lógica Automática: Se 100%, vira Concluído. Se > 0 e < 100, vira Em Andamento
    final_status = new_status
    if new_progress == 100:
        final_status = "Concluído"
    elif new_progress > 0 and new_progress < 100:
        final_status = "Em Andamento"
    elif new_progress == 0:
        final_status = "Não Iniciado"
        
    data = {"progress": new_progress, "status": final_status}
    supabase.table("tasks").update(data).eq("id", task_id).execute()
    return final_status

# --- Interface Principal ---

# 1. Header e Identidade
col_logo, col_user = st.columns([3, 1])
with col_logo:
    st.title("🚀 Kanban Operacional")

with col_user:
    # Seleção de Personagem (Sem Login)
    members_df = get_members()
    member_names = ["Visitante"] + members_df["name"].tolist()
    
    # Tenta recuperar do session state ou define padrão
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = "Visitante"
        
    selected_user = st.selectbox("Quem é você?", member_names, index=0)
    st.session_state["current_user"] = selected_user

st.divider()

# 2. Seleção de Projeto e Modo TV
projects_df = get_projects()

if projects_df.empty:
    st.warning("Nenhum projeto encontrado. Crie um abaixo.")
else:
    col_proj, col_actions = st.columns([3, 1])
    
    with col_proj:
        project_names = projects_df["name"].tolist()
        selected_project_name = st.selectbox("📂 Selecione o Projeto", project_names)
        project_data = projects_df[projects_df["name"] == selected_project_name].iloc[0]
        project_id = project_data["id"]
        project_pin = project_data["pin_code"]

    with col_actions:
        auto_refresh = st.toggle("📺 Modo TV (Auto-Refresh)", value=False)
        if auto_refresh:
            time.sleep(30) # Atualiza a cada 30s
            st.rerun()

    # 3. Dashboard do Projeto
    if selected_project_name:
        tasks_df = get_tasks(project_id)
        
        # Cálculo de Progresso Geral
        if not tasks_df.empty:
            avg_progress = tasks_df["progress"].mean()
            total_tasks = len(tasks_df)
            delayed_tasks = 0
            
            # Identificar atrasos
            today = date.today()
            for _, row in tasks_df.iterrows():
                if row["end_date"]:
                    end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
                    if end_date < today and row["progress"] < 100:
                        delayed_tasks += 1
            
            # Métricas Visuais
            m1, m2, m3 = st.columns(3)
            m1.metric("Progresso Total", f"{avg_progress:.1f}%")
            m2.metric("Total Atividades", total_tasks)
            m3.metric("Atrasadas ⚠️", delayed_tasks, delta_color="inverse")
            
            st.progress(int(avg_progress))
        else:
            st.info("Este projeto ainda não tem tarefas.")

        st.subheader(f"Quadro: {selected_project_name}")

        # 4. KANBAN BOARD
        c_todo, c_doing, c_done = st.columns(3)
        
        # Mapeamento de colunas
        cols = {
            "Não Iniciado": c_todo,
            "Em Andamento": c_doing,
            "Concluído": c_done
        }
        
        # Cabeçalhos Coloridos
        c_todo.info("📝 A Fazer")
        c_doing.warning("🔨 Em Andamento")
        c_done.success("✅ Concluído")

        if not tasks_df.empty:
            for index, task in tasks_df.iterrows():
                status = task["status"]
                if status not in cols: status = "Não Iniciado" # Fallback
                
                with cols[status]:
                    # Design do Cartão
                    with st.container(border=True):
                        # Cabeçalho do Cartão
                        st.markdown(f"**{task['title']}**")
                        
                        # Quem está fazendo
                        st.caption(f"👤 {task['owner_name']}")
                        
                        # Prazo com alerta visual
                        if task["end_date"]:
                            d_end = datetime.strptime(task["end_date"], "%Y-%m-%d").date()
                            if d_end < date.today() and task["progress"] < 100:
                                st.markdown(f"🔴 **:red[{d_end.strftime('%d/%m')}]**")
                            else:
                                st.markdown(f"📅 {d_end.strftime('%d/%m')}")
                        
                        # Slider de Progresso (Interativo)
                        new_prog = st.slider(f"%", 0, 100, int(task["progress"]), key=f"slider_{task['id']}")
                        
                        # Botão de Salvar Alteração Rápida
                        if new_prog != task["progress"]:
                            new_status = update_task_status(task["id"], new_prog)
                            st.toast(f"Tarefa atualizada para {new_status}!")
                            time.sleep(1)
                            st.rerun()

                        # Detalhes (Expander)
                        with st.expander("Detalhes"):
                            st.write(task["description"] if task["description"] else "Sem descrição")
                            if st.button("🗑️", key=f"del_{task['id']}"):
                                supabase.table("tasks").delete().eq("id", task["id"]).execute()
                                st.rerun()

# --- Rodapé: Criar Nova Tarefa ---
st.divider()
with st.expander("➕ Adicionar Nova Atividade / Projeto"):
    tab1, tab2 = st.tabs(["Nova Tarefa", "Novo Projeto"])
    
    with tab1:
        with st.form("new_task_form"):
            t_title = st.text_input("Título da Atividade")
            t_desc = st.text_area("Descrição / Produtos")
            c1, c2 = st.columns(2)
            t_start = c1.date_input("Início", date.today())
            t_end = c2.date_input("Prazo Final", date.today())
            
            # Tenta pré-selecionar o usuário atual
            default_idx = 0
            if st.session_state["current_user"] in member_names:
                default_idx = member_names.index(st.session_state["current_user"])
            
            t_owner = st.selectbox("Responsável", member_names, index=default_idx)
            
            submitted = st.form_submit_button("Criar Tarefa")
            if submitted and selected_project_name:
                data = {
                    "project_id": project_id,
                    "title": t_title,
                    "description": t_desc,
                    "start_date": str(t_start),
                    "end_date": str(t_end),
                    "owner_name": t_owner,
                    "status": "Não Iniciado",
                    "progress": 0
                }
                supabase.table("tasks").insert(data).execute()
                st.success("Tarefa criada!")
                st.rerun()
    
    with tab2:
        with st.form("new_proj_form"):
            p_name = st.text_input("Nome do Projeto")
            p_desc = st.text_area("Descrição")
            p_pin = st.text_input("Definir Senha do Projeto (PIN)", type="password", max_chars=4)
            
            p_submitted = st.form_submit_button("Criar Projeto")
            if p_submitted and p_name and p_pin:
                supabase.table("projects").insert({
                    "name": p_name, 
                    "description": p_desc,
                    "pin_code": p_pin
                }).execute()
                st.success(f"Projeto {p_name} criado!")
                st.rerun()

# --- Rodapé: Deletar Projeto (Área Perigosa) ---
if selected_project_name:
    with st.expander("🔴 Zona de Perigo (Projeto)"):
        st.write(f"Deseja apagar o projeto **{selected_project_name}** e todas as suas tarefas?")
        del_pin = st.text_input("Digite o PIN do Projeto para confirmar:", type="password")
        if st.button("APAGAR PROJETO PERMANENTEMENTE"):
            if del_pin == project_pin:
                supabase.table("projects").delete().eq("id", project_id).execute()
                st.success("Projeto deletado.")
                time.sleep(2)
                st.rerun()
            else:
                st.error("PIN incorreto!")
