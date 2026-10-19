"""R24 shells through real factories; raw response/attribute proof is opt-in own output."""
import hashlib
from html.parser import HTMLParser
import importlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class Attributes(HTMLParser):
    def __init__(self):
        super().__init__();self.nodes=[];self.text=[]
    def handle_starttag(self,tag,attrs):
        self.nodes.append({'tag':tag,'attrs':attrs})
    def handle_data(self,value):
        if value.strip():self.text.append(value)


@pytest.mark.parametrize('factory',['web.main_web','api.app'])
def test_personal_plan_exposes_explicit_source_shopping_and_unavailable_substitutions(factory):
    with TestClient(importlib.import_module(factory).create_app(),raise_server_exceptions=False) as client:
        response=client.get('/mi-plan')
    assert response.status_code==200
    output=os.environ.get('R24_RAW_OUTPUT')
    if output:
        root=Path(output);root.mkdir(parents=True,exist_ok=True)
        filename=factory.replace('.','-')
        raw=response.content;parser=Attributes();parser.feed(response.text)
        (root/(filename+'.html')).write_bytes(raw)
        (root/(filename+'-attrs-text.json')).write_bytes((json.dumps({'method':'TestClient SSR raw HTML, not executed browser DOM',
            'sha256':hashlib.sha256(raw).hexdigest(),'nodes':parser.nodes,'text':parser.text},ensure_ascii=False,indent=2)+'\n').encode())
    assert 'id="plan-shopping"' in response.text
    assert 'id="plan-substitutions-state"' in response.text
