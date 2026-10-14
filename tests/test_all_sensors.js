const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
    const elements = new Map(), requests = [], warnings = [], charts = [];
    let ready;
    const getElement = id => {
        if (!elements.has(id)) elements.set(id, {
            value: '', style: {}, dataset: {}, innerHTML: '',
            parentElement: { classList: { add() {}, remove() {} }, innerHTML: '' },
            addEventListener(event, callback) { this[event] = callback; },
        });
        return elements.get(id);
    };
    getElement('time-range').value = '24';
    getElement('group-by').value = 'none';
    class FixedDate extends Date {
        constructor(...args) { super(...(args.length ? args : ['2026-10-14T13:00:00Z'])); }
    }
    const state = { response: [], error: null };
    const context = vm.createContext({
        window: { showToast: message => warnings.push(message), location: {} },
        document: { getElementById: getElement,
            addEventListener: (event, callback) => { ready = callback; },
            querySelectorAll: () => [{ value: 'temp_forno', addEventListener() {} }],
            querySelector: () => ({ value: 'psi' }) },
        Date: FixedDate, URLSearchParams, setInterval() {}, clearInterval() {},
        console: { log() {}, error() {}, warn() {} },
        Chart: class { constructor(ctx, config) { charts.push(config); } destroy() {} },
        fetch: async url => {
            requests.push(url);
            if (url.includes('/latest')) return { ok: true, json: async () => ({ pressao_gases: null }) };
            return { ok: !state.error, json: async () => state.error ? { error: state.error } : state.response };
        },
    });
    vm.runInContext(fs.readFileSync('static/js/all_sensors.js', 'utf8'), context);
    ready();
    return { getElement, requests, warnings, charts, state,
        async settle() { await new Promise(resolve => setImmediate(resolve)); },
        custom(start, end) {
            getElement('time-range').value = 'custom';
            getElement('time-range').change();
            getElement('start-datetime').value = start;
            getElement('end-datetime').value = end;
            getElement('start-datetime').change();
        } };
}

test('custom default dates use Brazil wall time, not UTC', async () => {
    const h = harness();
    await h.settle();
    h.getElement('time-range').value = 'custom';
    h.getElement('time-range').change();
    assert.equal(h.getElement('end-datetime').value, '2026-10-14T10:00');
    assert.equal(h.getElement('start-datetime').value, '2026-10-13T10:00');
});

test('invalid custom period shows an error without sending a request', async () => {
    const h = harness();
    await h.settle();
    for (const [start, end] of [['2026-10-15T10:00', '2026-10-14T10:00'], ['', '']]) {
        h.custom(start, end);
        const previous = h.requests.length;
        await h.getElement('update-chart').click();
        assert.equal(h.requests.length, previous);
    }
    assert.equal(h.warnings.length, 2);
});

test('server validation errors are visible to the user', async () => {
    const h = harness();
    await h.settle();
    h.state.error = 'Data inválida para o período.';
    await h.getElement('update-chart').click();
    assert.ok(h.warnings.some(message => message.includes(h.state.error)));
});

test('a valid period after an empty result keeps the chart canvas and renders data', async () => {
    const h = harness();
    await h.settle();
    assert.equal(h.getElement('all-sensors-chart').parentElement.innerHTML, '');
    h.custom('2026-10-14T10:00', '2026-10-14T11:00');
    h.state.response = [{ timestamp: '2026-10-14 10:30:00', temp_forno: 25,
        torre_nivel_1: null, torre_nivel_2: null, torre_nivel_3: null,
        temp_tanque: null, temp_gases: null, pressao_gases: null, velocity: null }];
    await h.getElement('update-chart').click();
    assert.equal(h.charts.length, 1);
    assert.match(h.getElement('sensors-data-table-body').innerHTML, /25/);
    const query = new URL(h.requests.at(-1), 'http://localhost').searchParams;
    assert.equal(query.get('start_time'), '2026-10-14T10:00');
    assert.equal(query.get('end_time'), '2026-10-14T11:00');
});
