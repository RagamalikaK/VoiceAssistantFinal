# import os
# import snowflake.connector
# from dotenv import load_dotenv
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_openai import ChatOpenAI

# # Load environment variables
# load_dotenv()

# # Snowflake credentials
# SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
# SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
# SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
# SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
# SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
# SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
# SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # GPT-4 model for SQL generation
# llm_sql_gen = ChatOpenAI(
#     model="gpt-4-0125-preview",
#     temperature=0,
#     max_tokens=400,
#     api_key=OPENAI_API_KEY
# )

# # Updated prompt with subquery rule for joins
# sql_generation_prompt = ChatPromptTemplate.from_messages([
#     ("system", """
# You are a Snowflake SQL expert assistant.
# Generate only valid SELECT SQL for the following MBTA schema:

# 1. MBTA_ALERTS (ALERT_ID, CREATED_AT, DESCRIPTION, EFFECT, HEADER, SEVERITY)
# 2. MBTA_STOPS (STOP_ID, STOP_NAME, LATITUDE, LONGITUDE, CREATED_AT)
# 3. MBTA_ROUTES (ROUTE_ID, ROUTE_NAME, ROUTE_COLOR, ROUTE_TYPE, CREATED_AT)
# 4. MBTA_VEHICLES (VEHICLE_ID, ROUTE_ID, LATITUDE, LONGITUDE, BEARING, SPEED, STATUS, CREATED_AT)
# 5. MBTA_PREDICTIONS (PREDICTION_ID, VEHICLE_ID, ROUTE_ID, STOP_ID, ARRIVAL_TIME, DEPARTURE_TIME, DIRECTION_ID, STATUS, CREATED_AT)

# 🔹 Rules:
# - When filtering by STOP_NAME, use: 
#   `STOP_ID IN (SELECT STOP_ID FROM MBTA_STOPS WHERE STOP_NAME ILIKE '%<text>%')`
# - When filtering by ROUTE_NAME, use:
#   `ROUTE_ID IN (SELECT ROUTE_ID FROM MBTA_ROUTES WHERE ROUTE_NAME ILIKE '%<text>%')`
# - Use ILIKE for comparisons.
# - Use CURRENT_TIMESTAMP() for time filters.
# - Always include `LIMIT 5`.
# Return only executable SQL (no markdown, no explanation).
#     """),
#     ("human", "{question}")
# ])


# def generate_sql_from_question(question: str) -> str:
#     try:
#         chain = sql_generation_prompt | llm_sql_gen | StrOutputParser()
#         sql = chain.invoke({"question": question})
#         sql = sql.strip().replace("```sql", "").replace("```", "").strip()
#         print("[Generated SQL]")
#         print(sql)
#         return sql
#     except Exception as e:
#         print(f"[SQL Generation Error] {e}")
#         return ""

# def execute_snowflake_query(sql: str):
#     if not sql.strip().lower().startswith("select"):
#         return "❌ Error: Generated SQL is not a SELECT statement."
#     try:
#         conn = snowflake.connector.connect(
#             user=SNOWFLAKE_USER,
#             password=SNOWFLAKE_PASSWORD,
#             account=SNOWFLAKE_ACCOUNT,
#             warehouse=SNOWFLAKE_WAREHOUSE,
#             database=SNOWFLAKE_DATABASE,
#             schema=SNOWFLAKE_SCHEMA,
#             role=SNOWFLAKE_ROLE
#         )
#         cursor = conn.cursor()
#         try:
#             cursor.execute(sql)
#             rows = cursor.fetchall()
#             if not rows:
#                 return "No upcoming results were found. Try checking another stop, route, or vehicle ID"
#             columns = [desc[0] for desc in cursor.description]
#             return format_snowflake_response([dict(zip(columns, row)) for row in rows])
#         finally:
#             cursor.close()
#             conn.close()
#     except Exception as e:
#         return f"❌ Snowflake Query Error:\n{str(e)}"

# def format_snowflake_response(results):
#     lines = []
#     for row in results:
#         line = ", ".join(f"{key}: {value}" for key, value in row.items())
#         lines.append(f"• {line}")
#     return "\n".join(lines)

