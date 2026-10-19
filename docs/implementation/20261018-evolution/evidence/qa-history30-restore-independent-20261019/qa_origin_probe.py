"""Read-only reproduction of original outside-MAIN test import routing; collect-only."""
import importlib,inspect,json,os
from pathlib import Path
def pytest_sessionstart(session):
    names=['tests.isolation','tests.integration_schema_migrations','web.database.models','web.database.schema_control']
    loaded={name:importlib.import_module(name) for name in names}
    value={'scope':'Collect-only import-routing diagnosis; no test, migration or DB fixture execution.','module_paths':{name:str(Path(module.__file__).resolve()) for name,module in loaded.items()},'actual_expected_head':loaded['web.database.schema_control'].expected_head(),'Base_definition_file':inspect.getfile(loaded['web.database.models'].Base)}
    Path(os.environ['QA_ORIGIN_PROBE_OUTPUT']).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
