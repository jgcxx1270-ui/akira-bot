# akira_brain.py
import os, json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEM_DIR = Path("mem_users")
MEM_DIR.mkdir(exist_ok=True)
HISTORY_LIMIT = 6  # turnos recientes por usuario

def _mem_file(user_id: str) -> Path:
    safe = "".join(c for c in user_id if c.isdigit() or c in "+-_")
    return MEM_DIR / f"{safe}.json"

def load_user_state(user_id: str):
    f = _mem_file(user_id)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "memory": {"user_name": None, "likes": [], "facts": []},
        "history": []  # [("user","..."),("assistant","...")]
    }

def save_user_state(user_id: str, state: dict):
    _mem_file(user_id).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def _handle_commands(state: dict, msg_lower: str):
    mem = state["memory"]
    # me llamo ...
    if msg_lower.startswith("me llamo"):
        name = msg_lower.replace("me llamo", "", 1).strip()
        if name:
            mem["user_name"] = name
            return "¡Mucho gusto, {}! 🐶💙 Lo guardo.".format(name)
        return "¿Cómo te llamas? 😄"

    # me gusta ...
    if "me gusta" in msg_lower:
        like = msg_lower.split("me gusta", 1)[-1].strip()
        if like:
            mem["likes"].append(like)
            return f"¡Anotado! Te gusta {like}. 😄"

    # qué me gusta
    if "qué me gusta" in msg_lower or "que me gusta" in msg_lower:
        likes = mem["likes"]
        return ("Te gusta: " + ", ".join(likes) + " 🐾") if likes else "Aún no me dijiste tus gustos 😅"

    # recuerda que ...
    if msg_lower.startswith("recuerda que"):
        fact = msg_lower.replace("recuerda que", "", 1).strip(": ").strip()
        if fact:
            mem["facts"].append(fact)
            return "¡Listo! Lo guardo en mi memoria 🐾"
        return "¿Qué quieres que recuerde?"

    # olvida ...
    if msg_lower.startswith("olvida"):
        key = msg_lower.replace("olvida", "", 1).strip(": ").strip()
        if key:
            mem["facts"] = [f for f in mem["facts"] if key not in f]
            mem["likes"] = [l for l in mem["likes"] if key not in l]
            return "Hecho. Lo he olvidado 🫡"
        return "Dime qué debería olvidar."

    return None

def akira_reply(user_id: str, msg: str) -> str:
    state = load_user_state(user_id)
    mem = state["memory"]

    # 1) comandos locales (sin gastar API)
    cmd = _handle_commands(state, msg.lower())
    if cmd:
        state["history"].append(("user", msg))
        state["history"].append(("assistant", cmd))
        save_user_state(user_id, state)
        return cmd

    # 2) sistema + memoria
    mem_summary = []
    if mem.get("user_name"): mem_summary.append(f"Nombre del usuario: {mem['user_name']}")
    if mem.get("likes"): mem_summary.append("Gustos del usuario: " + ", ".join(mem["likes"]))
    if mem.get("facts"): mem_summary.append("Hechos guardados: " + "; ".join(mem["facts"]))

    system_prompt = (
        "Eres Akira, una mascota IA leal, alegre y curiosa 🐾. "
        "Tono cercano, empático y útil; explica paso a paso si es técnico. "
        "No inventes datos; si no sabes, dilo y propone opciones."
    )
    if mem_summary:
        system_prompt += "\n\nMemoria del usuario:\n" + "\n".join(mem_summary)

    # 3) contexto reciente
    recent = state["history"][-(HISTORY_LIMIT*2):]
    chat_msgs = [{"role": ("user" if r=="user" else "assistant"), "content": c} for r, c in recent]

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt}]
                     + chat_msgs
                     + [{"role":"user","content":msg}],
            temperature=0.6,
        )
        texto = resp.choices[0].message.content
    except Exception as e:
        texto = f"Ups… tuve un problema con mi conexión 🤕 ({e})"

    # 4) guardar historial
    state["history"].append(("user", msg))
    state["history"].append(("assistant", texto))
    save_user_state(user_id, state)
    return texto
