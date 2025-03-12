import requests
import os

def send_email(to_emails, subject, html_content):
    k = os.getenv("BREVO_API_KEY","API_KEY")
    u = "https://api.brevo.com/v3/smtp/email"
    h = {"accept":"application/json","api-key":k,"content-type":"application/json"}
    t = [{"email":x} for x in to_emails]
    d = {"sender":{"name":"ReporteArquitectura","email":"noreply@dominio.com"},"to":t,"subject":subject,"htmlContent":html_content}
    r = requests.post(u,headers=h,json=d)
    if r.status_code!=201: print(r.text)
