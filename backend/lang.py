from typing import Annotated
from typing_extensions import TypedDict
import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage
from langgraph.graph.message import add_messages
import os
from langchain.chat_models import init_chat_model
from new import read_gmail_messages, get_current_time, calculate

# Set up environment
GOOGLE_API_KEY = "AIzaSyC1aDVVu9iOq_o1275gshGHtbbwlQdBHww"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Initialize LLM
llm = init_chat_model("google_genai:gemini-2.5-flash")

# Define all tools
tools = [read_gmail_messages, get_current_time, calculate]

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# Tell the LLM which tools it can call
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")

        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

# Pass all tools to BasicToolNode
tool_node = BasicToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

# Add the missing conditional edges and routing
def route_tools(state: State):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

# Add conditional edges
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    {"tools": "tools", END: END},
)

# Add edges
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

# Compile the graph
graph = graph_builder.compile()

# Generate and save the graph image
# try:
#     image_data = graph.get_graph(xray=True).draw_mermaid_png()
#     output_path = os.path.join(os.path.dirname(__file__), "graph.png")
#     with open(output_path, "wb") as f:
#         f.write(image_data)
#     print(f"Graph image saved to: {output_path}")
# except Exception as e:
#     print(f"Error saving graph image: {e}")
