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

# Poori chat UI neeche is string mein hai (alag index.html ki zaroorat nahi)
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>AI Assistant</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>✨</text></svg>">
<style>
  :root {
    --bg: #0f1115; --panel: #161922; --border: #262b36; --text: #e8eaed; --muted: #9aa3b2;
    --accent: #10a37f; --accent-hover: #0e8f70; --code-bg: #0b0d12; --hover: #1d212b;
    --err-bg: #2d1819; --err-border: #6b2a2e; --shadow: 0 8px 30px rgba(0,0,0,.35);
  }
  @media (prefers-color-scheme: light) {
    :root {
      --bg: #f7f8fa; --panel: #ffffff; --border: #e3e6ec; --text: #1c1f26; --muted: #667085;
      --code-bg: #f3f4f7; --hover: #eef0f4; --err-bg: #fdecec; --err-border: #f1b3b3;
      --shadow: 0 8px 30px rgba(16,24,40,.08);
    }
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    display: flex; flex-direction: column; height: 100dvh; background: var(--bg); color: var(--text);
    font-family: Inter, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  button { font-family: inherit; }

  /* ---------- header ---------- */
  header {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 12px 20px; padding-top: calc(12px + env(safe-area-inset-top, 0px));
    background: var(--panel); border-bottom: 1px solid var(--border);
  }
  .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .logo {
    width: 36px; height: 36px; border-radius: 10px; flex: none; display: grid; place-items: center;
    background: linear-gradient(135deg, #10a37f, #0b7a9e); color: #fff;
  }
  .brand h1 { margin: 0; font-size: 15px; font-weight: 600; line-height: 1.2; }
  .status { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
  .ghost-btn {
    display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; font-size: 13px;
    color: var(--text); background: transparent; border: 1px solid var(--border); border-radius: 8px;
    cursor: pointer; transition: background .15s;
  }
  .ghost-btn:hover { background: var(--hover); }

  /* ---------- messages ---------- */
  #scroll { flex: 1; overflow-y: auto; scroll-behavior: smooth; }
  .wrap { max-width: 800px; margin: 0 auto; padding: 24px 16px 8px; }
  .row { scroll-margin-top: 12px; display: flex; gap: 12px; margin-bottom: 22px; animation: rise .25s ease-out; }
  @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  .row.user { justify-content: flex-end; }
  .bubble {
    max-width: 82%; padding: 10px 16px; background: var(--accent); color: #fff;
    border-radius: 18px 18px 4px 18px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere;
    font-size: 15px;
  }
  .avatar {
    width: 32px; height: 32px; border-radius: 50%; flex: none; display: grid; place-items: center;
    background: linear-gradient(135deg, #10a37f, #0b7a9e); color: #fff; margin-top: 2px;
  }
  .content { flex: 1; min-width: 0; font-size: 15px; line-height: 1.7; }
  .actions { display: flex; gap: 4px; margin-top: 6px; }
  .icon-btn {
    display: inline-flex; align-items: center; gap: 5px; padding: 4px 8px; font-size: 12px;
    color: var(--muted); background: transparent; border: 0; border-radius: 6px; cursor: pointer;
  }
  .icon-btn:hover { background: var(--hover); color: var(--text); }

  /* markdown */
  .md > :first-child { margin-top: 0; }
  .md > :last-child { margin-bottom: 0; }
  .md p { margin: 0 0 12px; }
  .md h1, .md h2, .md h3, .md h4, .md h5, .md h6 { margin: 20px 0 10px; line-height: 1.3; font-weight: 650; }
  .md h1 { font-size: 22px; } .md h2 { font-size: 19px; } .md h3 { font-size: 16.5px; }
  .md h4, .md h5, .md h6 { font-size: 15px; }
  .md ul, .md ol { margin: 0 0 12px; padding-left: 24px; }
  .md li { margin: 4px 0; }
  .md li > ul, .md li > ol { margin: 4px 0 0; }
  .md a { color: var(--accent); text-decoration: none; }
  .md a:hover { text-decoration: underline; }
  .md hr { border: 0; border-top: 1px solid var(--border); margin: 18px 0; }
  .md blockquote {
    margin: 0 0 12px; padding: 4px 14px; border-left: 3px solid var(--accent); color: var(--muted);
  }
  .md code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13.5px;
    background: var(--hover); padding: 2px 6px; border-radius: 5px;
  }
  .code { margin: 0 0 14px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--code-bg); }
  .code-head {
    display: flex; justify-content: space-between; align-items: center; padding: 6px 8px 6px 14px;
    font-size: 12px; color: var(--muted); background: var(--hover); border-bottom: 1px solid var(--border);
  }
  .code pre { margin: 0; padding: 14px; overflow-x: auto; }
  .code pre code { background: none; padding: 0; font-size: 13px; line-height: 1.6; color: var(--text); }
  .table-wrap { overflow-x: auto; margin: 0 0 14px; border: 1px solid var(--border); border-radius: 10px; }
  .md table { border-collapse: collapse; width: 100%; font-size: 14px; }
  .md th, .md td { padding: 9px 14px; text-align: left; border-bottom: 1px solid var(--border); }
  .md th { background: var(--hover); font-weight: 600; white-space: nowrap; }
  .md tr:last-child td { border-bottom: 0; }

  /* typing + error */
  .typing { display: flex; align-items: center; gap: 10px; padding-top: 6px; color: var(--muted); font-size: 13px; }
  .dots { display: inline-flex; gap: 4px; }
  .dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); animation: blink 1.2s infinite ease-in-out; }
  .dots i:nth-child(2) { animation-delay: .2s; } .dots i:nth-child(3) { animation-delay: .4s; }
  @keyframes blink { 0%, 80%, 100% { opacity: .25; transform: scale(.8); } 40% { opacity: 1; transform: scale(1); } }
  .errbox {
    display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 10px 14px; font-size: 14px;
    background: var(--err-bg); border: 1px solid var(--err-border); border-radius: 10px; overflow-wrap: anywhere;
  }
  .errbox button {
    padding: 5px 12px; font-size: 13px; color: var(--text); background: transparent;
    border: 1px solid var(--err-border); border-radius: 6px; cursor: pointer;
  }

  /* empty state */
  #empty { text-align: center; padding: 8vh 0 24px; }
  #empty .logo { width: 56px; height: 56px; border-radius: 16px; margin: 0 auto 18px; }
  #empty h2 { margin: 0 0 6px; font-size: 24px; font-weight: 650; }
  #empty p { margin: 0 0 28px; color: var(--muted); font-size: 15px; }
  .chips { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; text-align: left; }
  .chip {
    padding: 14px 16px; font-size: 14px; line-height: 1.4; text-align: left; color: var(--text); background: var(--panel);
    border: 1px solid var(--border); border-radius: 12px; cursor: pointer; transition: all .15s;
  }
  .chip:hover { background: var(--hover); border-color: var(--accent); transform: translateY(-1px); }
  .chip small { display: block; margin-top: 3px; color: var(--muted); font-size: 12px; }

  /* composer */
  footer { padding: 8px 16px; padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px)); }
  .composer {
    max-width: 800px; margin: 0 auto; display: flex; align-items: flex-end; gap: 8px; padding: 8px 8px 8px 16px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow);
    transition: border-color .15s;
  }
  .composer:focus-within { border-color: var(--accent); }
  textarea {
    flex: 1; resize: none; border: 0; outline: 0; background: transparent; color: var(--text);
    font: inherit; font-size: 16px; line-height: 1.5; padding: 8px 0; max-height: 180px;
  }
  textarea::placeholder { color: var(--muted); }
  #send {
    width: 38px; height: 38px; flex: none; display: grid; place-items: center; color: #fff;
    background: var(--accent); border: 0; border-radius: 10px; cursor: pointer; transition: background .15s;
  }
  #send:hover:not(:disabled) { background: var(--accent-hover); }
  #send:disabled { opacity: .4; cursor: not-allowed; }
  .hint { max-width: 800px; margin: 8px auto 0; text-align: center; font-size: 11.5px; color: var(--muted); }

  @media (max-width: 600px) {
    .chips { grid-template-columns: 1fr; }
    .bubble { max-width: 90%; }
    header { padding-left: 14px; padding-right: 14px; }
    .ghost-btn span { display: none; }
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="logo">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2zm7 11l.9 2.6L22.5 16l-2.6.9L19 19.5l-.9-2.6-2.6-.9 2.6-.9L19 13zM6 15l.9 2.6L9.5 18.5l-2.6.9L6 22l-.9-2.6L2.5 18.5l2.6-.9L6 15z"/></svg>
    </div>
    <div>
      <h1>AI Assistant</h1>
      <div class="status"><span class="dot"></span>Online</div>
    </div>
  </div>
  <button class="ghost-btn" id="newChat" title="Start a new chat">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    <span>New chat</span>
  </button>
</header>

<main id="scroll">
  <div class="wrap">
    <div id="empty">
      <div class="logo">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2zm7 11l.9 2.6L22.5 16l-2.6.9L19 19.5l-.9-2.6-2.6-.9 2.6-.9L19 13zM6 15l.9 2.6L9.5 18.5l-2.6.9L6 22l-.9-2.6L2.5 18.5l2.6-.9L6 15z"/></svg>
      </div>
      <h2>How can I help you today?</h2>
      <p>Ask me anything — coding, writing, research, ideas.</p>
      <div class="chips">
        <button class="chip" data-prompt="Explain Python in simple terms for a beginner">Explain Python<small>Simple, beginner-friendly overview</small></button>
        <button class="chip" data-prompt="Write a professional cover letter for a Java developer job">Write a cover letter<small>For a Java developer role</small></button>
        <button class="chip" data-prompt="Give me a 7-day study plan to learn SQL">Make a study plan<small>7 days to learn SQL</small></button>
        <button class="chip" data-prompt="Help me prepare for a software developer interview">Interview prep<small>Common questions &amp; tips</small></button>
      </div>
    </div>
    <div id="list"></div>
  </div>
</main>

<footer>
  <div class="composer">
    <textarea id="input" rows="1" placeholder="Message AI Assistant…" autocomplete="off" autofocus></textarea>
    <button id="send" title="Send" disabled>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    </button>
  </div>
  <div class="hint">Enter to send · Shift + Enter for a new line · AI can make mistakes, so verify important info.</div>
</footer>

<script>
/* ==MD START== */
function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function inline(t) {
  const codes = [];
  t = t.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
  t = esc(t);
  t = t.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>");
  t = t.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return t.replace(/\u0000(\d+)\u0000/g, (_, i) => "<code>" + esc(codes[+i]) + "</code>");
}

function codeBlock(lang, code) {
  return '<div class="code"><div class="code-head"><span>' + esc(lang || "code") +
    '</span><button class="icon-btn" data-copy="code">Copy</button></div><pre><code>' +
    esc(code) + "</code></pre></div>";
}

function buildList(items, i, indent) {
  const tag = items[i].ordered ? "ol" : "ul";
  let html = "<" + tag + ">";
  while (i < items.length && items[i].indent >= indent) {
    if (items[i].indent > indent) {
      const r = buildList(items, i, items[i].indent);
      html = html.endsWith("</li>") ? html.slice(0, -5) + r[0] + "</li>" : html + r[0];
      i = r[1];
      continue;
    }
    html += "<li>" + inline(items[i].text) + "</li>";
    i++;
  }
  return [html + "</" + tag + ">", i];
}

function md(src) {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  const out = [];
  let i = 0;
  const LI = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
  const HR = /^\s*([-*_])\1{2,}\s*$/;
  const isSep = l => l.includes("-") && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
  const cells = l => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
  const startsTable = k => lines[k].includes("|") && k + 1 < lines.length && isSep(lines[k + 1]);
  const isBlockStart = l => /^\s*(```|#{1,6}\s|>)/.test(l) || LI.test(l) || HR.test(l);

  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;

    if ((m = l.match(/^\s*```\s*([\w+#.-]*)/))) {
      const code = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
      i++;
      out.push(codeBlock(m[1], code.join("\n")));
      continue;
    }
    if ((m = l.match(/^(#{1,6})\s+(.*?)\s*#*\s*$/))) {
      const n = m[1].length;
      out.push("<h" + n + ">" + inline(m[2]) + "</h" + n + ">");
      i++;
      continue;
    }
    if (HR.test(l)) { out.push("<hr>"); i++; continue; }

    if (startsTable(i)) {
      const head = cells(l);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim() && lines[i].includes("|")) { rows.push(cells(lines[i])); i++; }
      out.push('<div class="table-wrap"><table><thead><tr>' +
        head.map(c => "<th>" + inline(c) + "</th>").join("") + "</tr></thead><tbody>" +
        rows.map(r => "<tr>" + head.map((_, k) => "<td>" + inline(r[k] || "") + "</td>").join("") + "</tr>").join("") +
        "</tbody></table></div>");
      continue;
    }
    if (/^\s*>/.test(l)) {
      const q = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) { q.push(lines[i].replace(/^\s*>\s?/, "")); i++; }
      out.push("<blockquote>" + md(q.join("\n")) + "</blockquote>");
      continue;
    }
    if (LI.test(l)) {
      const items = [];
      while (i < lines.length) {
        let k = i;
        if (!lines[k].trim()) {            // blank line inside a loose list
          while (k < lines.length && !lines[k].trim()) k++;
          if (k >= lines.length || !LI.test(lines[k])) break;
        }
        const mm = lines[k].match(LI);
        if (!mm) break;
        const ind = mm[1].replace(/\t/g, "    ").length, ord = /\d/.test(mm[2]);
        if (items.length && ind <= items[0].indent && ord !== items[0].ordered) break;  // bullet <-> numbered = new list
        items.push({ indent: ind, ordered: ord, text: mm[3] });
        i = k + 1;
      }
      out.push(buildList(items, 0, items[0].indent)[0]);
      continue;
    }

    const p = [];
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i]) && !startsTable(i)) { p.push(lines[i]); i++; }
    if (!p.length) { p.push(l); i++; }
    out.push("<p>" + p.map(inline).join("<br>") + "</p>");
  }
  return out.join("");
}
/* ==MD END== */

