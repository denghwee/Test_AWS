import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from state.agent_state import CompleteOrEscalate

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    streaming=True,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Tavily search tool with advanced configuration
tavily_search = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    api_key=os.getenv("TAVILY_API_KEY")
)


@tool
def search_technical_issue(query: str) -> str:
    """Search the internet for technical troubleshooting guides and solutions.
    Use this for IT-related questions like WiFi issues, software problems, etc."""
    results = tavily_search.invoke(query)
    if not results:
        return "No results found for your query."

    formatted = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "N/A") if isinstance(result, dict) else "Result"
        content = result.get("content", str(result)) if isinstance(result, dict) else str(result)
        url = result.get("url", "") if isinstance(result, dict) else ""
        formatted.append(f"**Source {i}**: {title}\n{content}\n🔗 {url}")

    return "\n\n---\n\n".join(formatted)


it_support_tools = [search_technical_issue]

it_support_agent_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are the **IT Support Agent** for FPT Software's customer service system.

Your capabilities:
- Search the internet for technical troubleshooting guides (search_technical_issue)
- Provide practical, step-by-step solutions from reliable sources

Rules:
1. Always search for solutions before providing answers.
2. Provide clear, actionable troubleshooting steps.
3. Include source references when available.
4. When the user's IT issue is resolved or they want to switch topics, call 'CompleteOrEscalate'.
5. If the issue requires on-site support, recommend escalation to IT department.

Current Context:
- User ID: {user_id}
- Email: {email}
- Conversation ID: {conversation_id}
"""),
    ("placeholder", "{messages}")
])

it_support_agent_runnable = it_support_agent_prompt | llm.bind_tools(
    it_support_tools + [CompleteOrEscalate]
)
