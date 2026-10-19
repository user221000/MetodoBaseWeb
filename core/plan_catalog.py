"""Canonical commercial catalog, with explicit transitional target compatibility.

Pure data: MXN prices are integer centavos and recurring periods are months.
Provider price IDs are adapter input, never environment reads in the domain.
The user approved Free=10 clients and continued desktop support on 2026-10-18.
"""
from __future__ import annotations

from copy import deepcopy

_PLAN_DEFINITIONS = {'free': {'precio_mxn': 0,
          'max_clientes': 10,
          'max_sesiones': 1,
          'max_planes_diarios': 5,
          'max_registros_diarios': 5,
          'max_planes_por_cliente_dia': 5,
          'multi_usuario': False,
          'preferencias_alimentos': True,
          'gestion_suscripciones': False,
          'progresion_clientes': False,
          'stripe_price_id': None,
          'features': ['pdf_export', 'food_preferences'],
          'descripcion': 'Hasta 10 clientes',
          'moneda': 'MXN',
          'periodo': 'month',
          'precio_centavos': 0,
          'audiencia': 'gym'},
 'standard': {'precio_mxn': 159,
              'max_clientes': 25,
              'max_sesiones': 2,
              'max_planes_diarios': 1,
              'max_registros_diarios': 25,
              'max_planes_por_cliente_dia': 1,
              'multi_usuario': False,
              'preferencias_alimentos': True,
              'gestion_suscripciones': False,
              'progresion_clientes': False,
              'stripe_price_id': None,
              'features': ['pdf_export', 'excel_export', 'api_access', 'food_preferences'],
              'descripcion': 'Para nutriólogos independientes',
              'moneda': 'MXN',
              'periodo': 'month',
              'precio_centavos': 15900,
              'audiencia': 'gym'},
 'gym_comercial': {'precio_mxn': 479,
                   'max_clientes': 75,
                   'max_sesiones': 4,
                   'max_planes_diarios': 3,
                   'max_registros_diarios': 0,
                   'max_planes_por_cliente_dia': 3,
                   'multi_usuario': False,
                   'preferencias_alimentos': True,
                   'gestion_suscripciones': True,
                   'progresion_clientes': False,
                   'stripe_price_id': None,
                   'features': ['pdf_export',
                                'excel_export',
                                'api_access',
                                'custom_branding',
                                'templates',
                                'food_preferences',
                                'client_subscriptions'],
                   'descripcion': 'Para gimnasios en crecimiento',
                   'moneda': 'MXN',
                   'periodo': 'month',
                   'precio_centavos': 47900,
                   'audiencia': 'gym'},
 'clinica': {'precio_mxn': 979,
             'max_clientes': 0,
             'max_sesiones': 0,
             'max_planes_diarios': 0,
             'max_registros_diarios': 0,
             'max_planes_por_cliente_dia': 0,
             'multi_usuario': True,
             'preferencias_alimentos': True,
             'gestion_suscripciones': True,
             'progresion_clientes': True,
             'stripe_price_id': None,
             'features': ['pdf_export',
                          'excel_export',
                          'api_access',
                          'custom_branding',
                          'templates',
                          'multi_user',
                          'priority_support',
                          'food_preferences',
                          'client_subscriptions',
                          'client_progression'],
             'descripcion': 'Sin límites, para clínicas y equipos grandes',
             'moneda': 'MXN',
             'periodo': 'month',
             'precio_centavos': 97900,
             'audiencia': 'gym'},
 'pro_usuario': {'precio_mxn': 79,
                 'max_clientes': 1,
                 'max_sesiones': 1,
                 'max_planes_diarios': 5,
                 'max_registros_diarios': 0,
                 'max_planes_por_cliente_dia': 5,
                 'multi_usuario': False,
                 'preferencias_alimentos': True,
                 'gestion_suscripciones': False,
                 'progresion_clientes': False,
                 'stripe_price_id': None,
                 'features': ['pdf_export', 'priority_support', 'food_preferences'],
                 'descripcion': 'Plan Pro para usuarios individuales',
                 'moneda': 'MXN',
                 'periodo': 'month',
                 'precio_centavos': 7900,
                 'audiencia': 'individual'}}


def get_plan_catalog(target: str, *, stripe_prices: dict[str, str] | None = None) -> dict:
    """Return an independent adapter view without mutating domain definitions.

    Desktop retains its historical Free daily limit of one while the user
    decides the web/desktop discrepancy (web five). No silent downgrade.
    Individual Pro is absent from desktop's gym-license selector.
    """
    if target not in {"web", "desktop"}:
        raise ValueError("Unknown catalog consumer")
    catalog = deepcopy(_PLAN_DEFINITIONS)
    if target == "desktop":
        catalog.pop("pro_usuario")
        catalog["free"]["max_planes_diarios"] = 1
        catalog["free"]["max_planes_por_cliente_dia"] = 1
    for name, definition in catalog.items():
        # Preserve the adapter contract: free has no provider price, paid plans
        # have an empty configuration value until the operator supplies an ID.
        definition["stripe_price_id"] = (stripe_prices or {}).get(name, "") if definition["precio_mxn"] else None
    return catalog
