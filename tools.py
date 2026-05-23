from db import TaskDatabase
from langchain.tools import tool


db: TaskDatabase = TaskDatabase()


def set_db(database: TaskDatabase) -> None:
    global db
    db = database


@tool(description="Creates a new task")
def create_task(title: str, description: str, priority: str, due_date: str, status: str) -> str:
    task = db.create(title, description, priority, due_date, status)
    return f"Task created: #{task['id']} - {task['title']} ({task['priority']} priority)"


@tool(description="Updates an existing task")
def update_task(task_id: str, title: str = None, description: str = None, 
                priority: str = None, due_date: str = None, status: str = None) -> str:
    task = db.update(task_id, title=title, description=description, 
                     priority=priority, due_date=due_date, status=status)
    if task:
        return f"Task #{task['id']} updated: {task['title']}"
    return f"Task {task_id} not found"


@tool(description="Deletes a task")
def delete_task(task_id: str) -> str:
    success = db.delete(task_id)
    return f"Task {task_id} deleted" if success else f"Task {task_id} not found"


@tool(description="Changes task priority")
def change_priority(task_id: str, priority: str) -> str:
    task = db.update(task_id, priority=priority)
    return f"Task {task_id} priority → {priority}" if task else f"Task {task_id} not found"


@tool(description="Lists all tasks")
def list_tasks() -> str:
    tasks = db.get_all()
    if not tasks:
        return "No tasks found"
    result = "Tasks:\n"
    for task in tasks:
        result += f"#{task['id']}: {task['title']} ({task['priority']}, {task['status']})\n"
    return result
