# analyzer.py — Procesa documentos e imágenes (Twilio media) con OpenAI + OCR
import os, io, base64, requests
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

# Extracción de PDF/DOCX
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document

# OCR (fotos de cuaderno / manuscritos / impresos)
import pytesseract
from PIL import Image

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "1400"))

# ============== Utilidades generales ==============
def chunk_text(s: str, max_len: int = 4000):
    s = s.strip()
    if len(s) <= max_len:
        return [s]
    parts, i = [], 0
    while i < len(s):
        parts.append(s[i:i+max_len])
        i += max_len
    return parts

def split_for_whatsapp(text: str):
    parts = chunk_text(text, MAX_REPLY_CHARS)
    if len(parts) == 1:
        return parts
    total = len(parts)
    return [f"({i+1}/{total})\n{p}" for i, p in enumerate(parts)]

def llm_answer(system_prompt: str, user_content):
    messages = [{"role": "system", "content": system_prompt}]
    if isinstance(user_content, list):
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": user_content})
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )
    return r.choices[0].message.content.strip()

# ============== Documentos ==============
def extract_text_from_pdf_bytes(b: bytes) -> str:
    with io.BytesIO(b) as fh:
        return pdf_extract_text(fh) or ""

def extract_text_from_docx_bytes(b: bytes) -> str:
    with io.BytesIO(b) as fh:
        doc = Document(fh)
    return "\n".join(p.text for p in doc.paragraphs).strip()

def handle_document_bytes(content_type: str, data: bytes, mode: str = "resumen"):
    """
    Procesa bytes de documento (PDF/DOCX/TXT). Úsalo cuando Twilio te da media protegida.
    mode: 'resumen' | 'explicar'
    """
    ct = (content_type or "").lower()
    text = ""

    try:
        if "pdf" in ct:
            text = extract_text_from_pdf_bytes(data)
        elif "officedocument.wordprocessingml.document" in ct or "wordprocessingml" in ct:
            text = extract_text_from_docx_bytes(data)
        elif "text" in ct:
            text = data.decode("utf-8", errors="ignore")
        else:
            # intento como texto simple
            text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    if not text.strip():
        return split_for_whatsapp(
            "No pude extraer texto del documento. Si es un PDF escaneado, envíalo como foto o usa un PDF con texto real."
        )

    if mode == "explicar":
        out = explain_text(text, "explica paso a paso")
    else:
        out = summarize_text(text, "resumen para estudiar")
    return split_for_whatsapp(out)

# ============== OCR (imágenes con texto) ==============
def ocr_from_bytes(data: bytes, lang: str = "spa"):
    try:
        img = Image.open(BytesIO(data))
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()
    except Exception as e:
        return f"[OCR] Error: {e}"

# ============== Imagen: Visión + OCR (con bytes) ==============
def image_bytes_to_data_url(content_type: str, data: bytes) -> str:
    ct = content_type or "image/jpeg"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{ct};base64,{b64}"

def analyze_image_bytes(content_type: str, data: bytes, goal: str = "analiza y resuelve si es un ejercicio"):
    """
    1) Construye data URL base64 (pública para el LLM) y usa Visión.
    2) Si el resultado es pobre, aplica OCR y resume/explica.
    """
    system = (
        "Eres un tutor escolar. Analiza la imagen (foto de tarea, problema, gráfico o texto) "
        "y explica claro, paso a paso. Si falta info, dilo y sugiere cómo completarla."
    )
    data_url = image_bytes_to_data_url(content_type, data)
    user_content = [
        {"type": "text", "text": f"Objetivo: {goal}"},
        {"type": "image_url", "image_url": {"url": data_url}}
    ]

    try:
        vision_out = llm_answer(system, user_content)
        if len(vision_out) < 120:
            ocr_text = ocr_from_bytes(data, lang="spa")
            if ocr_text and not ocr_text.startswith("[OCR] Error") and len(ocr_text) > 20:
                analysis = summarize_text(ocr_text, "texto detectado por OCR en imagen")
                return f"Texto detectado (OCR):\n{ocr_text[:600]}{'...' if len(ocr_text)>600 else ''}\n\nAnálisis:\n{analysis}"
        return vision_out
    except Exception as e:
        ocr_text = ocr_from_bytes(data, lang="spa")
        if ocr_text and not ocr_text.startswith("[OCR] Error") and len(ocr_text) > 20:
            analysis = summarize_text(ocr_text, "texto detectado por OCR (fallback)")
            return f"[Visión falló: {e}]\n\nTexto (OCR):\n{ocr_text[:600]}{'...' if len(ocr_text)>600 else ''}\n\nAnálisis:\n{analysis}"
        return f"No pude analizar la imagen todavía 🤕 Detalle: {e}"

# ============== Tareas escolares (texto) ==============
def summarize_text(text: str, focus: str = "resumen claro para estudiante"):
    prompt = (
        f"Resume en español con puntos clave y ejemplos si aplica. "
        f"Concluye en 1-2 líneas. Enfócate en: {focus}. "
        f"Si hay listas, usa viñetas."
    )
    return llm_answer(prompt, text)

def explain_text(text: str, instruction: str = "explica paso a paso"):
    prompt = (
        "Explica en español como para un estudiante de secundaria, paso a paso, "
        "claro y conciso. Incluye ejemplos simples si ayuda. "
        "Si hay fórmulas, escríbelas en texto plano."
    )
    user = f"Instrucción: {instruction}\n\nTexto:\n{text}"
    return llm_answer(prompt, user)
