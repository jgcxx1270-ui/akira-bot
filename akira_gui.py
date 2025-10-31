# akira_gui.py — Akira con OpenAI + Memoria + Animaciones

import os, random, json
from pathlib import Path

import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

from dotenv import load_dotenv
from openai import OpenAI

# ================== Config OpenAI ==================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ================== Memoria ==================
MEM_FILE = Path("akira_memory.json")
HISTORY_LIMIT = 8  # pares user/assistant recientes para el contexto

# ================== “Cerebro” de Akira ==================
class AkiraBrain:
    def __init__(self):
        self.memory = self._load_memory()
        self.history = []  # lista de tuplas: [("user", msg), ("assistant", msg), ...]

    # -------- Persistencia --------
    def _load_memory(self):
        if MEM_FILE.exists():
            try:
                return json.loads(MEM_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"user_name": None, "likes": [], "facts": []}

    def _save_memory(self):
        try:
            MEM_FILE.write_text(
                json.dumps(self.memory, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    # -------- Comandos locales (no gastan API) --------
    def _handle_commands(self, msg_lower):
        # me llamo ...
        if msg_lower.startswith("me llamo"):
            nombre = msg_lower.replace("me llamo", "", 1).strip()
            if nombre:
                self.memory["user_name"] = nombre
                self._save_memory()
                return (f"¡Mucho gusto, {nombre}! 🐶💙 Lo guardo.", "happy")

        # me gusta ...
        if "me gusta" in msg_lower:
            gusto = msg_lower.split("me gusta", 1)[-1].strip()
            if gusto:
                self.memory["likes"].append(gusto)
                self._save_memory()
                return (f"¡Anotado! Te gusta {gusto}. 😄", "happy")

        # qué me gusta
        if "qué me gusta" in msg_lower or "que me gusta" in msg_lower:
            likes = self.memory["likes"]
            if likes:
                return (f"Hasta ahora me dijiste que te gusta: {', '.join(likes)} 🐾", "happy")
            return ("Aún no me dijiste tus gustos 😅", "neutral")

        # recuerda que ...
        if msg_lower.startswith("recuerda que"):
            dato = msg_lower.replace("recuerda que", "", 1).strip(": ").strip()
            if dato:
                self.memory["facts"].append(dato)
                self._save_memory()
                return ("¡Listo! Lo guardo en mi memoria 🐾", "happy")
            return ("¿Qué quieres que recuerde exactamente?", "neutral")

        # olvida ...
        if msg_lower.startswith("olvida"):
            dato = msg_lower.replace("olvida", "", 1).strip(": ").strip()
            if dato:
                self.memory["facts"] = [f for f in self.memory["facts"] if dato not in f]
                self.memory["likes"] = [l for l in self.memory["likes"] if dato not in l]
                self._save_memory()
                return ("Hecho. Lo he olvidado 🫡", "neutral")
            return ("Dime qué debería olvidar.", "neutral")

        return None  # no es comando

    # -------- LLM --------
    def responder(self, msg: str):
        msg_lower = msg.lower()

        # 1) comandos locales primero
        cmd = self._handle_commands(msg_lower)
        if cmd:
            self.history.append(("user", msg))
            self.history.append(("assistant", cmd[0]))
            return cmd

        # 2) preparar system + contexto con memoria
        mem_summary = []
        if self.memory.get("user_name"):
            mem_summary.append(f"Nombre del usuario: {self.memory['user_name']}")
        if self.memory.get("likes"):
            mem_summary.append("Gustos del usuario: " + ", ".join(self.memory["likes"]))
        if self.memory.get("facts"):
            mem_summary.append("Hechos guardados: " + "; ".join(self.memory["facts"]))

        system_prompt = (
            "Eres Akira, una mascota IA leal, alegre y curiosa 🐾. "
            "Tono cercano, empático y útil. Explica paso a paso si es técnico. "
            "No inventes datos: si no sabes algo, dilo y propone opciones."
        )
        if mem_summary:
            system_prompt += "\n\nMemoria del usuario:\n" + "\n".join(mem_summary)

        # 3) últimos turnos
        recent = self.history[-(HISTORY_LIMIT*2):]
        chat_msgs = []
        for role, content in recent:
            chat_msgs.append(
                {"role": "user" if role == "user" else "assistant", "content": content}
            )

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}]
                         + chat_msgs
                         + [{"role": "user", "content": msg}],
                temperature=0.6,
            )
            texto = resp.choices[0].message.content

            # guardar historial
            self.history.append(("user", msg))
            self.history.append(("assistant", texto))

            # elegir estado visual simple según el input del user
            if any(p in msg_lower for p in ["feliz","lo logré","logre","me salió","me salio","contento","contenta"]):
                return (texto, "happy")
            if any(p in msg_lower for p in ["triste","mal","depre","deprimid"]):
                return (texto, "sad")
            if any(p in msg_lower for p in ["adiós","adios","chao","bye","nos vemos"]):
                return (texto, "bye")
            return (texto, "neutral")

        except Exception as e:
            return (f"Ups… tuve un problema con mi conexión 🤕 ({e})", "sad")

