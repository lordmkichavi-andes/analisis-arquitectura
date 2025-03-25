import logging
import os
import re

import sib_api_v3_sdk
from flask import Flask, request

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

def format_text_as_html(text):
    raw_paragraphs = text.strip().split("\n\n")
    html_paragraphs = []
    for raw_paragraph in raw_paragraphs:
        lines = raw_paragraph.split("\n")
        if not lines:
            continue

        lines = [re.sub(r"\*\*", "", line) for line in lines]
        pattern1 = re.match(r"^(\d+\.\s+)([^:]+):(.*)", lines[0].strip())
        pattern2 = re.match(r"^(Regla\s+\d+):(.*)", lines[0].strip())

        if pattern1:
            prefix = pattern1.group(1)
            title_text = pattern1.group(2)
            rest_after_colon = pattern1.group(3)
            lines[0] = f"<strong>{prefix}{title_text}:</strong>{rest_after_colon}"
        elif pattern2:
            regla_prefix = pattern2.group(1)
            rest_after_colon = pattern2.group(2)
            lines[0] = f"<strong>{regla_prefix}:</strong>{rest_after_colon}"
        else:
            lines[0] = lines[0].strip()

        processed_lines = []
        bullet_lines = []
        for line in lines:
            line_strip = line.strip()
            if re.match(r"^[-•]\s+", line_strip):
                line_content = re.sub(r"`([^`]+)`", r"<code>\1</code>", line_strip)
                line_content = re.sub(r"^[-•]\s+", "", line_content)
                bullet_lines.append(f"<li>{line_content}</li>")
            else:
                line_html = re.sub(r"`([^`]+)`", r"<code>\1</code>", line_strip)
                if line_html:
                    processed_lines.append(line_html + "<br>")

        if bullet_lines:
            bullets_html = "".join(bullet_lines)
            processed_lines.append(f"<ul>{bullets_html}</ul>")

        paragraph_html = "".join(processed_lines)
        if paragraph_html.strip():
            html_paragraphs.append(f"<p>{paragraph_html}</p>")

    html_output = (
        "<html>"
        "<head>"
        "<meta charset='UTF-8'>"
        "<style>"
        "  body { font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.4; color: #333; }"
        "  p { margin: 0 0 1em; }"
        "  code { font-family: 'Courier New', Courier, monospace; background: #f8f8f8; padding: 2px 4px; }"
        "  strong { font-weight: bold; }"
        "  ul { margin: 0 0 1em 1.5em; }"
        "  li { margin-bottom: 0.5em; }"
        "</style>"
        "</head>"
        "<body>"
        + "".join(html_paragraphs)
        + "</body></html>"
    )
    return html_output

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
