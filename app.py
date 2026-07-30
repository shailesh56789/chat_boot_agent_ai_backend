# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from dotenv import load_dotenv
# load_dotenv()

# from crewai import Agent, Task, Crew, LLM
# import os

# app = Flask(__name__)
# CORS(app)


# @app.route("/")
# def home():
#     return jsonify({
#         "status": "API Running",
#         "message": "Use POST /chat"
#     })


# llm = LLM(
#     model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
#     api_key=os.getenv("OPENROUTER_API_KEY"),
#     temperature=0.7
# )

# chat_agent = Agent(
#     role="Helpful Assistant",
#     goal="Answer user questions clearly and helpfully",
#     backstory="You are a friendly, knowledgeable assistant who helps with any question the user asks.",
#     llm=llm,
#     verbose=False
# )

# @app.route("/chat", methods=["POST"])
# def chat():
#     data = request.get_json()
#     user_message = data.get("message", "")

#     if not user_message:
#         return jsonify({"error": "Message khali hai"}), 400

#     chat_task = Task(
#         description=user_message,
#         expected_output="A clear, helpful, and conversational response",
#         agent=chat_agent
#     )

#     crew = Crew(
#         agents=[chat_agent],
#         tasks=[chat_task],
#         verbose=False
#     )

#     result = crew.kickoff()

#     return jsonify({"reply": str(result)})

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)




from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
import os
import requests

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route("/")
def home():
    return jsonify({
        "status": "API Running",
        "message": "Use POST /chat"
    })

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"error": "Message khali hai"}), 400

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": [
            {
                "role": "system",
                "content": "You are a friendly, knowledgeable assistant who helps with any question the user asks. Answer clearly and helpfully."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
