/* Reuse all frozen606 assertions. Only two dedicated loopback port literals change. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const root=path.resolve(__dirname,'../..'),file=path.join(__dirname,'personal_diary.cjs'),bytes=fs.readFileSync(file),source=bytes.toString('utf8');
const frozen=JSON.parse(fs.readFileSync(path.join(root,'docs/implementation/20261018-evolution/evidence/ux/diary-ui-source.json'),'utf8'));
if(crypto.createHash('sha256').update(bytes).digest('hex')!==frozen.sources['tests/e2e/personal_diary.cjs'].sha256)throw Error('The historical browser driver changed');
if(source.split('http://127.0.0.1:8776').length-1!==2)throw Error('Unexpected historical port locations');
const replay=new Module(__filename,module);replay.filename=__filename;replay.paths=module.paths;
replay._compile(source.replaceAll('http://127.0.0.1:8776','http://127.0.0.1:8777'),__filename);