/* ---------- app ---------- */
const $ = s => document.querySelector(s);
const scroller = $("#scroll"), list = $("#list"), empty = $("#empty");
const input = $("#input"), sendBtn = $("#send");
const KEY = "chat_history_v1";
const SPARK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2z"/></svg>';
const COPY_ICON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg>';

let messages = [];
let busy = false;

function save() { try { localStorage.setItem(KEY, JSON.stringify(messages)); } catch (e) {} }
function load() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "[]");
    if (Array.isArray(v)) {
      messages = v.filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string");
    }
  } catch (e) {}
}

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}
function scrollDown() { scroller.scrollTop = scroller.scrollHeight; }
function updateEmpty() { empty.hidden = list.children.length > 0; }
function updateBtn() { sendBtn.disabled = busy || !input.value.trim(); }

function addRow(role, content) {
  const row = el("div", "row " + role);
  if (role === "user") {
    const b = el("div", "bubble");
    b.textContent = content;
    row.append(b);
  } else {
    const c = el("div", "content");
    c.dataset.raw = content;
    c.append(el("div", "md", md(content)));
    c.append(el("div", "actions", '<button class="icon-btn" data-copy="msg">' + COPY_ICON + " Copy</button>"));
    row.append(el("div", "avatar", SPARK), c);
  }
  list.append(row);
  updateEmpty();
  if (role === "user") scrollDown();
  else row.scrollIntoView({ block: "start" });   // long answer: start reading from the top
  return row;
}

