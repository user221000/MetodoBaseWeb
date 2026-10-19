/* Safety wrapper only; driver assertions and browser actions are unchanged. */
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const assert=require('node:assert/strict'),pw=require('playwright-core');
const base=process.env.METODOBASE_E2E_URL,output=process.env.QA_BROWSER_OUTPUT;
const stats={exactOrigin:base,maxRedirects:0,apiCalls:0,routeFetches:0,blockedOtherOrigins:0};
function origin(url){return new URL(url).origin===base;}
function wrapRoute(route){return new Proxy(route,{get(target,key){if(key==='fetch')return async(options={})=>{assert.equal(origin(options.url||target.request().url()),true);stats.routeFetches++;return target.fetch({...options,maxRedirects:0});};const value=target[key];return typeof value==='function'?value.bind(target):value;}});}
function wrapRouting(owner){const route=owner.route.bind(owner);owner.route=async(pattern,handler,options)=>route(pattern,async(value,request)=>{if(!origin(value.request().url())){stats.blockedOtherOrigins++;return value.abort();}return handler(wrapRoute(value),request);},options);}
const launch=pw.chromium.launch.bind(pw.chromium);
pw.chromium.launch=async(...args)=>{const browser=await launch(...args),newContext=browser.newContext.bind(browser);browser.newContext=async(...options)=>{const context=await newContext(...options);wrapRouting(context);await context.route('**/*',route=>route.continue());for(const method of ['get','post','put','patch','delete','head','fetch']){const original=context.request[method].bind(context.request);context.request[method]=async(url,options={})=>{assert.equal(origin(typeof url==='string'?url:url.url()),true);stats.apiCalls++;return original(url,{...options,maxRedirects:0});};}const newPage=context.newPage.bind(context);context.newPage=async(...args)=>{const page=await newPage(...args);wrapRouting(page);return page;};return context;};return browser;};
process.on('exit',()=>fs.writeFileSync(path.join(output,'network-guard.json'),JSON.stringify(stats,null,2)));
const filename=process.env.QA_DRIVER_FILENAME,source=process.env.QA_DRIVER_SOURCE;
const driver=new Module(filename,module);driver.filename=filename;driver.paths=Module._nodeModulePaths(path.dirname(filename));
driver._compile(fs.readFileSync(source,'utf8'),filename);
