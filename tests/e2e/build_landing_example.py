"""Build a public excerpt from a real offline worker result, never from a real account."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.isolation import block_external_sockets, prepare_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    root = prepare_environment(discard_inherited=True).resolve()
    block_external_sockets()
    from fastapi.testclient import TestClient
    from web.database.engine import get_engine
    from web.database.models import Base
    from web.main_web import create_app
    from web.services import email_service
    engine = get_engine()
    if engine.dialect.name != 'sqlite' or not Path(engine.url.database or '').resolve().is_relative_to(root):
        raise RuntimeError('Own temporary SQLite required')
    Base.metadata.create_all(engine)
    email_service.send_welcome = lambda *_args,**_kwargs:{'success':True,'delivery':'synthetic_not_sent'}
    profile = {'edad':30,'peso_kg':75,'estatura_cm':175,'sexo':'M','objetivo':'mantenimiento','nivel_actividad':'moderada'}
    with TestClient(create_app()) as client:
        registered = client.post('/api/auth/registro',json={'email':'landing-example@example.invalid',
            'nombre':'Synthetic Demo','tipo':'usuario','password':'Synthetic-Landing-Password-2026!'})
        assert registered.status_code == 200, registered.status_code
        headers = {'Authorization':'Bearer '+registered.json()['token']}
        assert client.get('/api/auth/me',headers=headers).json()['role']=='viewer'
        assert client.put('/api/usuario/perfil',headers=headers,json=profile).status_code == 200
        response = client.post('/api/usuario/generar-plan',headers={**headers,'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code == 200, response.text
        result = response.json()
        meal = result['plan']['desayuno']
        excerpt = {'format':'worker_demo_excerpt_v1','meal':'desayuno','groups':[
            {'group':key,'option':meal[key]['opciones'][0]} for key in ('proteinas','carbohidratos','grasas')]}
        pdf = client.get('/api/usuario/descargar-pdf',headers=headers,params={'plan_id':result['plan_id']})
        assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as output:
        output.write(json.dumps(excerpt,indent=2,ensure_ascii=False)+'\n')
    args.evidence.mkdir(parents=True,exist_ok=False)
    (args.evidence/'generated-plan.json').write_text(json.dumps(result['plan'],indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (args.evidence/'generated-plan.pdf').write_bytes(pdf.content)
    source = Path(__file__).resolve().parents[2]
    files = ['web/services/plan_generation.py','web/services/generation_quota.py','core/generador_opciones.py',
        'src/alimentos_base.py','tests/e2e/build_landing_example.py']
    (args.evidence/'provenance.json').write_text(json.dumps({'scope':'Synthetic demonstrative excerpt only; no clinical/professional suitability or general nutritional recommendation',
        'profile_inputs':profile,'execution':'Real ASGI registration, profile, quota, worker, object publication and authorized exact PDF; own metadata-only SQLite and local objects. Welcome is a no-send boundary double; no external sockets.',
        'extraction':'First breakfast option from each of three macro groups, copied without changing weights or equivalences',
        'public_excerpt_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'pdf_sha256':hashlib.sha256(pdf.content).hexdigest(),'pdf_bytes':len(pdf.content),
        'sources':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in files}},indent=2)+'\n',encoding='utf8')
    print(json.dumps({'worker_success':True,'public_excerpt':str(args.output),'pdf_bytes':len(pdf.content)}))


if __name__ == '__main__':
    main()