# ================== Imágenes (expresiones) ==================
FRAMES_FILES = {
    "neutral": {"base":"akira_neutral.png","blink":"akira_neutral_blink.png","tail":[]},
    "happy":   {"base":"akira_happy.png","blink":"akira_happy_blink.png","tail":["akira_happy_tail1.png","akira_happy_tail2.png"]},
    "sad":     {"base":"akira_sad.png","blink":"akira_sad.png","tail":[]},
    "bye":     {"base":"akira_bye.png","blink":"akira_bye.png","tail":[]},
}

def cargar_png(ruta, ancho=300):
    if not ruta or not os.path.exists(ruta):
        return None
    img = Image.open(ruta).convert("RGBA")
    w, h = img.size
    esc = ancho / float(w)
    img = img.resize((int(w*esc), int(h*esc)), Image.LANCZOS)
    return ImageTk.PhotoImage(img)

def cargar_frames(mapa):
    frames = {}
    for estado, parts in mapa.items():
        frames[estado] = {
            "base":  cargar_png(parts.get("base")),
            "blink": cargar_png(parts.get("blink")),
            "tail":  [f for f in (cargar_png(p) for p in parts.get("tail", [])) if f]
        }
        if frames[estado]["blink"] is None:
            frames[estado]["blink"] = frames[estado]["base"]
    return frames

