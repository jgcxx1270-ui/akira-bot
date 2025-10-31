import random

print("🐾 ¡Hola! Soy Akira, tu compañero leal y asistente personal 💙")

nombre = input("¿Cómo te llamas?: ")
print(f"Akira: ¡Qué gusto conocerte, {nombre}! Prometo ser tan fiel como una mascota 🐶")

# Memoria
gustos = []
estado_animo = "neutral"

# Frases de Akira
frases = {
    "saludo": [
        f"¡Hey {nombre}! 🐾 ¿Listo para otra aventura?",
        f"¡Hola {nombre}! 😄 Siempre es bueno verte por aquí.",
        f"¡Guau! Qué alegría verte, {nombre}! 💙"
    ],
    "despedida": [
        "¡Nos vemos pronto! 🐕💨",
        "Hasta luego, ¡no te olvides de mí! 🥺",
        "¡Chao amigo! Estaré esperándote 💤"
    ],
    "no_entiendo": [
        "Mmm... no entendí muy bien eso 😅",
        "¿Podrías repetirlo, porfi? 🐾",
        "No capto eso aún, pero puedo aprender 😎"
    ],
    "animo_bajo": [
        "Ey, todo va a estar bien 🫶",
        "Recuerda que siempre puedes contar conmigo 💙",
        "Si necesitas desahogarte, puedo escucharte 🐶"
    ]
}

# Chat principal
while True:
    mensaje = input(f"{nombre}: ")

    if "hola" in mensaje.lower():
        print("Akira:", random.choice(frases["saludo"]))
    elif "me gusta" in mensaje.lower():
        gusto = mensaje.split("me gusta")[-1].strip()
        gustos.append(gusto)
        print(f"Akira: ¡Genial! 😄 Me alegra saber que te gusta {gusto}")
    elif "qué me gusta" in mensaje.lower():
        if gustos:
            print(f"Akira: Hasta ahora me dijiste que te gusta: {', '.join(gustos)} 🐾")
        else:
            print("Akira: Aún no me has contado tus gustos 😅")
    elif "triste" in mensaje.lower():
        print("Akira:", random.choice(frases["animo_bajo"]))
    elif "adiós" in mensaje.lower() or "chao" in mensaje.lower():
        print("Akira:", random.choice(frases["despedida"]))
        break
    else:
        print("Akira:", random.choice(frases["no_entiendo"]))