function addTyping() {
  const row = el("div", "row bot");
  const c = el("div", "content");
  const t = el("div", "typing", '<span class="dots"><i></i><i></i><i></i></span><span class="label">Thinking…</span>');
  c.append(t);
  row.append(el("div", "avatar", SPARK), c);
  list.append(row);
  updateEmpty();
  scrollDown();
  row._timer = setTimeout(() => {
    t.querySelector(".label").textContent = "Still working… the server may be waking up, this can take a moment.";
  }, 8000);
  return row;
}

function addError(msg, text) {
  const row = el("div", "row bot");
  const c = el("div", "content");
  const box = el("div", "errbox");
  box.append(el("span", "", "⚠️ " + esc(msg)));
  const retry = el("button", "", "Retry");
  retry.onclick = () => {
    const userRow = row.previousElementSibling;
    row.remove();
    if (userRow && userRow.classList.contains("user")) userRow.remove();
    send(text);
  };
  box.append(retry);
  c.append(box);
  row.append(el("div", "avatar", SPARK), c);
  list.append(row);
  scrollDown();
}

async function send(text) {
  text = (text || "").trim();
  if (!text || busy) return;
  busy = true;
  updateBtn();

  const history = messages.slice(-20);
  addRow("user", text);
  messages.push({ role: "user", content: text });
  save();
  const typing = addTyping();

  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history })
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || "Server error (" + r.status + ")");
    clearTimeout(typing._timer);
    typing.remove();
    messages.push({ role: "assistant", content: data.reply });
    save();
    addRow("assistant", data.reply);
  } catch (e) {
    clearTimeout(typing._timer);
    typing.remove();
    messages.pop();
    save();
    const msg = e instanceof TypeError ? "Couldn't reach the server. Check your connection and try again." : e.message;
    addError(msg, text);
  } finally {
    busy = false;
    updateBtn();
    input.focus();
  }
}