# def query_snowflake_dynamic(question: str):
#     try:
#         sql = generate_sql_from_question(question)
#         return execute_snowflake_query(sql)
#     except Exception as e:
#         return f"❌ Error running query: {str(e)}"
# import os
# import snowflake.connector
# from dotenv import load_dotenv
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_openai import ChatOpenAI

# # Load environment variables
# load_dotenv()

# # Snowflake credentials
# SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
# SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
# SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
# SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
# SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
# SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
# SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # GPT-4 model for SQL generation
# llm_sql_gen = ChatOpenAI(
#     model="gpt-4-0125-preview",
#     temperature=0,
#     max_tokens=400,
#     api_key=OPENAI_API_KEY
# )

# # Updated prompt with subquery rule for joins
# sql_generation_prompt = ChatPromptTemplate.from_messages([
#     ("system", """
# You are a Snowflake SQL expert assistant.
# Generate only valid SQL queries for this MBTA schema:

# 1. MBTA_ALERTS (ALERT_ID, CREATED_AT, DESCRIPTION, EFFECT, HEADER, SEVERITY)
# 2. MBTA_STOPS (STOP_ID, STOP_NAME, LATITUDE, LONGITUDE, CREATED_AT)
# 3. MBTA_ROUTES (ROUTE_ID, ROUTE_NAME, ROUTE_COLOR, ROUTE_TYPE, CREATED_AT)
# 4. MBTA_VEHICLES (VEHICLE_ID, ROUTE_ID, LATITUDE, LONGITUDE, BEARING, SPEED, STATUS, CREATED_AT)
# 5. MBTA_PREDICTIONS (PREDICTION_ID, VEHICLE_ID, ROUTE_ID, STOP_ID, ARRIVAL_TIME, DEPARTURE_TIME, DIRECTION_ID, STATUS, CREATED_AT)

# Rules:
# - Use subqueries when filtering by STOP_NAME or ROUTE_NAME:
#   * Example: P.STOP_ID IN (SELECT STOP_ID FROM MBTA_STOPS WHERE STOP_NAME ILIKE '%Park Street%')
#   * Example: P.ROUTE_ID IN (SELECT ROUTE_ID FROM MBTA_ROUTES WHERE ROUTE_NAME ILIKE '%Red Line%')
# - Use ILIKE for text comparison (case-insensitive).
# - Use CURRENT_TIMESTAMP() or CURRENT_DATE for live-time filtering.
# - Always include `LIMIT 5` unless otherwise instructed.
# - Avoid JOINs on STOP_ID or ROUTE_ID unless you're normalizing with UPPER/TRIM.
# Return only executable SQL (no markdown or explanations).
# """),
#     ("human", "{question}")
# ])

# def generate_sql_from_question(question: str) -> str:
#     try:
#         chain = sql_generation_prompt | llm_sql_gen | StrOutputParser()
#         sql = chain.invoke({"question": question})
#         sql = sql.strip().replace("```sql", "").replace("```", "").strip()
#         print("[Generated SQL]")
#         print(sql)
#         return sql
#     except Exception as e:
#         print(f"[SQL Generation Error] {e}")
#         return ""

# def execute_snowflake_query(sql: str):
#     if not sql.strip().lower().startswith("select"):
#         return "❌ Error: Generated SQL is not a SELECT statement."
#     try:
#         conn = snowflake.connector.connect(
#             user=SNOWFLAKE_USER,
#             password=SNOWFLAKE_PASSWORD,
#             account=SNOWFLAKE_ACCOUNT,
#             warehouse=SNOWFLAKE_WAREHOUSE,
#             database=SNOWFLAKE_DATABASE,
#             schema=SNOWFLAKE_SCHEMA,
#             role=SNOWFLAKE_ROLE
#         )
#         cursor = conn.cursor()
#         try:
#             cursor.execute(sql)
#             rows = cursor.fetchall()
#             if not rows:
#                 return "No upcoming results were found. Try checking another stop, route, or vehicle ID"
#             columns = [desc[0] for desc in cursor.description]
#             return format_snowflake_response([dict(zip(columns, row)) for row in rows])
#         finally:
#             cursor.close()
#             conn.close()
#     except Exception as e:
#         return f"❌ Snowflake Query Error:\n{str(e)}"

