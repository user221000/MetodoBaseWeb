"""Private recipient-link transport; no Session or ambient tenant is propagated."""
from dataclasses import dataclass
from html import escape
import logging

from web.database.tenant_context import current_tenant

logger=logging.getLogger(__name__)


@dataclass(frozen=True,repr=False)
class InvitationMessage:
    recipient:str
    gym_name:str
    url:str


def send_invitation(message):
    if current_tenant.get():
        logger.error('Member mail skipped reason=ambient_context')
        return False
    from web.services.email_service import _base_layout,_send
    content='<h2>Invitacion para consultar un plan</h2>'
    content+=f'<p>{escape(message.gym_name)} te invita a vincular tu cuenta a un cliente concreto.</p>'
    content+=f'<p><a href="{escape(message.url,quote=True)}">Revisar invitacion</a></p>'
    content+='<p>Inicia sesion o registra tu cuenta habitual y vuelve al mismo enlace. Tu perfil personal, equipo y permisos no cambian. El enlace vence en 7 dias; aceptar requiere tu confirmacion expresa.</p>'
    try:
        # Existing SDK contract distinguishes accepted from delivered. No
        # provider ACK, address, token or URL is copied into operational logs.
        return _send(message.recipient,'Vincular cuenta — Metodo Base',_base_layout(content)) is True
    except Exception as error:
        logger.error('Member mail failed class=%s',type(error).__name__)
        return False
