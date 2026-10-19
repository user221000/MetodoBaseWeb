from pathlib import Path
source=Path('F:\\MetodoBaseWeb-execution-20261018\\docs\\implementation\\20261018-evolution\\evidence\\ux\\diary-ui-bf46-independent-20261019-qa\\run2\\server-adapted.py').read_bytes().decode('utf-8')
exec(compile(source,'F:\\MetodoBaseWeb-diary-ui-20261019\\tests\\e2e\\personal_diary_server.py','exec'),{'__file__':'F:\\MetodoBaseWeb-diary-ui-20261019\\tests\\e2e\\personal_diary_server.py','__name__':'__main__'})
