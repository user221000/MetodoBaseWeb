/* Public proof handling against the actual37 script; no browser or providers. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../web/static/js/email-verification37.js'), 'utf8');

function realm(fragment, options = {}) {
    const listeners = new Map();
    const button = { disabled: true };
    const status = { textContent: '' };
    const form = { addEventListener(name, callback) { listeners.set('form:' + name, callback); } };
    const replacements = [], calls = [];
    const sandbox = {
        URLSearchParams,
        location: { hash: fragment, pathname: '/auth/verify-email', search: '?untrusted=ignored' },
        history: { replaceState(...args) {
            if (options.replaceThrows) throw new Error('Synthetic unavailable URL cleanup');
            replacements.push(args);
        } },
        document: { getElementById(id) { return { 'email-confirmation': form, 'confirm-email': button, 'confirmation-status': status }[id]; } },
        fetch: async (url, config) => {
            calls.push({ url, config });
            if (options.networkFails) throw new Error('Synthetic uncertain response');
            return { ok: options.httpStatus === undefined || options.httpStatus === 200,
                status: options.httpStatus || 200,
                json: async () => options.response || { code: 'account_email_confirmed', email_verified: true } };
        },
        addEventListener(name, callback) { listeners.set(name, callback); }
    };
    for (const forbidden of ['localStorage', 'sessionStorage', 'Api', 'indexedDB']) {
        Object.defineProperty(sandbox, forbidden, { get() { throw new Error('Public proof crossed forbidden boundary: ' + forbidden); } });
    }
    vm.runInNewContext(source, sandbox, { filename: 'email-verification37.js' });
    return { button, status, calls, replacements, async submit() {
        const listener = listeners.get('form:submit');
        if (listener) await listener({ preventDefault() {} });
    }, pagehide() { listeners.get('pagehide')?.(); } };
}

const token = 'P'.repeat(43);
const cases = [
    ['fragment cleaned before interaction and never automatically consumed', async () => {
        const page = realm('#token=' + token);
        assert.deepEqual(page.replacements, [[null, '', '/auth/verify-email']]);
        assert.equal(page.calls.length, 0);
        assert.equal(page.button.disabled, false);
        assert.equal(page.status.textContent.includes(token), false);
    }],
    ['missing malformed duplicate and additional fragment fields fail closed', async () => {
        for (const fragment of ['', '#token=short', '#token=' + token + '&token=' + token, '#token=' + token + '&actor=other']) {
            const page = realm(fragment);
            assert.equal(page.replacements.length, 1);
            assert.equal(page.button.disabled, true);
            await page.submit();
            assert.equal(page.calls.length, 0);
        }
    }],
    ['failed URL cleanup discards proof before any network', async () => {
        const page = realm('#token=' + token, { replaceThrows: true });
        assert.equal(page.button.disabled, true);
        await page.submit();
        assert.equal(page.calls.length, 0);
    }],
    ['explicit confirmation sends a closed body and omits auth cookies', async () => {
        const page = realm('#token=' + token);
        await page.submit();
        assert.equal(page.calls.length, 1);
        const request = page.calls[0];
        assert.equal(request.url, '/api/account/security/email/confirm');
        assert.equal(request.config.method, 'POST');
        assert.equal(request.config.credentials, 'omit');
        assert.equal(request.config.cache, 'no-store');
        assert.equal(request.config.referrerPolicy, 'no-referrer');
        assert.equal(request.config.headers['X-MetodoBase-Browser'], '1');
        assert.deepEqual(JSON.parse(request.config.body), { token });
        assert.equal('Authorization' in request.config.headers, false);
        assert.match(page.status.textContent, /Correo confirmado/);
    }],
    ['uncertain transport has no automatic retry or successful confirmation claim', async () => {
        const page = realm('#token=' + token, { networkFails: true });
        await page.submit();
        await page.submit();
        assert.equal(page.calls.length, 1);
        assert.match(page.status.textContent, /No pudimos confirmar/);
        assert.equal(page.button.disabled, true);
    }],
    ['unconfirmed durable outcome remains uncertain after503', async () => {
        const page = realm('#token=' + token, { httpStatus: 503 });
        await page.submit();
        assert.match(page.status.textContent, /No pudimos confirmar/);
        assert.equal(page.calls.length, 1);
    }],
    ['unusable token response never claims contact was confirmed', async () => {
        const page = realm('#token=' + token, { httpStatus: 400 });
        await page.submit();
        assert.match(page.status.textContent, /El enlace no está disponible/);
        assert.equal(page.status.textContent.includes(token), false);
    }],
    ['pagehide invalidates RAM proof and blocks later consumption', async () => {
        const page = realm('#token=' + token);
        page.pagehide();
        await page.submit();
        assert.equal(page.calls.length, 0);
        assert.equal(page.button.disabled, true);
    }]
];

(async () => {
    for (const [name, test] of cases) {
        await test();
        process.stdout.write('PASS ' + name + '\n');
    }
    process.stdout.write(JSON.stringify({ passed: cases.length, failed: 0, runtime: 'Node VM; no native browser' }) + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
