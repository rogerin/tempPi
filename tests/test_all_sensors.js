const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
    const elements = new Map(), requests = [], warnings = [], charts = [], posts = [];
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
    const state = { response: [], error: null, snapshotNumber: 0, pending: null,
        sensors: ['temp_forno'], pressureUnit: 'psi' };
    const context = vm.createContext({
        window: { showToast: message => warnings.push(message), location: {},
            URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} } },
        document: { getElementById: getElement,
            createElement: () => ({ click() {} }), body: { appendChild() {}, removeChild() {} },
            addEventListener: (event, callback) => { ready = callback; },
            querySelectorAll: () => state.sensors.map(value => ({ value, addEventListener() {} })),
            querySelector: () => ({ value: state.pressureUnit }) },
        Date: FixedDate, URLSearchParams, setInterval() {}, clearInterval() {},
        console: { log() {}, error() {}, warn() {} },
        Chart: class { constructor(ctx, config) { charts.push(config); } destroy() {} },
        bootstrap: { Modal: class {
            constructor(element) { this.element = element; state.modal = this; }
            show() {}
            hide() { this.element['hidden.bs.modal']?.(); }
            static getInstance() { return state.modal || null; }
        },
            Tab: class { show() {} static getInstance() { return null; } } },
        fetch: async (url, options) => {
            requests.push(url);
            if (options) {
                posts.push({ url, payload: JSON.parse(options.body) });
                return { ok: true, json: async () => ({ success: true }), blob: async () => ({}) };
            }
            if (url.includes('/latest')) return { ok: true, json: async () => ({ pressao_gases: null }) };
            let result = state.response;
            const params = new URL(url, 'http://localhost').searchParams;
            if (params.get('snapshot') === '1') {
                result = { data: state.response, snapshotToken: `snapshot-${++state.snapshotNumber}`,
                    filters: { startTime: params.get('start_time'), endTime: params.get('end_time'),
                        selectedSensors: (params.get('sensors') || '').split(','),
                        pressureUnit: params.get('pressure_unit') || 'psi', groupBy: params.get('group_by') || 'none' } };
            }
            if (state.pending) await new Promise(resolve => state.pending.push(resolve));
            return { ok: !state.error, json: async () => state.error ? { error: state.error } : result };
        },
    });
    vm.runInContext(fs.readFileSync('static/js/all_sensors.js', 'utf8'), context);
    ready();
    return { getElement, requests, warnings, charts, posts, state,
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

test('report cannot silently use edited filters that are not displayed yet', async () => {
    const h = harness();
    h.state.response = [{ timestamp: '2026-10-14 10:00:00', temp_forno: 374.4 }];
    await h.settle();
    await h.getElement('update-chart').click();
    assert.equal(h.charts.at(-1).data.datasets[0].data[0].y, 374.4);
    h.custom('2025-11-03T00:00', '2025-11-04T00:00');
    h.getElement('email-recipient').value = 'client@example.invalid';
    await h.getElement('btn-send-email').click();
    assert.equal(h.posts.length, 0);
    assert.ok(h.warnings.some(message => message.includes('Atualizar')));
});

test('download and email keep the snapshot opened in the modal despite refresh', async () => {
    const h = harness();
    await h.settle();
    h.custom('2026-10-14T10:00', '2026-10-14T11:00');
    h.state.response = [{ timestamp: '2026-10-14 10:00:00', temp_forno: 374.4 }];
    await h.getElement('update-chart').click();
    h.getElement('export-pdf-download').click({ preventDefault() {} });
    await h.getElement('btn-download-pdf').click();
    assert.equal(h.posts.length, 1);
    assert.ok(h.posts[0].payload.snapshotToken);
    h.state.response = [{ timestamp: '2026-10-14 10:00:00', temp_forno: 29.31 }];
    await h.getElement('update-chart').click();
    h.getElement('email-recipient').value = 'client@example.invalid';
    await h.getElement('btn-send-email').click();
    assert.equal(h.posts.length, 2);
    assert.equal(h.posts[1].payload.snapshotToken, h.posts[0].payload.snapshotToken);
    assert.equal(h.getElement('btn-download-pdf').disabled, false);
    await h.getElement('update-chart').click();
    await h.getElement('btn-download-pdf').click();
    assert.equal(h.posts[2].payload.snapshotToken, h.posts[0].payload.snapshotToken);
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

test('a slow earlier query cannot replace the latest chart or report', async () => {
    const h = harness();
    await h.settle();
    h.state.pending = [];
    h.custom('2026-10-14T10:00', '2026-10-14T11:00');
    h.state.response = [{ timestamp: '2026-10-14 10:00:00', temp_forno: 29.31 }];
    const earlier = h.getElement('update-chart').click();
    h.custom('2026-10-14T12:00', '2026-10-14T13:00');
    h.state.response = [{ timestamp: '2026-10-14 12:00:00', temp_forno: 374.4 }];
    const latest = h.getElement('update-chart').click();
    const latestToken = `snapshot-${h.state.snapshotNumber}`;
    h.state.pending[1]();
    await latest;
    h.state.pending[0]();
    await earlier;
    assert.equal(h.charts.at(-1).data.datasets[0].data[0].y, 374.4);
    assert.match(h.getElement('loaded-period').textContent, /12:00/);
    h.getElement('export-pdf-download').click({ preventDefault() {} });
    await h.getElement('btn-download-pdf').click();
    assert.equal(h.posts[0].payload.snapshotToken, latestToken);
});

test('server validation errors are visible to the user', async () => {
    const h = harness();
    await h.settle();
    h.state.error = 'Data inválida para o período.';
    await h.getElement('update-chart').click();
    assert.ok(h.warnings.some(message => message.includes(h.state.error)));
});

test('chart uses Brazil timestamps and BAR values without turning missing pressure into zero', async () => {
    const h = harness();
    await h.settle();
    h.state.sensors = ['pressao_gases', 'velocity'];
    h.state.pressureUnit = 'bar';
    h.state.response = [
        { timestamp: '2026-10-14 10:00:00', pressao_gases: 10, velocity: 12.34 },
        { timestamp: '2026-10-14 10:05:00', pressao_gases: null, velocity: 12.34 },
    ];
    await h.getElement('update-chart').click();
    const pressure = h.charts.at(-1).data.datasets[0].data;
    assert.equal(pressure.length, 1);
    assert.equal(pressure[0].y, 10 * 0.0689476);
    assert.equal(pressure[0].x, Date.parse('2026-10-14T13:00:00Z'));
    assert.match(h.getElement('sensors-data-table-body').innerHTML, /0.69 BAR/);
    assert.match(h.getElement('sensors-data-table-body').innerHTML, /12.34 rpm/);
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
