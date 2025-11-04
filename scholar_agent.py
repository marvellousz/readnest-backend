# scholar_agent.py
import os
import json
import traceback
from dotenv import load_dotenv

# Groq client wrapper (langchain_groq)
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

load_dotenv()  # loads GROQ_API_KEY, optional GROQ_MODEL

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.2,
    groq_api_key=GROQ_API_KEY,
)

prompt = PromptTemplate(
    input_variables=["user_prompt", "papers"],
    template="""
You are a Scholar Agent. A user asked:
{user_prompt}

We already fetched some research papers (from Semantic Scholar / OpenAlex):
{papers}

Your job:
1. Summarize each paper in 2-3 sentences.
2. For each paper, return Title, Summary, and Link.

Respond as a JSON array only, e.g.:
[
  {{"title":"...","summary":"...","link":"..."}},
  ...
]
"""
)

def safe_parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None

def build_fallback_results(papers):
    fallback = []
    for p in papers or []:
        title = p.get("title") or p.get("name") or "Untitled"
        summary = p.get("summary") or p.get("abstract") or p.get("snippet") or (p.get("content") or "")[:800]
        if not summary:
            summary = "No abstract available — open the paper link to read."
        link = p.get("link") or p.get("url") or ""
        fallback.append({"title": title, "summary": summary, "link": link})
    return fallback

def scholar_node(state):
    user_prompt = state.get("user_prompt", "")
    papers = state.get("papers", [])

    # stringify (truncate to avoid extremely long input)
    try:
        papers_text = json.dumps(papers, ensure_ascii=False, default=str)[:20000]
    except Exception:
        papers_text = str(papers)[:20000]

    formatted = prompt.format(user_prompt=user_prompt, papers=papers_text)

    try:
        response = llm.invoke(formatted)
        raw = getattr(response, "content", None) or getattr(response, "text", None) or str(response)
        parsed = safe_parse_json(raw)

        # direct parse success
        if parsed and isinstance(parsed, list):
            normalized = []
            for item in parsed:
                if isinstance(item, dict):
                    normalized.append({
                        "title": item.get("title") or item.get("name") or "Untitled",
                        "summary": item.get("summary") or item.get("abstract") or "",
                        "link": item.get("link") or item.get("url") or ""
                    })
            return {"results": normalized}

        # try to extract JSON array substring
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            maybe = raw[start:end+1]
            parsed2 = safe_parse_json(maybe)
            if parsed2 and isinstance(parsed2, list):
                normalized = []
                for item in parsed2:
                    if isinstance(item, dict):
                        normalized.append({
                            "title": item.get("title") or item.get("name") or "Untitled",
                            "summary": item.get("summary") or item.get("abstract") or "",
                            "link": item.get("link") or item.get("url") or ""
                        })
                return {"results": normalized}

        # unparseable -> return fallback plus raw for debugging
        fallback = build_fallback_results(papers)
        return {"error": "LLM returned unparseable output", "raw": raw[:4000], "results": fallback}

    except Exception as e:
        tb = traceback.format_exc()
        print("=== scholar_node exception ===")
        print(tb)
        fallback = build_fallback_results(papers)
        return {"error": str(e), "traceback": tb, "results": fallback}

graph = StateGraph(dict)
graph.add_node("scholar", scholar_node)
graph.set_entry_point("scholar")
graph.add_edge("scholar", END)

scholar_agent = graph.compile()
