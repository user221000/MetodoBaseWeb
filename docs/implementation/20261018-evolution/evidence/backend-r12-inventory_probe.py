"""Read-only R12 structural inventory; never imports application or database code.

Run with an explicit repository and output path. This records source facts,
not an implementation/security acceptance test. No connection or SDK is used.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


SOURCES = (
    'docs/audit/2026-10-18/ARQUITECTURA_Y_DOCUMENTACION.md',
    'docs/audit/2026-10-18/ux/INFORME_UX.md',
    'docs/audit/2026-10-18/PROMPT_EJECUCION_INTEGRAL.md',
    'docs/audit/2026-10-18/ROADMAP_PRIORIZADO.md',
    'docs/implementation/20261018-evolution/ARQUITECTURA_ACTUAL.md',
    'docs/implementation/20261018-evolution/AISLAMIENTO.md',
    'docs/implementation/20261018-evolution/DECISIONES.md',
    'docs/implementation/20261018-evolution/EQUIPO.md',
    'docs/implementation/20261018-evolution/RECUPERACION_CUENTA.md',
    'docs/implementation/20261018-evolution/evidence/backend-r04-policy-matrix.md',
    'web/database/models.py', 'web/database/engine.py',
    'web/database/tenant_context.py', 'web/database/tenant_policy.py',
    'web/database/schema_control.py',
    'web/database/alembic/schema_contract_v1.py',
    'web/database/alembic/security_contract_v1.py',
    'web/database/repository.py', 'web/middleware/tenant.py',
    'web/account_values.py', 'web/auth.py', 'web/auth_deps.py',
    'web/services/permissions.py', 'web/routes/auth.py',
    'web/routes/team.py', 'web/services/team_invitation_service.py',
    'web/routes/clientes.py', 'api/routes/clientes.py',
    'web/routes/planes.py', 'web/routes/usuario.py',
    'web/services/generation_quota.py', 'web/services/plan_generation.py',
    'web/services/plan_documents.py', 'web/services/private_objects.py',
    'web/storage/objects.py', 'web/storage/local.py',
    'web/services/password_recovery.py', 'web/services/recovery_dispatcher.py',
    'web/routes/password_recovery.py',
    'web/services/personal_diary_service.py',
    'web/services/personal_diary_persistence.py',
    'web/services/privacy_export.py',
    'tests/test_personal_member_scope.py',
    'tests/test_individual_publication_security_review.py',
    'tests/integration_invitation_tenant_postgres.py',
)


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments], text=True).strip()


def snapshot(root, paths):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}


def assignments(tree):
    output = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            output[statement.targets[0].id] = statement.value
    return output


def run(root: Path):
    paths = sorted(set(SOURCES) | {
        str(path.relative_to(root)).replace('\\', '/')
        for pattern in (
            'web/database/alembic/versions/*.py',
            'web/database/alembic/schema_targets/*.json',
            'tests/fixtures/schema/*.sql',
        ) for path in root.glob(pattern)
    })
    before = snapshot(root, paths)
    text = lambda name: (root / name).read_text(encoding='utf-8-sig')
    parse = lambda name: ast.parse(text(name), filename=name)
    model_classes = {node.name: node for node in parse('web/database/models.py').body if isinstance(node, ast.ClassDef)}
    models = {}
    for name, node in model_classes.items():
        values = assignments(node)
        table = values.get('__tablename__')
        if isinstance(table, ast.Constant):
            models[name] = {'table': table.value, 'fields': sorted(key for key, value in values.items()
                if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'Column')}
    policies = assignments(parse('web/database/tenant_policy.py'))
    tenant_tables = ast.literal_eval(policies['TENANT_COLUMNS'])
    control_tables = ast.literal_eval(policies['CONTROL_PLANE'].args[0])
    migrations = {}
    for path in root.glob('web/database/alembic/versions/*.py'):
        values = assignments(ast.parse(path.read_text(encoding='utf-8-sig')))
        if 'revision' in values:
            migrations[ast.literal_eval(values['revision'])] = ast.literal_eval(values.get('down_revision', ast.Constant(None)))
    ancestors = set()
    for value in migrations.values():
        ancestors.update(value if isinstance(value, tuple) else [value])
    heads = sorted(set(migrations) - ancestors)
    user_fields = set(models['Usuario']['fields'])
    plan_fields = set(models['PlanGenerado']['fields'])
    routes = []
    progress_writers = []
    for directory in ('web/routes', 'api/routes'):
        for path in (root / directory).glob('*.py'):
            source = path.read_text(encoding='utf-8-sig')
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.args:
                            path_value = decorator.args[0]
                            if isinstance(path_value, ast.Constant) and isinstance(path_value.value, str):
                                routes.append({'source': str(path.relative_to(root)).replace('\\', '/'),
                                    'line': node.lineno, 'method': decorator.func.attr, 'path': path_value.value})
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'ClientProgress':
                    progress_writers.append({'source': str(path.relative_to(root)), 'line': node.lineno})
    facts = {
        'business_table_count': len(models),
        'tenant_family_count': len(tenant_tables),
        'control_plane_count': len(control_tables),
        'tenant_families': tenant_tables,
        'control_plane_tables': sorted(control_tables),
        'heads': heads,
        'user_has_persistent_email_verified_field': bool(user_fields & {'email_verified', 'email_verified_at', 'verified_email'}),
        'missing_r12_model_names': sorted({'ClientAccountLink', 'ClientLinkInvitation', 'ClientPlanPublication'} - set(models)),
        'plan_has_explicit_member_publication_fields': bool(plan_fields & {'published_at', 'published', 'publication_status', 'member_visible'}),
        'client_progress_route_constructors': progress_writers,
        'models': models,
        'routes': routes,
    }
    checks = {
        'schema28_has_26_business_tables': len(models) == 26,
        'schema28_has_20_tenant_families_and_6_explicit_controls': len(tenant_tables) == 20 and len(control_tables) == 6,
        'all_business_tables_classified': {value['table'] for value in models.values()} == set(tenant_tables) | set(control_tables),
        'single_reviewed_head28': heads == ['20261019_account_recovery'],
        'no_persistent_global_email_verification': not facts['user_has_persistent_email_verified_field'],
        'google_checks_but_does_not_persist_verification': 'google_info.get("email_verified") != "true"' in text('web/routes/auth.py'),
        'email_semantics_strip_lower_preserved': 'return value.strip().lower()' in text('web/account_values.py'),
        'all_three_r12_entities_absent': len(facts['missing_r12_model_names']) == 3,
        'no_plan_member_publication_flag': not facts['plan_has_explicit_member_publication_fields'],
        'personal_route_context_is_account_id': 'request.url.path.startswith("/api/usuario/")' in text('web/middleware/tenant.py'),
        'same_session_other_tenant_rejected': 'raise ValueError("Tenant identity mismatch")' in text('web/database/tenant_context.py'),
        'professional_invitation_returns_token_to_issuer': '"invitation_token": token' in text('web/services/team_invitation_service.py'),
        'professional_invitation_rejects_existing_account': '"email_already_registered"' in text('web/services/team_invitation_service.py'),
        'owner_portfolio_export_barrier_present': 'user.role != UserRole.OWNER' in text('web/services/personal_diary_persistence.py'),
        'personal_export_excludes_unverified_member_links': '"unverified_gym_member_links"' in text('web/services/privacy_export.py'),
        'no_current_measurement_write_route_constructor': not progress_writers,
    }
    after = snapshot(root, paths)
    result = {
        'kind': 'R12_READONLY_STRUCTURAL_INVENTORY_NOT_RUNTIME_ACCEPTANCE',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'base': git(root, 'rev-parse', 'HEAD'),
        'branch': git(root, 'branch', '--show-current'),
        'application_imports': False, 'database_connections': 0, 'provider_calls': 0,
        'source_count': len(paths), 'changed_during_probe': before != after,
        'source_sha256_before': before, 'source_sha256_after': after,
        'checks': checks, 'facts': facts,
    }
    if before != after or not all(checks.values()):
        raise RuntimeError('R12 inventory premises differ; inspect without changing product')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.root.resolve(strict=True))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'checks_passed': len(result['checks']), 'sources': result['source_count'],
        'base': result['base'], 'changed_during_probe': result['changed_during_probe'],
        'runtime_or_database_acceptance': False}))
