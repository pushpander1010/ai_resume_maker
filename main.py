from langgraph.graph import StateGraph, START, END
from models import ModelState
from tools import read_pdf,write_email,write_referral,get_answers,is_email_in_jd,find_missing,ask_questions,create_draft_with_gmail_auth,fill_details,make_resume_docx,get_jd,fill_jd,jd_provided,resume_improvements,convert_docx_to_pdf
from dotenv import load_dotenv
from langchain_core.runnables.graph_mermaid import MermaidDrawMethod
from pathlib import Path

files = list(Path("input").glob("*.pdf"))
first_pdf=""
first_pdf = str(min(files, key=lambda p: p.stat().st_mtime))


#Breakdown for frontend
getting_input_graph=StateGraph(state_schema=ModelState)
getting_input_graph.add_node("read_pdf", read_pdf)
getting_input_graph.add_node("fill_jd", fill_jd)
getting_input_graph.add_node("get_jd",get_jd)
getting_input_graph.add_node("find_missing", find_missing)
getting_input_graph.add_node("ask_questions", ask_questions)
getting_input_graph.add_edge(START,"read_pdf")
getting_input_graph.add_edge(START,"get_jd")
getting_input_graph.add_edge("get_jd", "fill_jd")
getting_input_graph.add_edge("read_pdf", "find_missing")
getting_input_graph.add_edge("find_missing", "ask_questions")
getting_input_graph.add_edge("ask_questions",END)
getting_input_graph=getting_input_graph.compile()
getting_input_graph.get_graph().draw_mermaid_png(output_file_path="getting_input_graph.jpg")


process_request=StateGraph(state_schema=ModelState)
process_request.add_node("get_answers", get_answers)
process_request.add_node("make_resume_docx", make_resume_docx)
process_request.add_node("resume_improvements", resume_improvements,defer=True,)
process_request.add_node("create_draft_with_gmail_auth", create_draft_with_gmail_auth)
process_request.add_node("convert_docx_to_pdf",convert_docx_to_pdf)
process_request.add_node("write_email",write_email)
process_request.add_node("write_referral",write_referral)
process_request.add_node("fill_details", fill_details)


process_request.add_conditional_edges("convert_docx_to_pdf",is_email_in_jd,{
    "email_present":"write_email",
    "email_absent":"write_referral"
})
process_request.add_edge(START,"resume_improvements")
process_request.add_edge("resume_improvements","fill_details")
process_request.add_edge("fill_details","make_resume_docx")
process_request.add_edge("make_resume_docx","convert_docx_to_pdf")
#graph.add_edge("convert_docx_to_pdf","write_email")
process_request.add_edge("write_email","create_draft_with_gmail_auth")
process_request.add_edge("create_draft_with_gmail_auth",END)

process_request=process_request.compile()
process_request.get_graph().draw_mermaid_png(output_file_path="process_request.jpg")




# --- Create LangGraph ---
graph = StateGraph(state_schema=ModelState)



graph.add_node("read_pdf", read_pdf)
graph.add_node("get_jd",get_jd)
graph.add_node("fill_details", fill_details)
graph.add_node("fill_jd", fill_jd)
graph.add_node("find_missing", find_missing)
graph.add_node("ask_questions", ask_questions)
graph.add_node("get_answers", get_answers)
graph.add_node("make_resume_docx", make_resume_docx)
graph.add_node("resume_improvements", resume_improvements,defer=True,)
graph.add_node("create_draft_with_gmail_auth", create_draft_with_gmail_auth)
graph.add_node("convert_docx_to_pdf",convert_docx_to_pdf)
graph.add_node("write_email",write_email)
graph.add_node("write_referral",write_referral)

graph.add_edge(START,"read_pdf")
graph.add_edge(START,"get_jd")
graph.add_conditional_edges("get_jd",jd_provided,{True:"fill_jd",False:"get_jd"})
graph.add_edge("read_pdf", "find_missing")
graph.add_edge("find_missing", "ask_questions")
graph.add_edge("ask_questions","get_answers")
# graph.add_edge("fill_jd","resume_improvements")
# graph.add_edge("ask_questions","resume_improvements")
graph.add_conditional_edges("convert_docx_to_pdf",is_email_in_jd,{
    "email_present":"write_email",
    "email_absent":"write_referral"
})
graph.add_edge(["fill_jd","get_answers"],"resume_improvements")
graph.add_edge("resume_improvements","fill_details")
graph.add_edge("fill_details","make_resume_docx")
graph.add_edge("make_resume_docx","convert_docx_to_pdf")
#graph.add_edge("convert_docx_to_pdf","write_email")
graph.add_edge("write_email","create_draft_with_gmail_auth")
graph.add_edge("create_draft_with_gmail_auth",END)

if __name__=="__main__":
    graph = graph.compile()
    graph.get_graph().draw_mermaid_png(output_file_path="graph.jpg")
    init_state=ModelState(file_path=first_pdf)
    output=graph.invoke(init_state)
    print(output)
