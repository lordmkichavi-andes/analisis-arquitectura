import logging
import os
import re

from flask import Flask, request
import sib_api_v3_sdk

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

def parse_paragraph(paragraph):
    paragraph_html = paragraph.replace('\n', '<br>')
    return f"<p>{paragraph_html}</p>"

def format_text_as_html(text):
    paragraphs = text.strip().split("\n\n")
    html_paragraphs = []
    for p in paragraphs:
        if re.match(r"^\d+\.", p.strip()):
            parts = p.split("\n", 1)
            title = f"<strong>{parts[0]}</strong>"
            rest = parts[1].replace('\n', '<br>') if len(parts) > 1 else ""
            html_paragraphs.append(f"<p>{title}<br>{rest}</p>")
        else:
            html_paragraphs.append(parse_paragraph(p))
    html_content = (
        "<html>"
        "<head><meta charset='UTF-8'></head>"
        "<body>" + "".join(html_paragraphs) + "</body>"
        "</html>"
    )
    return html_content

def send_brevo_email(to_email, subject, html_body):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME")

    if not api_key:
        logging.error("Falta la variable de entorno BREVO_API_KEY.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    client = sib_api_v3_sdk.ApiClient(configuration)
    email_api = sib_api_v3_sdk.TransactionalEmailsApi(client)

    mail = sib_api_v3_sdk.SendSmtpEmail(
        subject=subject,
        html_content=html_body,
        sender={"email": sender_email, "name": sender_name},
        to=[{"email": to_email}],
    )

    try:
        logging.info("Enviando correo a %s", to_email)
        response = email_api.send_transac_email(mail)
        logging.info("Correo enviado correctamente. Respuesta: %s", response)
    except sib_api_v3_sdk.rest.ApiException as e:
        logging.error("Error al enviar correo: %s", str(e))

@app.route("/api/v1/architecture-result", methods=["POST"])
def analizar():
    data = request.get_json()
    if not data or "contenido" not in data:
        return "Falta 'contenido' en el payload", 400

    contenido = data["contenido"]
    logging.debug("Contenido IA:\n%s", contenido)
    contenido_html = format_text_as_html(contenido)

    if "developer_email" in data:
        send_brevo_email(
            to_email=data["developer_email"],
            subject="Informe de Arquitectura",
            html_body=contenido_html
        )

    if "leader_email" in data:
        send_brevo_email(
            to_email=data["leader_email"],
            subject="Informe de Arquitectura",
            html_body=contenido_html
        )

    return "Correo(s) enviado(s) con el contenido.", 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5011, use_reloader=False)
