from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, LLM
import os

app = Flask(__name__)
CORS(app)

llm = LLM(
    model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.7
)

chat_agent = Agent(
    role="Helpful Assistant",
    goal="Answer user questions clearly and helpfully",
    backstory="You are a friendly, knowledgeable assistant who helps with any question the user asks.",
    llm=llm,
    verbose=False
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "Message khali hai"}), 400

    chat_task = Task(
        description=user_message,
        expected_output="A clear, helpful, and conversational response",
        agent=chat_agent
    )

    crew = Crew(
        agents=[chat_agent],
        tasks=[chat_task],
        verbose=False
    )

    result = crew.kickoff()

    return jsonify({"reply": str(result)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)