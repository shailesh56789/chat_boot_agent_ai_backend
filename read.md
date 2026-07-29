Naya main.py (Chat Version)

Poori file ko is code se replace karein:

python
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, LLM
import os

# LLM setup
llm = LLM(
    model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.7
)

# Agent define karein - ab general chat assistant
chat_agent = Agent(
    role="Helpful Assistant",
    goal="Answer user questions clearly and helpfully",
    backstory="You are a friendly, knowledgeable assistant who helps with any question the user asks.",
    llm=llm,
    verbose=False   # False rakha taake thinking process na dikhe, sirf answer aaye
)

print("🤖 AI Chat Assistant Shuru Ho Gaya!")
print("Baat karne ke liye kuch bhi type karein. Band karne ke liye 'exit' ya 'quit' likhein.\n"
# Chat loop - jab tak user 'exit' na likhe
while True:
    user_input = input("Aap: ")

    if user_input.lower() in ["exit", "quit", "bye"]:
        print("🤖 Assistant: Alvida! Phir milte hain 👋")
        break

    # Task banayein user ke message ke saath
    chat_task = Task(
        description=user_input,
        expected_output="A clear, helpful, and conversational response",
        agent=chat_agent
    )

    crew = Crew(
        agents=[chat_agent],
        tasks=[chat_task],
        verbose=False
    )

    result = crew.kickoff()

    print(f"🤖 Assistant: {result}\n")
Kya Change Hua (Explanation)
Purana Code	Naya Code
Fixed topic tha	input() se user ka message live liya jata hai
Ek hi baar chalta tha	while True: loop se baar baar chalta hai
verbose=True	verbose=False — taake sirf clean answer dikhe, agent ka internal thinking na dikhe
Sirf tweet writer	General purpose "Helpful Assistant"
Koi exit nahi tha	"exit"/"quit"/"bye" likhne se chat band ho jayegi
Run Karein
bash
python main.py
Kaisa Dikhega
🤖 AI Chat Assistant Shuru Ho Gaya!
Baat karne ke liye kuch bhi type karein. Band karne ke liye 'exit' ya 'quit' likhein.

Aap: Pakistan ka capital kya hai?
🤖 Assistant: Pakistan ka capital Islamabad hai.

Aap: mujhe ek chota poem likh do dosti par
🤖 Assistant: [poem yahan aayega]

Aap: exit
🤖 Assistant: Alvida! Phir milte hain 👋

⚠️ Note: Har message OpenRouter ko ek naya API call bhejta hai, aur free tier mein rate limits hote hain (kuch requests per minute/day) — agar bohot fast messages bhejenge to kabhi kabhi "rate limit" error aa sakta hai, thoda ruk kar dobara try karein.

Save karke run karein aur chat karke dekhein!






https://openrouter.ai/workspaces/default/keys

https://artificialanalysis.ai/

https://www.promptingguide.ai/