# app_twilio.py — Akira WhatsApp (IA + documentos + imágenes) con manejo robusto
import os, requests
from flask import Flask, request, Response
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse

# IA y análisis
from akira_brain import akira_reply  # tu función de IA con memoria
from analyzer import (
    analyze_image_bytes, handle_document_bytes, split_for_whatsapp
)

load_dotenv()
app = Flask(__name__)

# Credenciales Twilio para descargar media protegida (sandbox)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")

@app.route("/whatsapp", methods=["POST", "GET"])
def whatsapp_webhook():
    # GET solo para debug rápido en el navegador
    if request.method == "GET":
        return "WhatsApp webhook vivo (usa POST desde Twilio)", 200

    resp = MessagingResponse()
    try:
        form = request.form
        from_number = form.get("From", "")
        body        = form.get("Body", "") or ""
        num_media   = int(form.get("NumMedia", "0") or 0)

        # LOGS útiles (se ven en Render → Logs)
        print(">>> HIT /whatsapp")
        print(">>> FROM:", from_number)
        print(">>> BODY:", body)
        print(">>> NUM_MEDIA:", num_media)

        if num_media > 0:
            # Soportamos solo el primer adjunto (lo común en WhatsApp)
            media_url = form.get("MediaUrl0")
            media_ct  = form.get("MediaContentType0", "")
            print(">>> MEDIA:", media_url, media_ct)

            # Descarga media protegida con auth SID/TOKEN
            r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=30)
            r.raise_for_status()
            data = r.content

            # Imagen → Visión + OCR; Documento → extraer texto (PDF/DOCX/TXT)
            if media_ct.startswith("image/"):
                goal = "analiza y resuelve si es un ejercicio; explica paso a paso"
                out = analyze_image_bytes(media_ct, data, goal=goal)
                parts = split_for_whatsapp(out)
            else:
                mode = "resumen"
                bl = body.lower()
                if any(k in bl for k in ["explica", "explícame", "explicame", "explicar"]):
                    mode = "explicar"
                parts = handle_document_bytes(media_ct, data, mode=mode)

            for p in parts:
                resp.message(p)
            return Response(str(resp), mimetype="application/xml", status=200)

        # Texto normal → IA con memoria/persona
        out = akira_reply(from_number, body)
        parts = split_for_whatsapp(out)
        for p in parts:
            resp.message(p)
        return Response(str(resp), mimetype="application/xml", status=200)

    except Exception as e:
        # Pase lo que pase, respondemos 200 para evitar timeouts 11200 en Twilio
        print(">>> ERROR:", e)
        resp.message(f"Ups, tuve un problema procesando tu mensaje 🤕\nDetalle: {e}")
        return Response(str(resp), mimetype="application/xml", status=200)

@app.route("/", methods=["GET"])
def home():
    return "Akira WhatsApp Bot ON", 200

@app.route("/healthz", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

