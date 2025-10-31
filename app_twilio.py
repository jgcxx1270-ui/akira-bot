# app_twilio.py — Webhook de WhatsApp (Twilio) con soporte de media protegida
import os, requests
from flask import Flask, request, Response
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse

from akira_brain import akira_reply
from analyzer import (
    analyze_image_bytes, handle_document_bytes, split_for_whatsapp
)

load_dotenv()
app = Flask(__name__)

# Credenciales Twilio para descargar media protegida
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From", "")
    body        = request.form.get("Body", "") or ""
    num_media   = int(request.form.get("NumMedia", "0") or 0)

    # Debug opcional:
    # print(">>> FORM:", dict(request.form))

    resp = MessagingResponse()

    try:
        if num_media > 0:
            media_url = request.form.get("MediaUrl0")
            media_ct  = request.form.get("MediaContentType0", "")

            # Descarga del recurso protegido de Twilio con Basic Auth (SID/TOKEN)
            r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=30)
            r.raise_for_status()
            data = r.content

            # Decide por tipo
            if media_ct.startswith("image/"):
                goal = "analiza la imagen y resuelve si es ejercicio; explica paso a paso"
                out = analyze_image_bytes(media_ct, data, goal=goal)
                parts = split_for_whatsapp(out)
                for p in parts:
                    resp.message(p)
            else:
                # Documento (pdf/docx/txt). Modo según texto del usuario
                mode = "resumen"
                bl = body.lower()
                if any(k in bl for k in ["explica", "explícame", "explicame", "explicar"]):
                    mode = "explicar"
                parts = handle_document_bytes(media_ct, data, mode=mode)
                for p in parts:
                    resp.message(p)

        else:
            # Texto normal → IA con memoria
            out = akira_reply(from_number, body)
            parts = split_for_whatsapp(out)
            for p in parts:
                resp.message(p)

    except Exception as e:
        resp.message(f"Tuve un problema al procesar tu mensaje/archivo 🤕\nDetalle: {e}")

    return Response(str(resp), mimetype="application/xml")

@app.route("/", methods=["GET"])
def home():
    return "Akira WhatsApp Bot ON", 200

if __name__ == "__main__":
    # Corre en 0.0.0.0 para exponer con ngrok
    app.run(host="0.0.0.0", port=5000, debug=True)
