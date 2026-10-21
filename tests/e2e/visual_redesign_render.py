"""Render actual templates with empty/unconfirmed UI and canonical public catalogue.

No factory, database, identity, HTTP API or provider is started. Browser acceptance
of this output is limited to layout/semantics. Baseline uses immutable Git sources.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import subprocess
import sys
from jinja2 import BaseLoader, Environment, FileSystemLoader, TemplateNotFound

ROOT = Path(__file__).resolve().parents[2]
BASE = '713bd3d39a37ed6bef0f344a67a6bfbfccbaa4b3'
sys.path.insert(0, str(ROOT))
from core.plan_catalog import get_plan_catalog, get_individual_plan_catalog

CASES = ['landing', 'login_gym', 'login_usuario', 'registro', 'dashboard', 'clientes',
    'planes', 'generar-plan', 'suscripciones', 'equipo', 'configuracion',
    'usuario_mi_plan', 'usuario_perfil', 'usuario_historial', 'usuario_suscripcion',
    'usuario_progreso', 'cuenta_seguridad37', 'usuario_seguridad37', 'recordatorios',
    'usuario_recordatorios', 'seguimiento', '404']


class BaselineLoader(BaseLoader):
    def get_source(self, environment, template):
        result = subprocess.run(['git', 'show', BASE + ':web/templates/' + template],
            cwd=ROOT, capture_output=True)
        if result.returncode:
            raise TemplateNotFound(template)
        return result.stdout.decode('utf-8'), template, lambda: True


def environment(baseline=False):
    loader = BaselineLoader() if baseline else FileSystemLoader(ROOT / 'web/templates')
    env = Environment(loader=loader, autoescape=True)
    env.globals.update(csrf_token=lambda request: 'visual-synthetic-csrf')
    return env


def render(case, baseline=False):
    env = environment(baseline)
    catalog = get_plan_catalog('web')
    business = {key: value for key, value in catalog.items() if value['audiencia'] == 'gym'}
    return env.get_template(case + '.html').render(
        request=SimpleNamespace(state=SimpleNamespace(csp_nonce='visual-synthetic-nonce')),
        static_version='visual-review', landing_style_version='visual-review',
        google_client_id='', plan_catalog=catalog, business_plans=business,
        individual_plans=get_individual_plan_catalog(),
        example=json.loads((ROOT / 'web/static/data/landing-example.json').read_text(encoding='utf-8')),
        notification_context='personal' if case.startswith('usuario_') else 'gym',
        account_login_url='/login-usuario' if case.startswith('usuario_') else '/login-gym',
        code=404, message='La página solicitada no está disponible.',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    assert args.output.is_absolute() and not args.output.exists()
    args.output.mkdir(parents=True)
    rows = []
    for case in CASES:
        html = render(case, args.baseline)
        (args.output / (case + '.html')).write_text(html, encoding='utf-8', newline='\n')
        rows.append({'case': case, 'template': case + '.html'})
    (args.output / 'render.json').write_text(json.dumps({'base': BASE, 'baseline': args.baseline,
        'scope': 'Static template layout only; catalogue real, account states unconfirmed',
        'cases': rows}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'rendered': len(rows), 'baseline': args.baseline, 'scope': 'No app, SQL or auth'}))
