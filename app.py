import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import time
import os
import base64

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Kanban AURA", page_icon="🚀", layout="wide")

# --- CSS Personalizado (Estilos) ---
st.markdown("""
<style>
    /* Estilo dos Avatares no Filtro */
    .avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 10px;
    }
    .avatar-img {
        border-radius: 50%;
        width: 60px;
        height: 60px;
        object-fit: cover;
        border: 2px solid #ddd;
        transition: transform 0.2s;
    }
    .avatar-img:hover {
        border-color: #ff4b4b;
        transform: scale(1.1);
    }
    
    /* Mini Avatar dentro do Card */
    .mini-avatar {
        border-radius: 50%;
        width: 25px;
        height: 25px;
        object-fit: cover;
        border: 1px solid #ccc;
        vertical-align: middle;
        margin-right: 5px;
    }

    /* Cores das Colunas (Cabeçalhos) */
    .header-todo {color: #d9534f; border-bottom: 3px solid #d9534f; padding-bottom: 5px;}
    .header-doing {color: #f0ad4e; border-bottom: 3px solid #f0ad4e; padding-bottom: 5px;}
    .header-done {color: #5cb85c; border-bottom: 3px solid #5cb85c; padding-bottom: 5px;}
    
    /* Botões do Filtro */
    div.stButton > button {
        width: 100%;
        border-radius: 20px;
        padding: 0px 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Mapeamento de Imagens (Baseado no seu print) ---
# Certifique-se que os arquivos estão na mesma pasta do app.py
IMAGE_MAP = {
    "Michael": "Michael.png",
    "Môroni": "Môroni.png", 
    "Morôni": "Môroni.png", # Garantindo caso digitem sem acento
    "Moroni": "Môroni.png",
    "Ranyer": "Ranyer.jpg", # Notei que no print é .jpg
    "Isabela": "Isabela.png",
    "Leonardo": "Leonardo.png",
    "Marcelo": "Marcelo Pena.png", 
    "Douglas": "Douglas.png", # Exemplo
}
DEFAULT_EMOJIS = ["👤", "🧑‍💼", "👩‍💻", "🧑‍💻", "🦸", "🦸‍♀️"]

# --- Funções Auxiliares ---

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# Função Mágica para Converter Imagem em Base64 (Resolve o erro de imagem quebrada)
def get_image_base64(name):
    # Tenta achar o arquivo mapeado
    filename = IMAGE_MAP.get(name) or IMAGE_MAP.get(name.split(" ")[0])
    
    if filename and os.path.exists(filename):
        with open(filename, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
            # Retorna a tag img pronta
            return f'<img src="data:image/png;base64,{encoded}" class="avatar-img" title="{name}">'
    return None

# Função para pegar mini avatar (para os cards)
def get_mini_avatar_html(owner_string):
    if not owner_string: return ""
    
    html = ""
    # Separa os donos
    owners = [o.strip() for o in owner_string.split("/")]
    
    for owner in owners:
        filename = IMAGE_MAP.get(owner) or IMAGE_MAP.get(owner.split(" ")[0])
        if filename and os.path.exists(filename):
            with open(filename, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                html += f'<img src="data:image/png;base64,{encoded}" class="mini-avatar" title="{owner}">'
        else:
            html += "👤" # Fallback se não tiver foto
            
    return html

def get_members():
    response = supabase.table("members").select("*").order("name").execute()
    df = pd.DataFrame(response.data)
    if not df.empty: return df["name"].tolist()
    return []

def get_projects():
    response = supabase.table("projects").select("*").order("created_at").execute()
    return pd.DataFrame(response.data)

def get_tasks(project_id):
    response = supabase.table("tasks").select("*").eq("project_id", project_id).order("end_date").execute()
    return pd.DataFrame(response.data)

def update_full_task(task_id, title, desc, owner_list, start_d, end_d, progress):
    status = "Em Andamento"
    if progress == 100: status = "Concluído"
    elif progress == 0: status = "Não Iniciado"
    
    owner_string = " / ".join(owner_list)
    
    data = {
        "title": title, "description": desc, "owner_name": owner_string,
        "start_date": str(start_d), "end_date": str(end_d),
        "progress": progress, "status": status
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

# Função HTML Report
def generate_html_report(project_name, metrics, tasks_df):
    html_template = f"""
    <html>
    <head>
        <title>Status - {project_name}</title>
        <style>
            body {{ font-family: sans-serif; color: #333; padding: 20px; }}
            h1 {{ color: #0E1117; }}
            .metrics-container {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .metric-box {{ background: #f0f2f6; padding: 15px; border-radius: 8px; min-width: 150px; text-align: center; }}
            .metric-val {{ font-size: 24px; font-weight: bold; color: #ff4b4b; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #0E1117; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>🚀 {project_name}</h1>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <div class="metrics-container">
            <div class="metric-box"><div class="metric-lbl">Total</div><div class="metric-val">{metrics['total']}</div></div>
            <div class="metric-box"><div class="metric-lbl">Concluídas</div><div class="metric-val">{metrics['done']} ({metrics['perc']}%)</div></div>
            <div class="metric-box"><div class="metric-lbl">Previsão</div><div class="metric-val">{metrics['forecast']}</div></div>
        </div>
        <h2>Tarefas</h2>
        {tasks_df[['title', 'status', 'progress', 'owner_name', 'end_date']].to_html(index=False)}
    </body>
    </html>
    """
    return html_template

# --- Barra de Progresso Customizada (HTML) ---
def custom_progress_bar(value, color):
    return f"""
    <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; height: 10px; margin-top: 5px; margin-bottom: 5px;">
        <div style="width: {value}%; background-color: {color}; height: 10px; border-radius: 5px;"></div>
    </div>
    """

# --- INÍCIO DA INTERFACE ---

# Inicializa estado do filtro
if "filter_user" not in st.session_state: st.session_state["filter_user"] = None
if "current_user" not in st.session_state: st.session_state["current_user"] = "Visitante"

# Carrega Dados Iniciais
projects_df = get_projects()
all_members_list = get_members()

# --- HEADER (TÍTULO + BOTÃO HTML) ---
# Aqui mudamos o layout para colocar o botão ao lado do título
col_header_title, col_header_btn = st.columns([3, 1])

with col_header_title:
    st.title("🚀 Gestão Visual AURA")

selected_project_name = None
tasks_df = pd.DataFrame()

# Lógica de Seleção de Projeto e Botão HTML
if not projects_df.empty:
    # 1. Seletor de Projeto (Logo abaixo do título para não poluir o header lateral)
    project_names = projects_df["name"].tolist()
    col_sel_proj, col_tv = st.columns([3, 1])
    with col_sel_proj:
        selected_project_name = st.selectbox("📂 Projeto Ativo", project_names)
    with col_tv:
        st.write("") # Espaçador
        if st.toggle("📺 Modo TV"):
            time.sleep(30)
            st.rerun()
            
    # Pega dados do projeto selecionado
    project_data = projects_df[projects_df["name"] == selected_project_name].iloc[0]
    project_id = int(project_data["id"])
    project_pin = project_data["pin_code"]
    tasks_df = get_tasks(project_id)

    # 2. Botão de Download (Agora no Topo Direito)
    with col_header_btn:
        st.write("") # Espaçamento para alinhar verticalmente
        if not tasks_df.empty:
            # Prepara dados
            t_total = len(tasks_df)
            t_done = len(tasks_df[tasks_df['progress'] == 100])
            t_perc = int((t_done / t_total) * 100) if t_total > 0 else 0
            t_max = pd.to_datetime(tasks_df['end_date'], errors='coerce').max()
            t_fore = t_max.strftime("%d/%m/%Y") if pd.notnull(t_max) else "N/A"
            metrics = {'total': t_total, 'done': t_done, 'perc': t_perc, 'forecast': t_fore}
            
            html_data = generate_html_report(selected_project_name, metrics, tasks_df)
            
            st.download_button(
                label="📄 Relatório HTML",
                data=html_data,
                file_name=f"Status_{selected_project_name}.html",
                mime="text/html",
                use_container_width=True
            )

st.divider()

# --- DASHBOARD E FILTROS ---
if selected_project_name and not tasks_df.empty:
    tasks_df['end_date'] = pd.to_datetime(tasks_df['end_date'], errors='coerce')
    
    # Métricas
    total_tasks = len(tasks_df)
    completed_tasks = len(tasks_df[tasks_df['progress'] == 100])
    perc_conclusao = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    max_date = tasks_df['end_date'].max()
    forecast_str = max_date.strftime("%d/%m/%Y") if pd.notnull(max_date) else "Indefinido"
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Atividades", total_tasks)
    m2.metric("Concluído", f"{completed_tasks} ({int(perc_conclusao)}%)")
    m3.metric("Previsão Término", forecast_str)
    
    # Barra Geral
    st.progress(int(tasks_df['progress'].mean()), text="Progresso Global do Projeto")
    
    st.markdown("---")
    
    # --- FILTRO VISUAL POR CONSULTOR ---
    st.subheader("Equipe")
    
    unique_owners = set()
    for owner_str in tasks_df["owner_name"].dropna().unique():
        parts = [p.strip() for p in owner_str.split("/")]
        unique_owners.update(parts)
    sorted_owners = sorted(list(unique_owners))
    
    if sorted_owners:
        # Cria colunas (máximo 8 por linha para não quebrar)
        cols_avatar = st.columns(min(len(sorted_owners), 8))
        
        for i, owner_name in enumerate(sorted_owners):
            # Lógica para quebrar linha se tiver muitos consultores
            col_idx = i % 8
            if i > 0 and i % 8 == 0:
                cols_avatar = st.columns(min(len(sorted_owners) - i, 8))
            
            with cols_avatar[col_idx]:
                # 1. Renderiza Imagem (Base64) ou Emoji
                img_tag = get_image_base64(owner_name)
                
                # Container centralizado
                st.markdown('<div class="avatar-container">', unsafe_allow_html=True)
                if img_tag:
                    st.markdown(img_tag, unsafe_allow_html=True)
                else:
                    emoji = DEFAULT_EMOJIS[i % len(DEFAULT_EMOJIS)]
                    st.markdown(f'<div style="font-size: 40px;">{emoji}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 2. Botão de Filtro
                # Divide o nome para caber no botão (Pega só o primeiro nome)
                short_name = owner_name.split(" ")[0]
                if st.button(short_name, key=f"btn_av_{i}"):
                    st.session_state["filter_user"] = owner_name
                    st.rerun()

    # Botão Limpar Filtro
    if st.session_state["filter_user"]:
        st.info(f"Filtro Ativo: **{st.session_state['filter_user']}**")
        if st.button("❌ Limpar Filtro"):
            st.session_state["filter_user"] = None
            st.rerun()

    st.markdown("---")

    # --- KANBAN BOARD ---
    
    # Filtragem
    filtered_df = tasks_df.copy()
    if st.session_state["filter_user"]:
        filtered_df = filtered_df[filtered_df['owner_name'].str.contains(st.session_state["filter_user"], na=False, case=False)]

    c_todo, c_doing, c_done = st.columns(3)
    cols = {"Não Iniciado": c_todo, "Em Andamento": c_doing, "Concluído": c_done}
    
    # Cabeçalhos Coloridos
    c_todo.markdown('<h3 class="header-todo">📝 A Fazer</h3>', unsafe_allow_html=True)
    c_doing.markdown('<h3 class="header-doing">🔨 Execução</h3>', unsafe_allow_html=True)
    c_done.markdown('<h3 class="header-done">✅ Concluído</h3>', unsafe_allow_html=True)

    if not filtered_df.empty:
        filtered_df = filtered_df.sort_values(by="end_date", ascending=True)

        for index, task in filtered_df.iterrows():
            status = task["status"]
            if status not in cols: status = "Não Iniciado"
            
            with cols[status]:
                container = st.container(border=True)
                with container:
                    # Cabeçalho do Card: Título + Mini Avatares
                    st.markdown(f"**{task['title']}**")
                    
                    # Gera os mini-avatares dos donos
                    avatars_html = get_mini_avatar_html(task['owner_name'])
                    st.markdown(f"<div>{avatars_html} <span style='font-size:0.8em; color:grey'>{task['owner_name']}</span></div>", unsafe_allow_html=True)
                    
                    # Data
                    d_end_str = "S/ Data"
                    if pd.notnull(task["end_date"]):
                        d_end = task["end_date"].date()
                        d_end_str = d_end.strftime('%d/%m')
                        today = date.today()
                        if d_end < today and task["progress"] < 100:
                            st.markdown(f"🔴 **{d_end_str}**")
                        else:
                            st.markdown(f"📅 {d_end_str}")

                    # BARRA DE PROGRESSO CUSTOMIZADA (COLORIDA)
                    bar_color = "#d9534f" # Vermelho padrão
                    if status == "Em Andamento": bar_color = "#f0ad4e" # Laranja
                    if status == "Concluído": bar_color = "#5cb85c" # Verde
                    
                    st.markdown(custom_progress_bar(task["progress"], bar_color), unsafe_allow_html=True)
                    
                    # Botão Popover
                    popover = st.popover("✏️ Editar", use_container_width=True)
                    with popover:
                        with st.form(key=f"form_edit_{task['id']}"):
                            ed_title = st.text_input("Título", value=task["title"])
                            ed_desc = st.text_area("Descrição", value=task["description"] or "")
                            
                            c_ed1, c_ed2 = st.columns(2)
                            try: val_s = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
                            except: val_s = date.today()
                            try: val_e = task["end_date"].date()
                            except: val_e = date.today()
                            
                            ed_start = c_ed1.date_input("Início", value=val_s)
                            ed_end = c_ed2.date_input("Fim", value=val_e)
                            
                            # Multiselect
                            curr_owners = [o.strip() for o in task["owner_name"].split("/")] if task["owner_name"] else []
                            valid_defs = [o for o in curr_owners if o in all_members_list]
                            ed_owners = st.multiselect("Responsáveis", all_members_list, default=valid_defs)
                            
                            ed_progress = st.slider("Progresso %", 0, 100, int(task["progress"]))
                            
                            if st.form_submit_button("💾 Salvar"):
                                update_full_task(task['id'], ed_title, ed_desc, ed_owners, ed_start, ed_end, ed_progress)
                                st.success("Ok!")
                                time.sleep(0.5)
                                st.rerun()

    else:
        st.info("Nenhuma tarefa encontrada com estes filtros.")

# --- RODAPÉ: CRIAÇÃO ---
st.divider()
st.subheader("🛠️ Adicionar / Configurar")

tab1, tab2, tab3 = st.tabs(["➕ Tarefa", "⚙️ Projeto", "🆕 Novo Projeto"])

with tab1:
    if selected_project_name:
        with st.form("new_task_form"):
            col_t1, col_t2 = st.columns([2, 1])
            nt_title = col_t1.text_input("Título")
            nt_owners = col_t2.multiselect("Responsáveis", all_members_list)
            nt_desc = st.text_area("Descrição")
            c_d1, c_d2 = st.columns(2)
            nt_start = c_d1.date_input("Início", date.today())
            nt_end = c_d2.date_input("Prazo", date.today())
            
            if st.form_submit_button("Criar Tarefa"):
                owner_string = " / ".join(nt_owners)
                data = {"project_id": project_id, "title": nt_title, "description": nt_desc,
                        "start_date": str(nt_start), "end_date": str(nt_end),
                        "owner_name": owner_string, "status": "Não Iniciado", "progress": 0}
                supabase.table("tasks").insert(data).execute()
                st.success("Criado!")
                st.rerun()

with tab2:
    if selected_project_name:
        with st.form("edit_proj"):
            n_name = st.text_input("Nome", value=project_data["name"])
            n_desc = st.text_area("Desc", value=project_data["description"])
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Salvar"):
                if pin == project_pin:
                    supabase.table("projects").update({"name": n_name, "description": n_desc}).eq("id", project_id).execute()
                    st.success("Salvo!")
                    st.rerun()
                else: st.error("PIN Errado")

with tab3:
    with st.form("new_proj"):
        cp_name = st.text_input("Nome")
        cp_desc = st.text_area("Descrição")
        cp_pin = st.text_input("PIN (Senha)", max_chars=4, type="password")
        if st.form_submit_button("Criar"):
            supabase.table("projects").insert({"name": cp_name, "description": cp_desc, "pin_code": cp_pin}).execute()
            st.success("Projeto Criado!")
            st.rerun()