function resize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 180) + "px";
}
function submit() {
  const t = input.value;
  input.value = "";
  resize();
  updateBtn();
  send(t);
}

async function copyText(t) {
  try { await navigator.clipboard.writeText(t); return true; } catch (e) {}
  const ta = document.createElement("textarea");
  ta.value = t; document.body.append(ta); ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (e) {}
  ta.remove();
  return ok;
}

document.addEventListener("click", async e => {
  const b = e.target.closest("[data-copy]");
  if (b) {
    const text = b.dataset.copy === "code"
      ? b.closest(".code").querySelector("code").textContent
      : b.closest(".content").dataset.raw;
    if (await copyText(text)) {
      const old = b.innerHTML;
      b.textContent = "Copied ✓";
      setTimeout(() => { b.innerHTML = old; }, 1500);
    }
    return;
  }
  const chip = e.target.closest(".chip");
  if (chip) send(chip.dataset.prompt);
});

input.addEventListener("input", () => { resize(); updateBtn(); });
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); }
});
sendBtn.addEventListener("click", submit);
$("#newChat").addEventListener("click", () => {
  if (busy) return;
  messages = [];
  save();
  list.innerHTML = "";
  updateEmpty();
  input.focus();
});

load();
messages.forEach(m => addRow(m.role === "user" ? "user" : "bot", m.content));
updateEmpty();
scroller.style.scrollBehavior = "auto"; scrollDown(); scroller.style.scrollBehavior = "";
</script>
</body>
</html>
"""


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
