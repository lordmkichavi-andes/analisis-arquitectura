import base64
import io
import logging
import os
import re
from datetime import datetime

import matplotlib.pyplot as plt
import sib_api_v3_sdk
from flask import Flask, request
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

MEGA_ESTUDIO_HTML = """
<h2>Informe de Evaluación de Arquitectura Automatizada</h2>
<p><strong>Resumen Ejecutivo:</strong> Una evaluación automatizada de arquitectura, integrada en la fábrica de software, mejora costos, calidad, mantenibilidad, seguridad y escalabilidad. Detecta desviaciones tempranas y reduce el retrabajo.</p>
<h3>Impacto en Costos:</h3>
<p>Se reducen costos al prevenir correcciones tardías. Corregir fallas de diseño en producción puede costar varias veces más que resolverlas al inicio. Una arquitectura limpia evita acumulación de deuda técnica.</p>
<h3>Calidad y Confiabilidad:</h3>
<p>La supervisión continua minimiza defectos y fallas, reforzando disponibilidad y confiabilidad.</p>
<h3>Mantenibilidad y Evolución:</h3>
<p>Monitorear la arquitectura permanentemente promueve modularidad y bajo acoplamiento. Esto agiliza la evolución del software y reduce riesgos de reescritura.</p>
<h3>Seguridad y Cumplimiento:</h3>
<p>Se integran principios de seguridad en el diseño. El evaluador automatizado detecta dependencias inseguras y configuraciones erróneas, reduciendo brechas.</p>
<h3>Escalabilidad y Rendimiento:</h3>
<p>La arquitectura se evalúa para soportar mayor carga. Se detectan cuellos de botella y se corrigen con anticipación, evitando caídas críticas.</p>
<h3>Conclusiones:</h3>
<p>La evaluación automatizada de arquitectura reduce costos, eleva la calidad y acelera la entrega de valor.</p>
"""

def extraer_score(texto):
    p = re.search(r"Score\s*=\s*([\d]+(\.\d+)?)", texto)
    if p:
        v = float(p.group(1))
        logging.debug("Score extraído: %f", v)
        return v
    logging.debug("No se encontró Score en el texto")
    return None

def generar_grafico_score(score):
    logging.debug("Generando gráfico para Score: %f", score)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(["Score"], [score], color="blue")
    ax.set_ylim([0, 1])
    ax.set_ylabel("0 a 1")
    ax.set_title(f"Score Detectado: {score}")
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    logging.debug("Gráfico generado correctamente")
    return img_b64

def generar_pdf_en_memoria(texto_base, grafico_b64=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=60)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Informe de Evaluación de Arquitectura", styles["Title"]))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 0.2*inch))

    for linea in texto_base.split("\n"):
        if linea.strip():
            story.append(Paragraph(linea.strip(), styles["Normal"]))
    story.append(Spacer(1, 0.3*inch))

    if grafico_b64:
        img_data = base64.b64decode(grafico_b64)
        story.append(Image(io.BytesIO(img_data), width=4*inch, height=3*inch))

    doc.build(story)
    pdf_data = buf.getvalue()
    buf.close()
    return pdf_data

def send_brevo_email_pdf(to_email, subject, html_body, pdf_bytes):
    k = os.getenv("BREVO_API_KEY", "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")
    s_email = os.getenv("BREVO_SENDER_EMAIL", "lordmkichavi@gmail.com")
    s_name = os.getenv("BREVO_SENDER_NAME", "Remitente")
    if not k:
        logging.error("Faltan variables de entorno para Brevo (BREVO_API_KEY)")
        return
    cfg = sib_api_v3_sdk.Configuration()
    cfg.api_key["api-key"] = k
    cl = sib_api_v3_sdk.ApiClient(cfg)
    api = sib_api_v3_sdk.TransactionalEmailsApi(cl)
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    mail = sib_api_v3_sdk.SendSmtpEmail(
        subject=subject,
        html_content=html_body,
        sender={"email": s_email, "name": s_name},
        to=[{"email": to_email}],
        attachment=[{"content": pdf_b64, "name": "InformeArquitectura.pdf"}]
    )
    try:
        logging.info("Enviando correo a %s con PDF adjunto", to_email)
        r = api.send_transac_email(mail)
        logging.info("Correo enviado. Respuesta: %s", r)
    except sib_api_v3_sdk.rest.ApiException as e:
        logging.error("Error al enviar correo: %s", str(e))

@app.route("/api/v1/architecture-result", methods=["POST"])
def analizar():
    d = request.get_json()
    if not d or "contenido" not in d:
        return "Falta 'contenido'", 400
    c_ia = d["contenido"]
    logging.debug("Contenido IA:\n%s", c_ia)
    sc = extraer_score(c_ia)
    g_b64 = generar_grafico_score(sc) if sc is not None else None
    txt = (
        "Informe de Evaluación de Arquitectura Automatizada\n\n"
        "Contenido IA recibido:\n"
        f"{c_ia}\n\n"
        "Resumen:\n"
    )
    txt += MEGA_ESTUDIO_HTML.replace("<h2>", "").replace("</h2>", "\n") \
        .replace("<h3>", "").replace("</h3>", "\n") \
        .replace("<p>", "").replace("</p>", "\n") \
        .replace("<strong>", "").replace("</strong>", "") \
        .replace("<br>", "\n").replace("<br/>", "\n") \
        .replace("<br />", "\n")
    pdf_data = generar_pdf_en_memoria(txt, g_b64)
    if "developer_email" in d:
        send_brevo_email_pdf(d["developer_email"], "Informe de Arquitectura", "Adjuntamos el reporte en PDF", pdf_data)
    if "leader_email" in d:
        send_brevo_email_pdf(d["leader_email"], "Informe de Arquitectura", "Adjuntamos el reporte en PDF", pdf_data)
    return "Reporte generado y (si procede) enviado", 200

if __name__ == "__main__":
    logging.info("Iniciando aplicación en puerto 5011")
    app.run(debug=True, port=5011)
