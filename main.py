from langgraph.graph import StateGraph, START, END
from pathlib import Path
import os

from models import ModelState
from tools import (
    read_pdf,
    write_email,
    write_referral,
    get_answers,
    is_email_in_jd,
    find_missing,
    ask_questions,
    create_draft_with_gmail_auth,
    fill_details,
    make_resume_docx,
    make_resume_docx_1,
    make_resume_docx_2,
    make_resume_docx_3,
    make_resume_docx_4,
    make_resume_docx_5,
    get_jd,
    fill_jd,
    jd_provided,
    resume_improvements,
    convert_docx_to_pdf,
    select_resume_format,
)


#Breakdown for frontend
def build_getting_input_graph():
    g = StateGraph(state_schema=ModelState)
    g.add_node("read_pdf", read_pdf)
    g.add_node("fill_jd", fill_jd)
    g.add_node("get_jd", get_jd)
    g.add_node("find_missing", find_missing)
    g.add_node("ask_questions", ask_questions)
    g.add_edge(START, "read_pdf")
    g.add_edge(START, "get_jd")
    g.add_edge("get_jd", "fill_jd")
    g.add_edge("read_pdf", "find_missing")
    g.add_edge("find_missing", "ask_questions")
    g.add_edge("ask_questions", END)
    return g.compile()


def build_process_request_graph():
    g = StateGraph(state_schema=ModelState)
    g.add_node("get_answers", get_answers)
    g.add_node("make_resume_docx", make_resume_docx)
    g.add_node("make_resume_docx_1", make_resume_docx_1)
    g.add_node("make_resume_docx_2", make_resume_docx_2)
    g.add_node("make_resume_docx_3", make_resume_docx_3)
    g.add_node("make_resume_docx_4", make_resume_docx_4)
    g.add_node("make_resume_docx_5", make_resume_docx_5)
    g.add_node("resume_improvements", resume_improvements, defer=True)
    g.add_node("create_draft_with_gmail_auth", create_draft_with_gmail_auth)
    g.add_node("convert_docx_to_pdf", convert_docx_to_pdf)
    g.add_node("write_email", write_email)
    g.add_node("write_referral", write_referral)
    g.add_node("fill_details", fill_details)

    g.add_conditional_edges(
        "convert_docx_to_pdf",
        is_email_in_jd,
        {"email_present": "write_email", "email_absent": "write_referral"},
    )
    g.add_edge(START, "resume_improvements")
    g.add_edge("resume_improvements", "fill_details")
    # Route to selected resume formatter
    g.add_conditional_edges(
        "fill_details",
        select_resume_format,
        {
            "fmt1": "make_resume_docx_1",
            "fmt2": "make_resume_docx_2",
            "fmt3": "make_resume_docx_3",
            "fmt4": "make_resume_docx_4",
            "fmt5": "make_resume_docx_5",
        },
    )
    g.add_edge("make_resume_docx", "convert_docx_to_pdf")
    g.add_edge("write_email", "create_draft_with_gmail_auth")
    g.add_edge("create_draft_with_gmail_auth", END)
    return g.compile()




def build_main_graph():
    g = StateGraph(state_schema=ModelState)
    g.add_node("read_pdf", read_pdf)
    g.add_node("get_jd", get_jd)
    g.add_node("fill_details", fill_details)
    g.add_node("fill_jd", fill_jd)
    g.add_node("find_missing", find_missing)
    g.add_node("ask_questions", ask_questions)
    g.add_node("get_answers", get_answers)
    g.add_node("make_resume_docx", make_resume_docx)
    g.add_node("make_resume_docx_1", make_resume_docx_1)
    g.add_node("make_resume_docx_2", make_resume_docx_2)
    g.add_node("make_resume_docx_3", make_resume_docx_3)
    g.add_node("make_resume_docx_4", make_resume_docx_4)
    g.add_node("make_resume_docx_5", make_resume_docx_5)
    g.add_node("resume_improvements", resume_improvements, defer=True)
    g.add_node("create_draft_with_gmail_auth", create_draft_with_gmail_auth)
    g.add_node("convert_docx_to_pdf", convert_docx_to_pdf)
    g.add_node("write_email", write_email)
    g.add_node("write_referral", write_referral)

    g.add_edge(START, "read_pdf")
    g.add_edge(START, "get_jd")
    g.add_conditional_edges("get_jd", jd_provided, {True: "fill_jd", False: "get_jd"})
    g.add_edge("read_pdf", "find_missing")
    g.add_edge("find_missing", "ask_questions")
    g.add_edge("ask_questions", "get_answers")
    g.add_conditional_edges(
        "convert_docx_to_pdf",
        is_email_in_jd,
        {"email_present": "write_email", "email_absent": "write_referral"},
    )
    g.add_edge(["fill_jd", "get_answers"], "resume_improvements")
    g.add_edge("resume_improvements", "fill_details")
    g.add_conditional_edges(
        "fill_details",
        select_resume_format,
        {
            "fmt1": "make_resume_docx_1",
            "fmt2": "make_resume_docx_2",
            "fmt3": "make_resume_docx_3",
            "fmt4": "make_resume_docx_4",
            "fmt5": "make_resume_docx_5",
        },
    )
    g.add_edge("make_resume_docx", "convert_docx_to_pdf")
    g.add_edge("write_email", "create_draft_with_gmail_auth")
    g.add_edge("create_draft_with_gmail_auth", END)
    return g.compile()


if __name__ == "__main__":
    # Optional: draw diagrams only when requested
    if os.environ.get("DRAW_GRAPHS"):
        build_getting_input_graph().get_graph().draw_mermaid_png(
            output_file_path="getting_input_graph.jpg"
        )
        build_process_request_graph().get_graph().draw_mermaid_png(
            output_file_path="process_request.jpg"
        )

    # Determine the most recent PDF in input/ lazily at runtime
    files = list(Path("input").glob("*.pdf"))
    first_pdf = str(min(files, key=lambda p: p.stat().st_mtime)) if files else None

    graph = build_main_graph()
    if os.environ.get("DRAW_GRAPHS"):
        graph.get_graph().draw_mermaid_png(output_file_path="graph.jpg")
    init_state = ModelState(file_path=first_pdf)
    output = graph.invoke(init_state)
    print(output)
