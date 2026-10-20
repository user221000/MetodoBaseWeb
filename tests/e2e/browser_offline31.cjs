'use strict';
// VM/DOM fixtures supply their own transports. Reject host I/O and real browsers.
const denied=()=>{throw Error('Browser-session VM gate: external I/O disabled');};
require('node:net').Socket.prototype.connect=denied;
require('node:net').Server.prototype.listen=denied;
require('node:tls').connect=denied;
for(const name of['request','get']){require('node:http')[name]=denied;require('node:https')[name]=denied;}
for(const name of['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork'])require('node:child_process')[name]=denied;
globalThis.fetch=async()=>{throw Error('Browser-session VM gate: host fetch disabled');};
const Module=require('node:module'),load=Module._load;
Module._load=function(name,...args){if(/playwright|puppeteer/.test(name))denied();return load.call(this,name,...args);};
