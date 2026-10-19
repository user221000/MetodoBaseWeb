import pytest
from tests.test_landing_commercial import landing

@pytest.mark.parametrize('path',['/checkout.html','/pages/checkout.html','/web/pages/checkout.html'])
def test_unused_checkout_file_has_no_public_route(landing,path):
    response=landing[0].get(path)
    assert response.status_code==404
    assert 'cdn.tailwindcss.com' not in response.text
