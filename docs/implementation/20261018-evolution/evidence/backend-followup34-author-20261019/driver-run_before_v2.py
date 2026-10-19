import os,sys
root="F:/mb-google33-reviewed-common-20261019"
os.chdir(root);sys.path.insert(0,root)
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
import pytest
raise SystemExit(pytest.main([sys.argv[1],"-q","--tb=short","--confcutdir="+str(__import__("pathlib").Path(sys.argv[1]).parent),"--junitxml="+sys.argv[2]]))