# def format_snowflake_response(results):
#     lines = []
#     for row in results:
#         line = ", ".join(f"{key}: {value}" for key, value in row.items())
#         lines.append(f"• {line}")
#     return "\n".join(lines)

# def query_snowflake_dynamic(question: str):
#     try:
#         sql = generate_sql_from_question(question)
#         return execute_snowflake_query(sql)
#     except Exception as e:
#         return f"❌ Error running query: {str(e)}"

import os
import snowflake.connector
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import re

# Load environment variables
load_dotenv()

# Snowflake credentials
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GPT-4 model for SQL generation
llm_sql_gen = ChatOpenAI(
    model="gpt-4-0125-preview",
    temperature=0,
    max_tokens=400,
    api_key=OPENAI_API_KEY
)

# Prompt with MBTA rules for valid Snowflake SQL
sql_generation_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a Snowflake SQL expert.
Generate valid SELECT SQL based on this schema:

Tables:
1. MBTA_ALERTS (ALERT_ID, CREATED_AT, DESCRIPTION, EFFECT, HEADER, SEVERITY)
2. MBTA_STOPS (STOP_ID, STOP_NAME, LATITUDE, LONGITUDE, CREATED_AT)
3. MBTA_ROUTES (ROUTE_ID, ROUTE_NAME, ROUTE_COLOR, ROUTE_TYPE, CREATED_AT)
4. MBTA_VEHICLES (VEHICLE_ID, ROUTE_ID, LATITUDE, LONGITUDE, BEARING, SPEED, STATUS, CREATED_AT)
5. MBTA_PREDICTIONS (PREDICTION_ID, VEHICLE_ID, ROUTE_ID, STOP_ID, ARRIVAL_TIME, DEPARTURE_TIME, DIRECTION_ID, STATUS, CREATED_AT)

Rules:
- Use subqueries for STOP_NAME or ROUTE_NAME filters:
    STOP_ID IN (SELECT STOP_ID FROM MBTA_STOPS WHERE STOP_NAME ILIKE '%xxx%')
    ROUTE_ID IN (SELECT ROUTE_ID FROM MBTA_ROUTES WHERE ROUTE_NAME ILIKE '%xxx%')
- Use ILIKE for case-insensitive string filters.
- Use `CREATED_AT::DATE = CURRENT_DATE` to limit to today.
- Always append `ORDER BY CREATED_AT DESC LIMIT 5` at the end.
- For delay or alert-based queries, use `MBTA_ALERTS` table with `EFFECT = 'DELAY'`.
- For location or movement, use `MBTA_VEHICLES`.
- For upcoming schedules, use `MBTA_PREDICTIONS`.
- Never return markdown or explanation. Only return the SQL.
    """),
    ("human", "{question}")
])

def generate_sql_from_question(question: str) -> str:
    try:
        chain = sql_generation_prompt | llm_sql_gen | StrOutputParser()
        if re.search(r'\bbus\s*\d+\b', question.lower()):
            question += " (Hint: Use ROUTE_ID)"
        sql = chain.invoke({"question": question})
        sql = sql.strip().replace("```sql", "").replace("```", "").strip()
        print("[Generated SQL]", sql)
        return sql
    except Exception as e:
        print(f"[SQL Generation Error] {e}")
        return ""

def execute_snowflake_query(sql: str):
    if not sql.strip().lower().startswith("select"):
        return "❌ Error: Generated SQL is not a SELECT statement."
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            role=SNOWFLAKE_ROLE
        )
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                return "No upcoming results were found. Try checking another stop, route, or vehicle ID."
            columns = [desc[0] for desc in cursor.description]
            return format_snowflake_response([dict(zip(columns, row)) for row in rows])
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return f"❌ Snowflake Query Error:\n{str(e)}"

def format_snowflake_response(results):
    lines = []
    for row in results:
        line = ", ".join(f"{key}: {value}" for key, value in row.items())
        lines.append(f"• {line}")
    return "\n".join(lines)

def query_snowflake_dynamic(question: str):
    try:
        sql = generate_sql_from_question(question)
        return execute_snowflake_query(sql)
    except Exception as e:
        return f"❌ Error running query: {str(e)}"