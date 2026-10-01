import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)  # same-origin pe zaroorat nahi, par purane frontend ke liye rehne diya

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Pehla model try hoga, fail ho to agla. Env se badal sakte ho: OPENROUTER_MODEL
MODELS = list(dict.fromkeys(
    m for m in [
        os.getenv("OPENROUTER_MODEL"),
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "openrouter/free",
    ] if m
))

PER_MODEL_TIMEOUT = 40   # sec; gunicorn.conf.py ka timeout (120) isse bada rakha hai
MAX_TOKENS = 1024        # lambe jawab bhi time limit ke andar rahein

SYSTEM_PROMPT = (
    "You are a friendly, knowledgeable assistant who helps with any question "
    "the user asks. Answer clearly and helpfully. Reply in the same language "
    "the user writes in."
)

MAX_HISTORY = 20  # last itne messages hi model ko bhejte hain

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Chat Assistant</title>
<style>
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body { display: flex; flex-direction: column; background: #343541; color: #fff;
         font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
  #chat { flex: 1; overflow-y: auto; padding: 20px; }
  .msg { max-width: 75%; margin-bottom: 14px; padding: 12px 16px; border-radius: 10px;
         line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }
  .user { background: #10a37f; margin-left: auto; }
  .bot { background: #444654; margin-right: auto; }
  .err { background: #7a2e2e; margin-right: auto; }
  #bar { display: flex; gap: 10px; padding: 14px; background: #40414f; }
  #input { flex: 1; padding: 12px; border: 0; border-radius: 8px; outline: 0; font-size: 15px; }
  #send { padding: 12px 20px; background: #10a37f; border: 0; border-radius: 8px;
          color: #fff; font-size: 15px; cursor: pointer; }
  #send:disabled { opacity: .6; cursor: not-allowed; }
</style>
</head>
<body>
  <div id="chat"></div>
  <div id="bar">
    <input id="input" type="text" placeholder="Apna message likhein..." autocomplete="off" autofocus>
    <button id="send">Send</button>
  </div>
<script>
  const chat = document.getElementById("chat");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const history = [];

  function add(text, cls) {
    const d = document.createElement("div");
    d.className = "msg " + cls;
    d.textContent = text;           // textContent => XSS safe
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
  }

  async function send() {
    const text = input.value.trim();
    if (!text || sendBtn.disabled) return;
    input.value = "";
    add(text, "user");
    history.push({ role: "user", content: text });
    sendBtn.disabled = true;
    const wait = add("Soch raha hoon...", "bot");
    try {
      const r = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history.slice(0, -1) })
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || ("Server error " + r.status));
      wait.textContent = data.reply;
      history.push({ role: "assistant", content: data.reply });
    } catch (e) {
      wait.className = "msg err";
      wait.textContent = "Error: " + e.message;
      history.pop();               // fail hua message history se hata do
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", e => { if (e.key === "Enter") send(); });
  add("Namaste! Mujhse kuch bhi poochiye.", "bot");
</script>
</body>
</html>"""


@app.route("/")
def home():
    return Response(HTML, mimetype="text/html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(os.getenv("OPENROUTER_API_KEY")),
    })


@app.route("/chat", methods=["POST"])
def chat():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({
            "error": "OPENROUTER_API_KEY set nahi hai. Render > Environment mein add karein."
        }), 500

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message khali hai"}), 400

    # client se aayi history sanitize karo
    history = []
    for m in (data.get("history") or [])[-MAX_HISTORY:]:
        if (
            isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
        ):
            history.append({"role": m["role"], "content": m["content"]})

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": user_message}]
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = "Unknown error"
    for model in MODELS:
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json={"model": model, "messages": messages,
                      "temperature": 0.7, "max_tokens": MAX_TOKENS},
                timeout=PER_MODEL_TIMEOUT,
            )
            body = resp.json() if resp.content else {}
            if resp.status_code != 200:
                detail = (body.get("error") or {}).get("message") or resp.text[:300]
                last_error = f"{model}: {resp.status_code} {detail}"
                app.logger.error("OpenRouter error -> %s", last_error)
                continue
            reply = body["choices"][0]["message"]["content"]
            if not reply:
                last_error = f"{model}: khali jawab aaya"
                continue
            return jsonify({"reply": reply, "model": model})
        except Exception as e:  # network / timeout / bad json
            last_error = f"{model}: {e}"
            app.logger.exception("Chat request failed")

    return jsonify({"error": f"AI se jawab nahi mila. {last_error}"}), 502


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
