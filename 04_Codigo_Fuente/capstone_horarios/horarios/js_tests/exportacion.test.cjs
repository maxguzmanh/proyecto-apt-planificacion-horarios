const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/exportacion.js"), "utf8");

function setup(completo = false, conTabla = false, fetchPersonalizado = null, conLibreria = true) {
    const nodes = new Map(), calls = [], descargas = [];
    let options, dt;
    class Node {
        constructor() { this.value = ""; this.disabled = false; this.listeners = {}; this.children = []; this.hidden = false; }
        addEventListener(n, f) { this.listeners[n] = f; }
        replaceChildren(...children) { this.children = children; this.value = ""; }
        appendChild(child) { this.children.push(child); }
    }
    const campos = ["periodo", "centro", "facultad", "programa", "semestre"];
    campos.forEach((c, i) => { const n = new Node(); n.value = completo ? String(i + 1) : ""; nodes.set(`exportar-${c}`, n); });
    const form = new Node(); form.dataset = { urlFacultades: "/facultades", urlProgramas: "/programas", urlSemestres: "/semestres" };
    nodes.set("exportacion-form", form); nodes.set("exportacion-estado", new Node()); nodes.set("exportacion-filtrar", new Node());
    const buscador = new Node();
    const contenedorBotones = new Node();
    if (conTabla) {
        const tabla = new Node(); tabla.dataset = { rowCount: "4", exportUrl: "/planificacion/exportar-excel/?periodo=1&centro=2" };
        nodes.set("exportacion-header-actions", new Node());
        nodes.set("exportacion-tabla", tabla); nodes.set("exportacion-fallback", new Node()); nodes.set("exportacion-tabla-estado", new Node());
    }
    class MockDataTable {
        static Buttons = true;
        constructor(_nodo, config) { options = config; dt = this; this.busqueda = ""; this.cantidad = 4; this.listeners = {}; }
        buttons() { return { container: () => [contenedorBotones] }; }
        search() { return this.busqueda; }
        on(n, f) { this.listeners[n] = f; }
        button() { return { enable: valor => this.habilitado = valor }; }
        rows() { return { count: () => this.cantidad }; }
        table() { return { container: () => ({ querySelector: () => buscador }) }; }
    }
    const fetch = async url => { calls.push(url); return fetchPersonalizado ? fetchPersonalizado(url) : { ok: true, redirected: false, json: async () => [{ id: 20, nombre: "Opción demo" }] }; };
    vm.runInNewContext(source, { document: { getElementById: id => nodes.get(id), addEventListener: (_, f) => f() },
        Option: class { constructor(text, value) { this.text = text; this.value = value; } }, URLSearchParams, URL, fetch,
        DataTable: conLibreria ? MockDataTable : undefined,
        window: { location: { origin: "https://uniplan.example", assign: url => descargas.push(url) } } });
    return { nodes, calls, form, campo: c => nodes.get(`exportar-${c}`), filtrar: nodes.get("exportacion-filtrar"), options, dt, descargas, buscador, contenedorBotones };
}
test("periodo obligatorio impide enviar", () => {
    const app = setup(); let impedido = false;
    app.form.listeners.submit({ preventDefault() { impedido = true; } });
    assert.equal(impedido, true); assert.equal(app.filtrar.disabled, true);
});
test("solo periodo permite filtrar sin otros campos", () => {
    const app = setup(); app.campo("periodo").value = "1"; app.campo("periodo").listeners.change();
    assert.equal(app.filtrar.disabled, false); assert.equal(app.campo("centro").disabled, false);
    assert.equal(app.campo("facultad").disabled, true); assert.equal(app.nodes.has("exportar-nivel"), false);
});
test("centro carga facultad y limpia posteriores", async () => {
    const app = setup(true); await app.campo("centro").listeners.change();
    assert.match(app.calls[0], /^\/facultades\?periodo=1&centro=2/);
    assert.equal(app.campo("programa").value, ""); assert.equal(app.campo("semestre").value, "");
    assert.equal(app.filtrar.disabled, false);
});
test("programa carga semestres sin sede ni nivel", async () => {
    const app = setup(true); await app.campo("programa").listeners.change();
    assert.match(app.calls[0], /^\/semestres\?/); assert.ok(app.calls[0].includes("periodo=1"));
    assert.ok(!app.calls[0].includes("sede")); assert.ok(!app.calls[0].includes("nivel"));
});
test("cambio de periodo limpia contexto", () => {
    const app = setup(true); app.campo("periodo").listeners.change();
    assert.equal(app.campo("centro").value, ""); assert.equal(app.campo("semestre").value, "");
    assert.equal(app.filtrar.disabled, false);
});
test("respuesta tardía no restaura opciones anteriores", async () => {
    let resolver;
    const app = setup(true, false, () => new Promise(r => resolver = r));
    const pendiente = app.campo("centro").listeners.change(); app.campo("periodo").listeners.change();
    resolver({ ok: true, json: async () => [{ id: 99, nombre: "Anterior" }] }); await pendiente;
    assert.ok(!app.campo("facultad").children.some(o => o.value === "99"));
});
test("fallo de red conserva filtrado opcional por periodo", async () => {
    const app = setup(true, false, async () => { throw new Error("red"); }); await app.campo("centro").listeners.change();
    assert.match(app.nodes.get("exportacion-estado").textContent, /No fue posible/); assert.equal(app.filtrar.disabled, false);
});
test("DataTable tiene paginación, búsqueda y botón superior", () => {
    const app = setup(true, true);
    assert.equal(app.options.layout.topStart[0], "pageLength");
    assert.equal(app.options.layout.bottomStart, "info");
    assert.equal(app.options.pageLength, 10); assert.equal(app.options.scrollX, true);
    assert.equal(app.options.layout.topStart[1].buttons[0].text, "Exportar Excel");
    assert.equal(app.options.search.smart, false); assert.equal(app.buscador.maxLength, 200);
    assert.equal(app.nodes.get("exportacion-fallback").hidden, true);
    assert.equal(app.nodes.get("exportacion-header-actions").children[0], app.contenedorBotones);
});
test("botón exporta consulta aplicada y búsqueda mediante backend", () => {
    const app = setup(true, true); app.dt.busqueda = "Aula pendiente";
    app.campo("centro").value = "999";
    app.options.layout.topStart[1].buttons[0].action(null, app.dt);
    const url = new URL(app.descargas[0]);
    assert.equal(url.pathname, "/planificacion/exportar-excel/"); assert.equal(url.searchParams.get("centro"), "2");
    assert.equal(url.searchParams.get("busqueda"), "Aula pendiente"); assert.ok(!url.searchParams.has("page"));
});
test("sin coincidencias deshabilita exportación", () => {
    const app = setup(true, true); app.dt.cantidad = 0; app.dt.listeners.draw(); assert.equal(app.dt.habilitado, false);
});
test("sin librería mantiene tabla y exportación de respaldo", () => {
    const app = setup(true, true, null, false);
    assert.equal(app.nodes.get("exportacion-fallback").hidden, false);
    assert.match(app.nodes.get("exportacion-tabla-estado").textContent, /no está disponible/);
});
test("búsqueda demasiado larga no solicita descarga", () => {
    const app = setup(true, true); app.dt.busqueda = "x".repeat(201);
    app.options.layout.topStart[1].buttons[0].action(null, app.dt); assert.equal(app.descargas.length, 0);
});

test("cabecera de resultados contiene exportación y no contador de filas", () => {
    const html = fs.readFileSync(path.join(__dirname, "../templates/horarios/exportar.html"), "utf8");
    assert.ok(html.indexOf('id="exportacion-header-actions"') < html.indexOf('id="exportacion-tabla"'));
    assert.ok(!html.includes('{{ filas|length }} filas'));
});
