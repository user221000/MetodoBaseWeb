"""Explicit bounded operator action; no server, scheduler or activation side effect."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit,unquote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('operation',choices=('inspect','apply'))
    parser.add_argument('--subject',required=True)
    parser.add_argument('--request',required=True)
    parser.add_argument('--expected-version',type=int)
    parser.add_argument('--database-env',required=True)
    parser.add_argument('--expected-database',required=True)
    parser.add_argument('--policy',type=Path)
    parser.add_argument('--policy-digest')
    parser.add_argument('--policy-key-env')
    parser.add_argument('--batch-size',type=int,default=200)
    args=parser.parse_args(argv)
    try:
        # Operational credentials are read by explicit environment NAME only;
        # neither URL nor key enters command arguments or public diagnostics.
        url=os.environ[args.database_env]
        endpoint=urlsplit(url)
        if unquote(endpoint.path.lstrip('/'))!=args.expected_database:
            raise ValueError('Explicit destination database binding differs')
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from web.database.tenant_context import tenant_scope,configure_tenant_engine
        from web.database.schema_control import verify_runtime_schema
        from web.services.account_privacy import _request,summary
        engine=configure_tenant_engine(create_engine(url,pool_size=1,max_overflow=0))
        try:
            from web.services.privacy_restore_binding import verify_application_connection
            with engine.connect() as connection:verify_application_connection(connection)
            verify_runtime_schema(engine)
            with tenant_scope(args.subject),Session(engine) as db:
                verify_application_connection(db.connection())
                if args.operation=='inspect':
                    result=summary(db,_request(db,args.subject,args.request))
                else:
                    if not all((args.policy,args.policy_digest,args.policy_key_env,args.expected_version)):
                        raise ValueError('Apply requires explicit authenticated policy and expected version')
                    if args.policy_key_env in {'BACKUP_ENCRYPTION_KEY','WEB_SECRET_KEY','SECRET_KEY'}:
                        raise ValueError('An independent policy authentication key is required')
                    from web.services.privacy_suppression import authenticate_policy
                    from web.services.privacy_disposition import apply_batch
                    policy=authenticate_policy(args.policy.read_bytes(),base64.b64decode(os.environ[args.policy_key_env],validate=True),args.policy_digest)
                    result=apply_batch(db,args.subject,args.request,args.expected_version,policy,batch_size=args.batch_size)
                    db.commit()
                print(json.dumps(result,sort_keys=True))
        finally:
            engine.dispose()
        return 0
    except Exception as error:
        print(json.dumps({'accepted':False,'error_class':type(error).__name__,'details':'private_operator_review_required'}))
        return 1


if __name__=='__main__':raise SystemExit(main())
