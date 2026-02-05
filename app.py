import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import time
import os # Necessário para verificar se a imagem existe

# --- Configuração da Página e CSS Personalizado ---
st.set_page_config(page_title="Gestão Kanban AURA", page_icon="🚀", layout="wide")

# CSS para melhorar a aparência dos avatares e filtros
st.markdown("""
<style>
    .avatar-btn {text-align: center; cursor: pointer;}
    .avatar-img {border-radius: 50%; width: 50px; height: 50px; object-fit: cover; border: 2px solid #ddd;}
    .avatar-img:hover {border-color: #ff4b4b;}
    /* Cores das Colunas */
    .header-todo {color: #d9534f; border-bottom: 3px solid #d9534f; padding-bottom: 5px;}
    .header-doing {color: #f0ad4e; border-bottom: 3px solid #f0ad4e; padding-bottom: 5px;}
    .header-done {color: #5cb85c; border-bottom: 3px solid #5cb85c; padding-bottom: 5px;}
</style>
""", unsafe_allow_html=True)

# --- Mapeamento Manual de Nomes para Arquivos de Imagem ---
# Adicione aqui como você quer mapear os nomes do banco para os arquivos.
# Se o nome no banco for "Marcelo" e o arquivo for "Marcelo Pena.png", mapeie aqui.
IMAGE_MAP = {
    "Michael": "Michael.png",
    "Môroni": "Môroni.png",
    "Ranyer": "Ranyer.png",
    "Isabela": "Isabela.png",
    "Leonardo": "Leonardo.png",
    "Marcelo": "Marcelo Pena.png", 
    # Adicione outros conforme necessário, usando o primeiro nome como chave se preferir
}
DEFAULT_EMOJIS = ["👤", "🧑‍💼", "👩‍💻", "🧑‍💻", "🦸", "🦸‍♀️"]

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
    df = pd.DataFrame(response.data)
    if not df.empty:
        return df["name"].tolist()
    return []

def get_projects():
    response = supabase.table("projects").select("*").order("created_at").execute()
    return pd.DataFrame(response.data)

def get_tasks(project_id):
    response = supabase.table("tasks").select("*").eq("project_id", project_id).order("end_date").execute()
    return pd.DataFrame(response.data)

