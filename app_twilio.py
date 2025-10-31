# app_twilio.py — webhook a prueba de balas (eco + logs + salud)
import os
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST", "GET"])
def whatsapp_webhook():
    # Aceptamos GET solo para debug rápido desde el navegador:
    if request.method == "GET":
        return "WhatsApp webhook vivo (usa POST desde Twilio)", 200

    try:
        form = dict(request.form)
        print(">>> HIT /whatsapp")
        print(">>> HEADERS:", dict(request.headers))
        print(">>> FORM:", form)

        incoming = form.get("Body", "") or ""
        # Respuesta inmediata (eco). Esto garantiza 200 rápido.
        resp = MessagingResponse()
        resp.message(f"Eco Akira 🐾: {incoming if incoming else '...'}")
        return Response(str(resp), mimetype="application/xml", status=200)

    except Exception as e:
        # Nunca dejamos de responder 200 a Twilio (evita timeouts 11200)
        resp = MessagingResponse()
        resp.message(f"Akira vivo, pero error interno: {e}")
        return Response(str(resp), mimetype="application/xml", status=200)

@app.route("/", methods=["GET"])
def home():
    return "Akira WhatsApp Bot ON", 200

@app.route("/healthz", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug=False para que no se reinicie doble
    app.run(host="0.0.0.0", port=port, debug=False)
