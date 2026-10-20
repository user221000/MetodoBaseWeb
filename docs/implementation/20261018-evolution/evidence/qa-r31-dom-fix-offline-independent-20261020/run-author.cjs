'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const root=process.env.DETACH31_SOURCE_ROOT;
if(!root)throw Error('Explicit source root required');
const filename=path.join(root,'tests/e2e/session_dom_detachment31.cjs');
const raw=path.join(__dirname,'author-canary.raw.cjs');
const target=new Module(filename,module);target.filename=filename;
target.paths=Module._nodeModulePaths(path.dirname(filename));
target._compile(fs.readFileSync(raw,'utf8'),filename);
