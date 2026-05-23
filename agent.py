import os
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import create_task, update_task, delete_task, change_priority, list_tasks

SYSTEM_PROMPT = """You are an intelligent todo list assistant.

Tools available:
- create_task: Create new tasks
- update_task: Update existing tasks
- delete_task: Delete tasks
- change_priority: Change task priority
- list_tasks: View all tasks

Field requirements:
- priority: "low", "medium", or "high"
- status: "not_started", "in_progress", or "completed"
- due_date: DD-MM-YYYY format

Be friendly, conversational, and helpful. Extract information from natural language and use appropriate tools."""


def run_agent(user_input: str, conversation_history: List = None) -> tuple[str, List]:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "API key not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY.", conversation_history

    tools = [create_task, update_task, delete_task, change_priority, list_tasks]
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=api_key,
        temperature=0.7,
    ).bind_tools(tools)

    if conversation_history is None:
        conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]

    conversation_history.append(HumanMessage(content=user_input))
    ai_msg = model.invoke(conversation_history)
    conversation_history.append(ai_msg)

    if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
        tool_map = {
            "create_task": create_task,
            "update_task": update_task,
            "delete_task": delete_task,
            "change_priority": change_priority,
            "list_tasks": list_tasks,
        }

        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    tool_message = ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name,
                    )
                    conversation_history.append(tool_message)
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name,
                    )
                    conversation_history.append(tool_message)

        final_response = model.invoke(conversation_history)
        conversation_history.append(final_response)
        return final_response.content, conversation_history

    return ai_msg.content, conversation_history
