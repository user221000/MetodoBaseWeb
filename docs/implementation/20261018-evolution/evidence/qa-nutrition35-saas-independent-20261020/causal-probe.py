from pathlib import Path
import hashlib,json,os,sys,tempfile
ROOT=Path('F:/mb-qa-followup34-sqlfix-20261020')
TASK=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-nutrition35-saas-20261020')
PRIVATE=TASK/'private'
os.environ['TEMP']=str(PRIVATE)
os.environ['TMP']=str(PRIVATE)
tempfile.tempdir=None
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
from web.database.models import Cliente
from web.database.repository import _cliente_to_dict
from web.services.nutrition_profiles import capture_profile
from core.nutrition_restrictions import NutritionRestrictionInputError
client=Cliente(id_cliente='synthetic-causal-only',gym_id='synthetic-causal-only',nombre='Synthetic',alimentos_excluidos='[]')
assert _cliente_to_dict(client)['alimentos_excluidos']==[]
client.alimentos_excluidos='['
try:
    capture_profile(client)
except NutritionRestrictionInputError as error:
    domain_class=type(error).__name__
    domain_code=error.code
else:
    raise AssertionError('domain accepted malformed storage')
try:
    _cliente_to_dict(client)
except json.JSONDecodeError as error:
    serializer_class=type(error).__name__
else:
    raise AssertionError('before serializer did not reproduce')
result={'source_head':'54e511b3ac8636c6ffb6c20cd3b4f8d86922ad2e',
        'valid_empty_list_control':True,'same_invalid_value_domain_class':domain_class,'domain_code':domain_code,
        'same_invalid_value_serializer_class':serializer_class,
        'cause':'repository serializer decodes exclusions before capture_profile validates them',
        'database_network_or_auth_used':False,'no_health_payload_published':True,
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(TASK/'causal-review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
