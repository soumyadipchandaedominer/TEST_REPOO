# llm_service.py
# Only call LLM
# Return only generated SQL (nothing else)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from db_service import (
    load_metadata,
    set_table_name,
    set_business_rules,
    build_final_schema_description,
)

app = Flask(__name__)
CORS(app)


#  -------- INITIAL SETUP ----------
# Load metadata.json at startup
load_metadata("D:\\sql_prompt\\test5.json")

# Set static table name
set_table_name("your_static_table_name") #to be replaced with actual table name

# Set predefined business rules
set_business_rules([
    "Always compute totals using row-level numeric fields such as INVVALUE, TAXABLEVALUE, QTY, IGST, CGST, SGST, etc.",
    "Never sum pre-aggregated or invoice-level totals such as TOTALSALES, TOTALTAXABLEVALUE, or TOTALAMT.",
    "For total sales, always use SUM(INVVALUE) unless the user explicitly specifies a different column.",
    "When invoice data contains repeated total values, ignore repeated totals and compute from atomic row amounts.",
    "When ambiguous, default to the row-level numeric source, not any summary field."
])


# ---------- LLM SQL GENERATOR ----------
def generate_sql_query(frontend_schema, question):
    schema_description = build_final_schema_description(frontend_schema)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    sql_prompt = """
You are an expert SQL generator.

Use the combined schema + metadata + business rules:

{schema}

User Question:
{question}

Return ONLY a valid SQL query ending with a semicolon.
No explanation. No markdown.
"""

    prompt = PromptTemplate.from_template(sql_prompt)
    chain = prompt | llm

    raw = chain.invoke({
        "schema": schema_description,
        "question": question
    })

    text = raw.content if hasattr(raw, "content") else str(raw)

    # Extract SQL
    match = re.search(r"(SELECT[\s\S]*?;)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return text.strip()

# ---------- API ----------
@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.json
    frontend_schema = data.get("schema", "")
    question = data.get("question", "")
    sql = generate_sql_query(frontend_schema, question)
    return jsonify({"sql": sql})


if __name__ == "__main__":
    app.run(port=5001, debug=True)