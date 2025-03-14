import logging
import os
from flask import Flask, request
import sib_api_v3_sdk

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

def send_brevo_email(to_email, subject, html_body):
    api_key = os.getenv("BREVO_API_KEY", ".....")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "lordmkichavi@gmail.com")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Remitente")

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

    if "developer_email" in data:
        send_brevo_email(
            to_email=data["developer_email"],
            subject="Informe de Arquitectura",
            html_body=contenido
        )

    if "leader_email" in data:
        send_brevo_email(
            to_email=data["leader_email"],
            subject="Informe de Arquitectura",
            html_body=contenido
        )

    return "Correo(s) enviado(s) con el contenido.", 200

if __name__ == "__main__":
    logging.info("Iniciando aplicación en puerto 5011")
    app.run(debug=True, port=5011)
