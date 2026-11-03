"""Public, factual privacy information while the integral notice is pending.

This projection contains no provider configuration, personal account data or
inferred legal identity. Completing business details requires a separate review;
neither visiting this page nor registering records a new consent.
"""

PRIVACY_CONTACT_EMAIL = "consultoriahernandez@icloud.com"


def public_privacy_notice() -> dict:
    """Return a fresh public projection, explicitly marked as preparation."""
    return {
        "version": "2026-11-03-preparacion-1",
        "status": "preparacion",
        "title": "Información de privacidad",
        "integral_notice_available": False,
        "contact_email": PRIVACY_CONTACT_EMAIL,
        "responsible_name": None,
        "responsible_address": None,
        "status_message": (
            "La identidad y el domicilio del responsable están pendientes de confirmar. "
            "Esta página informa del estado actual y no sustituye un aviso de privacidad integral."
        ),
        "sections": [
            {
                "title": "Contacto",
                "paragraphs": [
                    ("Para consultas sobre tus datos, utiliza el correo de contacto indicado. "
                    "Describe tu solicitud; no envíes contraseñas, códigos de acceso ni "
                    "información clínica por este medio.")
                ],
            },
            {
                "title": "Suscripción y datos",
                "paragraphs": [
                    ("Cancelar la renovación de una suscripción no elimina automáticamente "
                    "la cuenta, los clientes, los planes ni los archivos PDF. La vigencia "
                    "y los cobros se gestionan por separado de las solicitudes sobre datos personales.")
                ],
            },
            {
                "title": "Solicitudes sobre tus datos",
                "paragraphs": [
                    ("Puedes utilizar el contacto indicado para solicitar acceso, rectificación, "
                    "cancelación u oposición al tratamiento de tus datos. La identidad, el alcance "
                    "y las condiciones aplicables requieren revisión; el envío de una solicitud "
                    "no significa que los datos ya se hayan eliminado.")
                ],
            },
        ],
    }
