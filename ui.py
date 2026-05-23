import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from agent import run_agent
from db import TaskDatabase
from tools import set_db

load_dotenv()

# --- HELPER FUNCTIONS ---

def parse_due_date(date_str: str):
    if isinstance(date_str, datetime):
        return date_str
    if not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if not date_str:
        return None

    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    return None


def normalize_status(status: str) -> str:
    if not isinstance(status, str):
        return ""
    return status.strip().lower().replace("_", " ")


def filter_tasks(tasks, filter_field, filter_value):
    if filter_field == "None" or filter_value == "All":
        return tasks

    filtered = []
    normalized_filter = normalize_status(filter_value)

    for task in tasks:
        status = normalize_status(task.get("status", ""))
        priority = task.get("priority", "").strip().lower()
        due_date = task.get("due_date", "")
        parsed_due = parse_due_date(due_date)

        if filter_field == "Status":
            if status != normalized_filter:
                continue
        elif filter_field == "Priority":
            if filter_value.lower() != priority:
                continue
        elif filter_field == "Due date":
            today = datetime.now().date()
            if not parsed_due:
                continue
            due_day = parsed_due.date()
            if filter_value == "Overdue" and due_day >= today:
                continue
            if filter_value == "Due today" and due_day != today:
                continue
            if filter_value == "Upcoming" and due_day <= today:
                continue

        filtered.append(task)
    return filtered


def sort_tasks(tasks, sort_option):
    if sort_option == "Due date (soonest)":
        return sorted(tasks, key=lambda t: parse_due_date(t.get("due_date", "")) or datetime.max)
    if sort_option == "Due date (latest)":
        return sorted(tasks, key=lambda t: parse_due_date(t.get("due_date", "")) or datetime.min, reverse=True)
    if sort_option == "Priority":
        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(tasks, key=lambda t: priority_order.get(t.get("priority", "").lower(), 3))
    if sort_option == "Status":
        status_order = {"completed": 0, "in progress": 1, "not started": 2}
        return sorted(tasks, key=lambda t: status_order.get(normalize_status(t.get("status", "")), 3))
    return sorted(tasks, key=lambda x: int(x.get('id', 0)))


# --- PAGE CONFIGURATION ---

st.set_page_config(
    page_title="AI Todo Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- GLOBAL STYLING ---

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #09090b 0%, #1e1b4b 100%);
            color: #f8fafc;
        }
        /* Custom Styling for Task Cards */
        .task-card {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #6366f1;
            padding: 1.2rem;
            border-radius: 12px;
            margin-bottom: 1rem;
        }
        .task-card-completed {
            background-color: rgba(16, 185, 129, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-left: 5px solid #10b981;
            padding: 1.2rem;
            border-radius: 12px;
            margin-bottom: 1rem;
        }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 6px;
            text-transform: uppercase;
            margin-right: 0.5rem;
        }
        .badge-high { background-color: rgba(239, 68, 68, 0.2); color: #f87171; }
        .badge-medium { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .badge-low { background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge-status { background-color: rgba(255, 255, 255, 0.1); color: #e2e8f0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- STATE INITIALIZATION ---

if 'db' not in st.session_state:
    st.session_state.db = TaskDatabase()

db = st.session_state.db
set_db(db)

if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi there! I can help you manage tasks, create new to-dos, update priorities, and keep your schedule organized. Try typing: *'Add a high priority task to review backend code by tomorrow'*"}
    ]

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = None


# --- APPLICATION HEADER ---

st.title("AI Todo Assistant")
st.caption("Manage your tasks seamlessly with natural language commands powered by an AI Agent.")
st.divider()


# --- MAIN LAYOUT ---

col1, col2 = st.columns([3, 2], gap="large")

# Task Dashboard
with col1:
    st.subheader("Task Board")
    
    # Unified filter / sort controls
    f_col1, f_col2, f_col3 = st.columns([1.2, 1.2, 1.2])
    with f_col1:
        action_choice = st.selectbox("Action", ["None", "Filter", "Sort"], index=0, key="action_choice")
    with f_col2:
        field_choice = st.selectbox("Field", ["Status", "Priority", "Due date"], index=0, key="field_choice")
    with f_col3:
        if action_choice == "Filter":
            if field_choice == "Status":
                control_choice = st.selectbox("Status", ["All", "Completed", "Not Started", "In Progress"], index=0, key="filter_value")
            elif field_choice == "Priority":
                control_choice = st.selectbox("Priority", ["All", "High", "Medium", "Low"], index=0, key="filter_value")
            else:
                control_choice = st.selectbox("Due date", ["All", "Overdue", "Due today", "Upcoming"], index=0, key="filter_value")
        elif action_choice == "Sort":
            if field_choice == "Due date":
                control_choice = st.selectbox("Order", ["Due date (soonest)", "Due date (latest)"], index=0, key="sort_value")
            else:
                control_choice = field_choice
        else:
            st.write(" ")
            control_choice = None

    st.write("")  # Padding spacer

    # Fetch, filter, and sort tasks dynamically from state database
    tasks = db.get_all()
    if action_choice == "Filter":
        tasks = filter_tasks(tasks, field_choice, control_choice)
    if action_choice == "Sort":
        tasks = sort_tasks(tasks, control_choice)
    if action_choice == "None":
        tasks = sort_tasks(tasks, "ID")

    if not tasks:
        st.info("No tasks found matching your active filter criteria.")
    else:
        # Loop over database records and project cleanly styled custom cards
        for task in tasks:
            is_completed = task['status'].lower() == 'completed'
            card_style = "task-card-completed" if is_completed else "task-card"
            p_level = task['priority'].lower()
            
            due_display = task.get('due_date', 'No date') or 'No date'
            status_text = task['status'].replace('_', ' ').title()
            
            st.markdown(
                f"""
                <div class="{card_style}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-size: 1.15rem; font-weight: 600; color: #ffffff;">#{task['id']} - {task['title']}</span>
                        <div>
                            <span class="badge badge-{p_level}">{task['priority'].title()}</span>
                            <span class="badge badge-status">{status_text}</span>
                        </div>
                    </div>
                    <p style="margin: 0.5rem 0 1rem 0; color: #cbd5e1; font-size: 0.95rem;">{task['description']}</p>
                    <div style="font-size: 0.85rem; color: #94a3b8; display: flex; align-items: center; gap: 4px;">
                        📅 <b>Due:</b> {due_display}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


# Chatbot Interface
with col2:
    st.subheader("Agent Chat")
    
    chat_container = st.container(height=600)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Ask me to update or manage your tasks..."):
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt})

        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing command..."):
                    response, st.session_state.conversation_history = run_agent(
                        prompt,
                        st.session_state.conversation_history,
                    )
                    st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()