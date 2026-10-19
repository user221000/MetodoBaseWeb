"""Exact R12 paths shared by final privacy headers and sensitive limits."""
import re

# Match route shapes independently of input validity: a wrong-method response
# happens before UUID validation and needs the same final privacy headers.
# DTO/path validation remains strict inside the router; this grants no access.
_UUID=r'[^/]+'
_CLIENT=r'[^/]+'
_API=re.compile(
    r'(?:/api/clientes/'+_CLIENT+r'/vinculacion(?:/invitaciones(?:/'+_UUID+r'/reenviar)?'
    r'|/'+_UUID+r'(?:/publicaciones(?:/'+_UUID+r')?)?)?'
    r'|/api/usuario/vinculaciones/(?:invitacion|aceptar)'
    r'|/api/usuario/vinculos(?:/'+_UUID+r'(?:/plan|/publicaciones/'+_UUID+r'/pdf)?)?)\Z'
)


def is_member_link_api(path):
    return isinstance(path,str) and _API.fullmatch(path) is not None


def is_member_link_private(path):
    return path=='/auth/accept-client-link' or is_member_link_api(path)
