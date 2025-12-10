"""
Monitor Total (GitHub + Vercel) - Versión Python
Replica el flujo de n8n para monitorear eventos de GitHub y Vercel
y enviar notificaciones a Telegram.
"""

import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# ============================================
# CONFIGURACIÓN
# ============================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_BOT_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003155739026")


# ============================================
# FUNCIONES DE TELEGRAM
# ============================================
def send_telegram_message(text: str) -> bool:
    """Envía un mensaje a Telegram con formato HTML."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Mensaje enviado a Telegram")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")
        return False


# ============================================
# MANEJADORES DE EVENTOS
# ============================================
def handle_push_event(data: dict):
    """Maneja eventos de push a GitHub."""
    repo = data.get("repository", {})
    head_commit = data.get("head_commit", {})
    pusher = data.get("pusher", {})
    ref = data.get("ref", "").replace("refs/heads/", "")

    message = (
        f"🚀 <b>Nuevo Push Recibido</b>\n\n"
        f"📦 <b>Repo:</b> <a href=\"{repo.get('html_url', '')}\">{repo.get('name', 'N/A')}</a>\n"
        f"🌿 <b>Rama:</b> <code>{ref}</code>\n"
        f"👤 <b>Autor:</b> {pusher.get('name', 'N/A')}\n\n"
        f"📝 <b>Commit:</b> <code>{head_commit.get('id', '')[:7]}</code>\n"
        f"💬 <b>Mensaje:</b> {head_commit.get('message', 'N/A')}\n\n"
        f"🔗 <a href=\"{data.get('compare', '')}\"><b>Ver Diferencias (Diff)</b></a>"
    )

    send_telegram_message(message)


def handle_workflow_run_event(data: dict):
    """Maneja eventos de workflow_run de GitHub Actions."""
    workflow_run = data.get("workflow_run", {})
    repo = data.get("repository", {})
    conclusion = workflow_run.get("conclusion", "")

    if conclusion == "failure":
        # Workflow falló
        message = (
            f"💀 <b>FALLO CRÍTICO EN GITHUB ACTIONS</b>\n\n"
            f"📦 <b>Repo:</b> <a href=\"{repo.get('html_url', '')}\">{repo.get('name', 'N/A')}</a>\n"
            f"⚙️ <b>Workflow:</b> <code>{workflow_run.get('name', 'N/A')}</code>\n"
            f"🌿 <b>Rama:</b> <code>{workflow_run.get('head_branch', 'N/A')}</code>\n\n"
            f"🧨 <b>Evento:</b> {workflow_run.get('event', 'N/A')}\n"
            f"❌ <b>Estado:</b> FAILURE\n\n"
            f"🆘 <a href=\"{workflow_run.get('html_url', '')}\"><b>VER LOGS DEL ERROR</b></a>"
        )
    else:
        # Workflow exitoso
        # Calcular duración
        try:
            updated_at = datetime.fromisoformat(
                workflow_run.get("updated_at", "").replace("Z", "+00:00"))
            run_started_at = datetime.fromisoformat(
                workflow_run.get("run_started_at", "").replace("Z", "+00:00"))
            duration = int((updated_at - run_started_at).total_seconds())
            duration_str = f"{duration}s"
        except:
            duration_str = "N/A"

        message = (
            f"✅ <b>GITHUB ACTION COMPLETADO</b>\n\n"
            f"📦 <b>Repo:</b> <a href=\"{repo.get('html_url', '')}\">{repo.get('name', 'N/A')}</a>\n"
            f"⚙️ <b>Workflow:</b> <code>{workflow_run.get('name', 'N/A')}</code>\n"
            f"🌿 <b>Rama:</b> <code>{workflow_run.get('head_branch', 'N/A')}</code>\n\n"
            f"🏁 <b>Conclusión:</b> {conclusion}\n"
            f"⏱️ <b>Duración:</b> {duration_str}\n\n"
            f"🔍 <a href=\"{workflow_run.get('html_url', '')}\"><b>VER DETALLES</b></a>"
        )

    send_telegram_message(message)


def handle_deployment_status_event(data: dict):
    """Maneja eventos de deployment_status (Vercel/otros)."""
    deployment_status = data.get("deployment_status", {})
    deployment = data.get("deployment", {})
    repo = data.get("repository", {})
    state = deployment_status.get("state", "")

    if state == "failure":
        # Despliegue falló
        message = (
            f"🔥 <b>¡FALLÓ EL DESPLIEGUE!</b>\n\n"
            f"📂 <b>Repo:</b> <a href=\"{repo.get('html_url', '')}\">{repo.get('name', 'N/A')}</a>\n"
            f"🌿 <b>Rama:</b> <code>{deployment.get('ref', 'N/A')}</code>\n"
            f"🌍 <b>Entorno:</b> {deployment.get('environment', 'N/A')}\n\n"
            f"📜 <b>Detalle:</b>\n"
            f"<code>{deployment_status.get('description', 'N/A')}</code>\n\n"
            f"🔗 <a href=\"{deployment_status.get('target_url', '')}\"><b>VER LOGS DEL ERROR</b></a>"
        )
    elif state == "success":
        # Despliegue exitoso
        meta = deployment.get("meta", {}) or deployment.get("payload", {})
        branch = meta.get("githubCommitRef", deployment.get("ref", "N/A"))

        message = (
            f"🎉 <b>¡DESPLIEGUE EXITOSO!</b>\n\n"
            f"📂 <b>Repo:</b> <a href=\"{repo.get('html_url', '')}\">{repo.get('name', 'N/A')}</a>\n"
            f"🌿 <b>Rama:</b> <code>{branch}</code>\n"
            f"🌍 <b>Entorno:</b> {deployment.get('environment', 'N/A')}\n\n"
            f"🔗 <b>Link:</b> <code>{deployment_status.get('target_url', 'N/A')}</code>\n\n"
            f"👉 <a href=\"{deployment_status.get('target_url', '')}\"><b>Hacer Clic para Abrir</b></a>"
        )
    else:
        # Otros estados (pending, etc.) - no notificar
        print(f"ℹ️ Estado de deployment ignorado: {state}")
        return

    send_telegram_message(message)


# ============================================
# ENDPOINT WEBHOOK
# ============================================
@app.route("/github-push", methods=["POST"])
def github_webhook():
    """
    Endpoint principal que recibe webhooks de GitHub.
    Clasifica el evento y lo enruta al manejador correspondiente.
    """
    # Obtener el tipo de evento desde el header
    event_type = request.headers.get("X-GitHub-Event", "")
    data = request.json or {}

    print(f"\n{'='*50}")
    print(f"📩 Evento recibido: {event_type}")
    print(f"{'='*50}")

    # Clasificador de eventos (equivalente al Switch de n8n)
    if event_type == "push":
        handle_push_event(data)
    elif event_type == "workflow_run":
        # Solo procesar cuando el workflow ha completado
        if data.get("action") == "completed":
            handle_workflow_run_event(data)
        else:
            print(f"ℹ️ Workflow action ignorada: {data.get('action')}")
    elif event_type == "deployment_status":
        handle_deployment_status_event(data)
    else:
        print(f"⚠️ Evento no manejado: {event_type}")

    return jsonify({"status": "ok", "event": event_type}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de health check."""
    return jsonify({"status": "healthy", "service": "GitHub Monitor"}), 200


@app.route("/", methods=["GET"])
def home():
    """Página de inicio."""
    return """
    <html>
        <head><title>GitHub Monitor</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>🚀 GitHub Monitor</h1>
            <p>Servidor activo y escuchando webhooks de GitHub.</p>
            <p><b>Endpoint:</b> <code>POST /github-push</code></p>
            <hr>
            <p>Eventos soportados:</p>
            <ul style="list-style: none;">
                <li>✅ push</li>
                <li>✅ workflow_run</li>
                <li>✅ deployment_status</li>
            </ul>
        </body>
    </html>
    """


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 GitHub Monitor - Iniciando servidor...")
    print("="*50)
    print(f"📱 Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    print(
        f"🔑 Token configurado: {'Sí' if TELEGRAM_BOT_TOKEN != 'TU_BOT_TOKEN_AQUI' else 'No'}")
    print("="*50 + "\n")

    # Ejecutar servidor
    app.run(host="0.0.0.0", port=5000, debug=True)
