"""Envio de emails de aviso da pipeline via SMTP do Gmail (gratuito, com senha de app).

Variáveis no .env:
  SMTP_USER       conta Gmail que envia (ex.: fulano@gmail.com)
  SMTP_PASSWORD   senha de app de 16 caracteres (não é a senha normal da conta)
  NOTIFY_EMAIL    destinatário(s), separados por vírgula
"""

import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL direto


def enviar(assunto: str, corpo: str) -> None:
    usuario = os.environ.get("SMTP_USER")
    senha = os.environ.get("SMTP_PASSWORD")
    destino = os.environ.get("NOTIFY_EMAIL")
    if not (usuario and senha and destino):
        log.warning("SMTP_USER/SMTP_PASSWORD/NOTIFY_EMAIL não configurados — email não enviado")
        return

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"Pipeline Combustíveis <{usuario}>"
    msg["To"] = destino
    msg.set_content(corpo)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(usuario, senha)
        smtp.send_message(msg)
    log.info("Email enviado para %s: %s", destino, assunto)


def ao_falhar(context) -> None:
    """on_failure_callback: chamado só quando a task falha de vez (após os retries)."""
    ti = context.get("ti")
    dag_run = context.get("dag_run")
    task_id = getattr(ti, "task_id", "?")
    run_id = getattr(dag_run, "run_id", "?")
    erro = context.get("exception")
    corpo = (
        f"A pipeline anp_precos_combustiveis FALHOU.\n\n"
        f"Task:  {task_id}\n"
        f"Run:   {run_id}\n"
        f"Erro:  {erro!r}\n\n"
        f"Veja o log completo na UI do Airflow (túnel SSH -> http://localhost:8081)."
    )
    try:
        enviar(f"[ERRO] Pipeline combustíveis — task {task_id}", corpo)
    except Exception:  # o aviso nunca deve mascarar o erro original
        log.exception("Falha ao enviar email de erro")