# ================== Interfaz (Tkinter) ==================
class AkiraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Akira 🐾 - Tu compañero leal")
        self.root.geometry("720x760")
        self.root.config(bg="#dff9fb")

        self.brain = AkiraBrain()
        self.frames = cargar_frames(FRAMES_FILES)

        self.estado_actual = "neutral"
        self.cola_index = 0
        self.job_blink = None
        self.job_wag = None

        # GRID
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Avatar
        top = tk.Frame(self.root, bg="#dff9fb")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        self.img_label = tk.Label(top, bg="#dff9fb")
        self.img_label.pack()

        # Chat
        mid = tk.Frame(self.root, bg="#dff9fb")
        mid.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)

        self.chat = scrolledtext.ScrolledText(
            mid, wrap=tk.WORD, width=80, height=22, bg="#f7f1e3", font=("Arial", 11)
        )
        self.chat.grid(row=0, column=0, sticky="nsew")
        self.chat.config(state="disabled")

        # Entrada
        bottom = tk.Frame(self.root, bg="#dff9fb")
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,12))
        bottom.columnconfigure(0, weight=1)

        self.entry = tk.Entry(bottom, font=("Arial", 12))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=6)
        self.entry.bind("<Return>", self.enviar)

        self.btn = tk.Button(
            bottom, text="Enviar 🐾", command=self.enviar,
            bg="#74b9ff", fg="white", font=("Arial", 11, "bold"), padx=16, pady=6
        )
        self.btn.grid(row=0, column=1, padx=(8,0))

        # Mensaje inicial + ayuda de comandos
        self._append("Akira", "¡Hola! Soy tu compañero leal. Escríbeme algo para comenzar 💙")
        self._append("Akira", "Puedo recordar cosas si me dices: 'recuerda que ...'. "
                               "También puedo olvidarlas con: 'olvida ...'. "
                               "Dime: 'me llamo ...' o 'me gusta ...' y lo guardo 🐾")

        self._aplicar_estado("neutral")
        self._planificar_parpadeo()
        self.entry.focus_set()

    # ---- UI helpers ----
    def _set_frame(self, img):
        if img is None:
            base = self.frames.get(self.estado_actual, {}).get("base") or self.frames.get("neutral", {}).get("base")
            if base:
                self.img_label.config(image=base)
                self.img_label.image = base
            return
        self.img_label.config(image=img)
        self.img_label.image = img

    def _mostrar_base(self): self._set_frame(self.frames[self.estado_actual]["base"])
    def _mostrar_blink(self): self._set_frame(self.frames[self.estado_actual]["blink"])

    def _mostrar_tail(self):
        tails = self.frames[self.estado_actual]["tail"]
        if not tails: return
        self._set_frame(tails[self.cola_index % len(tails)])
        self.cola_index = (self.cola_index + 1) % len(tails)

    def _append(self, speaker, text):
        self.chat.config(state="normal")
        self.chat.insert(tk.END, f"{speaker}: {text}\n")
        self.chat.config(state="disabled")
        self.chat.yview(tk.END)

    # ---- Parpadeo ----
    def _planificar_parpadeo(self):
        delay = random.randint(2200, 5500)
        self.job_blink = self.root.after(delay, self._parpadear)

    def _parpadear(self):
        self._mostrar_blink()
        self.root.after(120, self._mostrar_base)
        self._planificar_parpadeo()

    # ---- Cola (happy) ----
    def _iniciar_wag(self):
        if self.job_wag is not None: return
        def loop():
            self._mostrar_tail()
            if not self.frames[self.estado_actual]["tail"]:
                self._detener_wag(); self._mostrar_base(); return
            self.job_wag = self.root.after(random.choice([90, 100, 110, 120]), loop)
        self.job_wag = self.root.after(0, loop)

    def _detener_wag(self):
        if self.job_wag is not None:
            self.root.after_cancel(self.job_wag)
            self.job_wag = None

    def _aplicar_estado(self, nuevo):
        self.estado_actual = nuevo
        self.cola_index = 0
        if not self.frames[self.estado_actual]["tail"]:
            self._detener_wag()
        self._mostrar_base()
        if self.frames[self.estado_actual]["tail"]:
            self._iniciar_wag()

    # ---- Interacción ----
    def enviar(self, event=None):
        msg = self.entry.get().strip()
        if not msg: return
        self.entry.delete(0, tk.END)
        self._append("Tú", msg)

        texto, estado = self.brain.responder(msg)
        self._append("Akira", texto)
        self._aplicar_estado(estado)

# ================== Run ==================
if __name__ == "__main__":
    # Aviso si faltan imágenes (no rompe)
    faltan = []
    for est, parts in FRAMES_FILES.items():
        b = parts.get("base");  bp = parts.get("blink")
        if b and not os.path.exists(b): faltan.append(b)
        if bp and not os.path.exists(bp): faltan.append(bp)
        for f in parts.get("tail", []):
            if not os.path.exists(f): faltan.append(f)
    if faltan:
        print("Aviso: faltan imágenes:", ", ".join(sorted(set(faltan))))

    root = tk.Tk()
    app = AkiraApp(root)
    root.mainloop()
