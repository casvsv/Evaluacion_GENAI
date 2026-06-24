from flask import url_for
import logging

# Configurar logger para simular salida a terminal
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def send_reset_email(user, token):
    """
    Simula el envío de un correo electrónico con el token de recuperación.
    En producción, usarías Flask-Mail, SendGrid, Amazon SES, etc.
    """
    reset_url = url_for('main.reset_token', token=token, _external=True)
    
    logger.info("\n" + "=" * 60)
    logger.info(" SIMULACIÓN DE ENVÍO DE CORREO - RECUPERACIÓN DE CONTRASEÑA ")
    logger.info("=" * 60)
    logger.info(f"Para:   {user.email}")
    logger.info("Asunto: Restablece tu contraseña en AuthSystem")
    logger.info("-" * 60)
    logger.info("Hola,")
    logger.info("Para restablecer tu contraseña, haz clic en el siguiente enlace:")
    logger.info(f"\n{reset_url}\n")
    logger.info("Si no hiciste esta solicitud, simplemente ignora este correo y no habrá cambios.")
    logger.info("=" * 60 + "\n")
    
    return True