# Função atualizada para aceitar LISTA de donos
def update_full_task(task_id, title, desc, owner_list, start_d, end_d, progress):
    status = "Em Andamento"
    if progress == 100: status = "Concluído"
    elif progress == 0: status = "Não Iniciado"
    
    # Junta a lista com " / " para salvar no banco como texto
    owner_string = " / ".join(owner_list)
    
    data = {
        "title": title,
        "description": desc,
        "owner_name": owner_string, # Salva a string combinada
        "start_date": str(start_d),
        "end_date": str(end_d),
        "progress": progress,
        "status": status
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

# --- Função Geradora de Relatório HTML ---
def generate_html_report(project_name, metrics, tasks_df):
    
    html_template = f"""
    <html>
    <head>
        <title>Relatório Executivo - {project_name}</title>
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
        <h1>🚀 Relatório de Status: {project_name}</h1>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        
        <div class="metrics-container">
            <div class="metric-box"><div class="metric-lbl">Total Atividades</div><div class="metric-val">{metrics['total']}</div></div>
            <div class="metric-box"><div class="metric-lbl">Concluídas</div><div class="metric-val">{metrics['done']} ({metrics['perc']}%)</div></div>
            <div class="metric-box"><div class="metric-lbl">Previsão Término</div><div class="metric-val">{metrics['forecast']}</div></div>
        </div>

        <h2>Detalhamento das Atividades</h2>
        {tasks_df[['title', 'status', 'progress', 'owner_name', 'end_date']].to_html(index=False, classes="minimal-table")}
    </body>
    </html>
    """
    return html_template

# --- Interface Principal ---

# Inicializa estado do filtro
if "filter_user" not in st.session_state:
    st.session_state["filter_user"] = None

# 1. Header
st.title("🚀 Gestão Visual de Projetos")
st.divider()

# 2. Seleção de Projeto
projects_df = get_projects()
all_members_list = get_members()

if projects_df.empty:
    st.warning("Nenhum projeto encontrado. Crie um novo no rodapé.")
    selected_project_name = None
else:
    col_sel, col_actions = st.columns([3, 1])
    with col_sel:
        project_names = projects_df["name"].tolist()
        selected_project_name = st.selectbox("📂 Selecione o Projeto", project_names)
        project_data = projects_df[projects_df["name"] == selected_project_name].iloc[0]
        project_id = int(project_data["id"])
        project_pin = project_data["pin_code"]
    
    with col_actions:
        if st.toggle("📺 Modo TV (Auto-Refresh)"):
            time.sleep(30)
            st.rerun()
            
        # Botão de Limpar Filtro se estiver ativo
        if st.session_state["filter_user"]:
            if st.button(f"❌ Limpar Filtro: {st.session_state['filter_user']}"):
                st.session_state["filter_user"] = None
                st.rerun()

# 3. Lógica do Dashboard e Filtros
if selected_project_name:
    tasks_df = get_tasks(project_id)
    
    # --- BARRA LATERAL: GERAR RELATÓRIO ---
    with st.sidebar:
        st.header("🖨️ Relatórios")
        if not tasks_df.empty:
             # Recalcula métricas para o relatório
            t_total = len(tasks_df)
            t_done = len(tasks_df[tasks_df['progress'] == 100])
            t_perc = int((t_done / t_total) * 100) if t_total > 0 else 0
            t_max_date = pd.to_datetime(tasks_df['end_date'], errors='coerce').max()
            t_forecast = t_max_date.strftime("%d/%m/%Y") if pd.notnull(t_max_date) else "N/A"
            
            metrics_data = {'total': t_total, 'done': t_done, 'perc': t_perc, 'forecast': t_forecast}
            
            html_string = generate_html_report(selected_project_name, metrics_data, tasks_df)
            file_name = f"Relatorio_{selected_project_name.replace(' ', '_')}_{date.today()}.html"
            
            st.download_button(
                label="📄 Baixar Relatório Executivo (HTML)",
                data=html_string,
                file_name=file_name,
                mime="text/html"
            )
        else:
            st.write("Sem dados para gerar relatório.")

    # --- MÉTRICAS DE TOPO ---
    if not tasks_df.empty:
        tasks_df['end_date'] = pd.to_datetime(tasks_df['end_date'], errors='coerce')
        total_tasks = len(tasks_df)
        completed_tasks = len(tasks_df[tasks_df['progress'] == 100])
        perc_conclusao = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        max_date = tasks_df['end_date'].max()
        forecast_str = max_date.strftime("%d/%m/%Y") if pd.notnull(max_date) else "Indefinido"
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Atividades", total_tasks)
        m2.metric("Concluído", f"{completed_tasks} ({int(perc_conclusao)}%)")
        m3.metric("Previsão Término Projeto", forecast_str)
        st.progress(int(tasks_df['progress'].mean()), text="Progresso Médio Geral")
        
        st.markdown("---")
        
        # --- NOVA SEÇÃO: FILTRO POR AVATAR DOS CONSULTORES ---
        st.subheader("Filtro Rápido por Consultor")
        
        # 1. Extrair nomes únicos das strings "Nome / Outro Nome"
        unique_owners = set()
        for owner_str in tasks_df["owner_name"].dropna().unique():
            parts = [p.strip() for p in owner_str.split("/")]
            unique_owners.update(parts)
        sorted_owners = sorted(list(unique_owners))
        
        if sorted_owners:
            # Cria colunas dinâmicas para os avatares
            cols_avatar = st.columns(len(sorted_owners))
            for i, owner_name in enumerate(sorted_owners):
                with cols_avatar[i]:
                    # Tenta achar a imagem mapeada
                    image_file = IMAGE_MAP.get(owner_name) or IMAGE_MAP.get(owner_name.split(" ")[0])
                    
                    # Verifica se o arquivo realmente existe no sistema
                    has_image = False
                    if image_file and os.path.exists(image_file):
                        has_image = True

                    if has_image:
                        # Exibe imagem redonda
                        st.markdown(f"""
                            <div class="avatar-btn">
                                <img src="app/{image_file}" class="avatar-img" title="Filtrar por {owner_name}">
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Exibe Emoji se não tiver imagem
                        emoji = DEFAULT_EMOJIS[i % len(DEFAULT_EMOJIS)]
                        st.markdown(f'<div style="text-align:center; font-size: 40px;" title="{owner_name}">{emoji}</div>', unsafe_allow_html=True)
                    
                    # Botão para ativar o filtro
                    if st.button(owner_name.split(" ")[0], key=f"btn_av_{i}", use_container_width=True):
                        st.session_state["filter_user"] = owner_name
                        st.rerun()

        # --- APLICAÇÃO DO FILTRO NO DATAFRAME ---
        filtered_df = tasks_df.copy()
        if st.session_state["filter_user"]:
            # Filtra se a string de donos CONTÉM o nome selecionado
            filtered_df = filtered_df[filtered_df['owner_name'].str.contains(st.session_state["filter_user"], na=False, case=False)]
            st.caption(f"Exibindo apenas tarefas de: **{st.session_state['filter_user']}**")

        st.markdown("---")

        # --- KANBAN BOARD COM CORES DISTINTAS ---
        c_todo, c_doing, c_done = st.columns(3)
        cols = {"Não Iniciado": c_todo, "Em Andamento": c_doing, "Concluído": c_done}
        
        # Cabeçalhos Coloridos usando CSS personalizado definido no início
        c_todo.markdown('<h3 class="header-todo">📝 A Fazer (Backlog)</h3>', unsafe_allow_html=True)
        c_doing.markdown('<h3 class="header-doing">🔨 Em Execução</h3>', unsafe_allow_html=True)
        c_done.markdown('<h3 class="header-done">✅ Concluído</h3>', unsafe_allow_html=True)

        if not filtered_df.empty:
            filtered_df = filtered_df.sort_values(by="end_date", ascending=True)

            for index, task in filtered_df.iterrows():
                status = task["status"]
                if status not in cols: status = "Não Iniciado"
                
                with cols[status]:
                    container = st.container(border=True)
                    with container:
                        st.markdown(f"**{task['title']}**")
                        # Mostra múltiplos donos
                        st.caption(f"👥 {task['owner_name']}")
                        
                        d_end_str = "S/ Data"
                        if pd.notnull(task["end_date"]):
                            d_end = task["end_date"].date()
                            d_end_str = d_end.strftime('%d/%m')
                            today = date.today()
                            if d_end < today and task["progress"] < 100:
                                st.markdown(f"🔴 **Prazo: {d_end_str}**")
                            else:
                                st.markdown(f"📅 Prazo: {d_end_str}")

                        st.progress(task["progress"])
                        
                        # --- POPOVER DE EDIÇÃO MULTI-USUÁRIO ---
                        popover = st.popover("✏️ Editar / Detalhes", use_container_width=True)
                        
                        with popover:
                            st.markdown(f"### Editando: {task['title']}")
                            with st.form(key=f"form_edit_{task['id']}"):
                                ed_title = st.text_input("Título", value=task["title"])
                                ed_desc = st.text_area("Descrição", value=task["description"] if task["description"] else "")
                                
                                c_ed1, c_ed2 = st.columns(2)
                                try: val_start = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
                                except: val_start = date.today()
                                try: val_end = task["end_date"].date()
                                except: val_end = date.today()
                                ed_start = c_ed1.date_input("Início", value=val_start)
                                ed_end = c_ed2.date_input("Fim", value=val_end)
                                
                                # --- NOVA LÓGICA DE MULTISELEÇÃO ---
                                # 1. Divide a string atual "A / B" em lista ["A", "B"]
                                current_owners_list = [o.strip() for o in task["owner_name"].split("/")] if task["owner_name"] else []
                                # 2. Filtra para garantir que os atuais ainda existem na lista geral
                                valid_defaults = [o for o in current_owners_list if o in all_members_list]
                                
                                # 3. Multiselect
                                ed_owners = st.multiselect("Responsáveis (Múltiplos)", all_members_list, default=valid_defaults)
                                
                                ed_progress = st.slider("Progresso %", 0, 100, int(task["progress"]))
                                
                                if st.form_submit_button("💾 Salvar Alterações"):
                                    # Envia a LISTA de donos para a função
                                    update_full_task(task['id'], ed_title, ed_desc, ed_owners, ed_start, ed_end, ed_progress)
                                    st.success("Atualizado!")
                                    time.sleep(0.5)
                                    st.rerun()
    else:
        st.info("Sem atividades para os filtros atuais.")

# --- ÁREA DE CRIAÇÃO E CONFIGURAÇÃO ---
st.divider()
st.subheader("🛠️ Ferramentas")

tab1, tab2, tab3 = st.tabs(["➕ Nova Atividade", "⚙️ Editar Projeto (Admin)", "🆕 Novo Projeto"])

# ABA 1: NOVA TAREFA (Com Multiseleção)
with tab1:
    if selected_project_name:
        with st.form("new_task_form"):
            col_t1, col_t2 = st.columns([2, 1])
            nt_title = col_t1.text_input("Título da Atividade")
            # Multiselect aqui também
            nt_owners = col_t2.multiselect("Responsáveis", all_members_list)
            
            nt_desc = st.text_area("Descrição")
            c_d1, c_d2 = st.columns(2)
            nt_start = c_d1.date_input("Data Início", date.today())
            nt_end = c_d2.date_input("Data Prazo", date.today())
            
            if st.form_submit_button("Adicionar Tarefa"):
                # Junta a lista para salvar
                owner_string = " / ".join(nt_owners)
                
                data = {
                    "project_id": project_id,
                    "title": nt_title,
                    "description": nt_desc,
                    "start_date": str(nt_start),
                    "end_date": str(nt_end),
                    "owner_name": owner_string,
                    "status": "Não Iniciado",
                    "progress": 0
                }
                supabase.table("tasks").insert(data).execute()
                st.success("Tarefa criada!")
                st.rerun()
    else:
        st.info("Selecione um projeto para criar tarefas.")

# ABA 2 e 3 permanecem iguais ao anterior...
with tab2:
    if selected_project_name:
        st.markdown(f"**Editando configurações de: {selected_project_name}**")
        with st.form("edit_project_form"):
            new_proj_name = st.text_input("Nome do Projeto", value=project_data["name"])
            new_proj_desc = st.text_area("Descrição do Projeto", value=project_data["description"])
            auth_pin = st.text_input("🔒 Digite o PIN do Projeto para salvar alterações:", type="password")
            if st.form_submit_button("Atualizar Dados do Projeto"):
                if auth_pin == project_pin:
                    supabase.table("projects").update({"name": new_proj_name,"description": new_proj_desc}).eq("id", project_id).execute()
                    st.success("Dados do projeto atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("PIN Incorreto!")
    else:
        st.warning("Selecione um projeto.")

with tab3:
    with st.form("create_proj_form"):
        cp_name = st.text_input("Nome do Novo Projeto")
        cp_desc = st.text_area("Descrição")
        cp_pin = st.text_input("Crie uma Senha (PIN):", max_chars=4, type="password")
        if st.form_submit_button("Criar Projeto"):
            if cp_name and cp_pin:
                supabase.table("projects").insert({"name": cp_name, "description": cp_desc,"pin_code": cp_pin}).execute()
                st.success(f"Projeto {cp_name} criado!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nome e PIN obrigatórios.")
