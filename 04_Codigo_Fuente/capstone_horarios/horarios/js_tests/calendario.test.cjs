const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/calendario.js"), "utf8");
function setup({ canCreate = true, canEdit = true, rejected = false, networkError = false } = {}) {
    const nodes = new Map(), calls = [], modales = new Map(), documentListeners = {};
    let options, draggableOptions, refetches = 0;
    class Node {
        constructor(id) { this.id = id; this.value = ""; this.listeners = {}; this.children = []; this.textContent = ""; this.style = {}; this.hidden = true; this.offsetWidth = 180; this.offsetHeight = 80; }
        addEventListener(name, fn) { this.listeners[name] = fn; }
        replaceChildren(...children) { this.children = children; this.value = ""; }
        appendChild(child) { this.children.push(child); }
        querySelectorAll() { return []; }
        setAttribute(name, value) { this[name] = value; }
        getBoundingClientRect() { return { left: 10, bottom: 50 }; }
        contains(target) { return target === this; }
        focus() { this.focused = true; }
        reset() { node("asignar-aula-select").value = ""; }
        reportValidity() { return true; }
        replaceWith(other) { this.replaced = other; }
    }
    function node(id) { if (!nodes.has(id)) nodes.set(id, new Node(id)); return nodes.get(id); }
    node("uniplan-calendar").dataset = { canCreate: String(canCreate), canEdit: String(canEdit),
        referenceWeek: "2000-01-03", eventsUrl: "/eventos/", moveUrl: "/mover/", resizeUrl: "/resize/",
        createUrl: "/crear/", assignUrl: "/asignar/", aulasBase: "/horarios/0/aulas/", filters: "sede=1&semestre=5" };
    const document = { addEventListener: (name, fn) => name === "DOMContentLoaded" ? fn() : documentListeners[name] = fn,
        getElementById: id => !canEdit && ["mover-horario-modal", "asignar-aula-modal"].includes(id) ? null : node(id),
        querySelector: selector => selector.includes("csrfmiddlewaretoken") ? { value: "csrf-test" } : node(selector),
        querySelectorAll: () => [], createElement: () => new Node() };
    class Calendar { constructor(_el, config) { options = config; } render() {} setOption(k, v) { options[k] = v; } refetchEvents() { refetches++; } }
    class Draggable { constructor(_el, config) { draggableOptions = config; } }
    class Modal { constructor(el) { this.el = el; this.visible = false; modales.set(el.id, this); } show() { this.visible = true; } hide() { this.visible = false; this.el.listeners["hidden.bs.modal"]?.(); } }
    const fetch = async (url, request = {}) => {
        calls.push({ url, ...request });
        if (request.method === "POST") {
            if (networkError) throw new Error("Error de red");
            return { ok: !rejected, json: async () => rejected ? { errors: { oferta: ["Conflicto backend"] } } : { ok: true, horario_id: 9, event: { classNames: url.includes("asignar") ? ["evento-completo"] : ["evento-pendiente"] } } };
        }
        if (url.includes("/aulas/")) return { ok: true, json: async () => ({ event: { extendedProps: { aula_id: null } }, aulas: [{ id: 3, nombre: "Aula real", sede: "Sede real" }] }) };
        return { ok: true, text: async () => "panel actualizado" };
    };
    const bootstrap = { Modal };
    vm.runInNewContext(source, { document, fetch, bootstrap, window: { FullCalendar: { Calendar, Draggable }, bootstrap,
        innerWidth: 1200, innerHeight: 900, location: { href: "/planificacion/?sede=1" } },
        FullCalendar: { Calendar, Draggable }, Option: class { constructor(text, value) { this.text = text; this.value = value; } },
        DOMParser: class { parseFromString() { return { querySelector: () => node("nuevo-panel") }; } } });
    return { node, calls, modales, options, draggableOptions, documentListeners, refetches: () => refetches };
}
function evento(aulaId = null) {
    return { id: "9", title: "Asignatura real", start: new Date(2000, 0, 3, 8), end: new Date(2000, 0, 3, 9),
        extendedProps: { horario_id: 9, asignatura: "Asignatura real", codigo_asignatura: "ASIG", profesor: "Docente real",
            grupos: [], modalidad: "Presencial", dia: "LU", hora_inicio: "08:00:00", hora_fin: "09:00:00",
            aula_id: aulaId, aula_pendiente: aulaId === null, aula: aulaId === null ? "Aula pendiente" : "Sala real" } };
}
function cambio(fin = 10) {
    let reverted = 0;
    const actual = evento(); actual.end = new Date(2000, 0, 3, fin);
    return { get reverted() { return reverted; }, revert() { reverted++; }, event: actual, oldEvent: evento() };
}
function recibido(hora = 10, minuto = 0) {
    let removed = 0, reverted = 0;
    return { get removed() { return removed; }, get reverted() { return reverted; }, revert() { reverted++; },
        event: { title: "Asignatura real", start: new Date(2000, 0, 6, hora, minuto), extendedProps: { oferta_id: 7, provisional: true }, setProp() {}, remove() { removed++; } } };
}
function abrirMenu(app, event = evento()) {
    const el = app.node("event-box");
    app.options.eventDidMount({ event, el });
    el.listeners.contextmenu({ preventDefault() {}, clientX: 50, clientY: 50 });
    return el;
}
async function confirmar(app) { await app.node("mover-confirmar").listeners.click(); }

test("tarjeta completa transporta oferta y provisional de una hora", () => {
    const app = setup();
    assert.equal(app.draggableOptions.itemSelector, ".offer-drag-card");
    const data = app.draggableOptions.eventData({ dataset: { ofertaId: "7", asignatura: "Asignatura", profesor: "Docente" } });
    assert.equal(data.duration, "01:00:00"); assert.equal(data.extendedProps.oferta_id, 7);
});

test("drop guarda directamente una hora sin aula ni modal", async () => {
    const app = setup(), info = recibido(10, 30);
    await app.options.eventReceive(info);
    const post = app.calls.find(c => c.method === "POST");
    assert.deepEqual(JSON.parse(post.body), { oferta_id: 7, dia: "JU", hora_inicio: "10:30:00", hora_fin: "11:30:00" });
    assert.equal(post.headers["X-CSRFToken"], "csrf-test");
    assert.equal(info.removed, 1); assert.ok([...app.modales.values()].every(m => !m.visible));
    assert.equal(app.refetches(), 1); assert.ok(app.node(".academic-subject-list").replaced);
});

test("drop rechazado elimina provisional y muestra motivo", async () => {
    const app = setup({ rejected: true }), info = recibido();
    await app.options.eventReceive(info);
    assert.equal(info.removed, 1); assert.equal(app.node("calendar-message").textContent, "Conflicto backend");
});

test("evento pendiente muestra Aula pendiente", () => {
    const app = setup();
    const content = app.options.eventContent({ event: evento() }).domNodes[0];
    assert.equal(content.children[3].textContent, "Aula pendiente");
});

test("clic derecho abre menú y distingue asignar/cambiar aula", () => {
    const app = setup(); abrirMenu(app);
    assert.equal(app.node("calendar-context-menu").hidden, false);
    assert.equal(app.node("context-asignar-aula").textContent, "Asignar aula");
    abrirMenu(app, evento(3));
    assert.equal(app.node("context-asignar-aula").textContent, "Cambiar aula");
});

test("menú también accesible con Mayús F10", () => {
    const app = setup(), el = abrirMenu(app);
    app.documentListeners.keydown({ key: "Escape" });
    assert.equal(app.node("calendar-context-menu").hidden, true);
    el.listeners.keydown({ key: "F10", shiftKey: true, preventDefault() {} });
    assert.equal(app.node("calendar-context-menu").hidden, false);
});

test("asignar aula consulta backend y refresca evento/panel", async () => {
    const app = setup(); abrirMenu(app);
    await app.node("context-asignar-aula").listeners.click();
    assert.equal(app.modales.get("asignar-aula-modal").visible, true);
    app.node("asignar-aula-select").value = "3";
    await app.node("asignar-aula-form").listeners.submit({ preventDefault() {} });
    assert.deepEqual(JSON.parse(app.calls.find(c => c.method === "POST").body), { horario_id: 9, aula_id: 3 });
    assert.equal(app.refetches(), 1); assert.ok(app.node(".academic-subject-list").replaced);
});

test("cancelar aula no hace POST", async () => {
    const app = setup(); abrirMenu(app);
    await app.node("context-asignar-aula").listeners.click();
    app.modales.get("asignar-aula-modal").hide();
    assert.equal(app.calls.filter(c => c.method === "POST").length, 0);
});

test("rechazo de aula muestra error y conserva evento desde backend", async () => {
    const app = setup({ rejected: true }); abrirMenu(app);
    await app.node("context-asignar-aula").listeners.click();
    app.node("asignar-aula-select").value = "3";
    await app.node("asignar-aula-form").listeners.submit({ preventDefault() {} });
    assert.equal(app.node("calendar-message").textContent, "Conflicto backend"); assert.equal(app.refetches(), 1);
});

test("resize abre confirmación sin guardar", () => {
    const app = setup(), info = cambio(); app.options.eventResize(info);
    assert.equal(app.modales.get("mover-horario-modal").visible, true);
    assert.equal(app.calls.length, 0); assert.match(app.node("mover-nuevo").textContent, /08:00–10:00/);
});

test("cancelar resize llama revert sin POST", () => {
    const app = setup(), info = cambio(); app.options.eventResize(info);
    app.modales.get("mover-horario-modal").hide();
    assert.equal(info.reverted, 1); assert.equal(app.calls.length, 0);
});

test("confirmar resize usa endpoint y refresca panel", async () => {
    const app = setup(), info = cambio(); app.options.eventResize(info); await confirmar(app);
    assert.equal(app.calls.find(c => c.method === "POST").url, "/resize/");
    assert.equal(info.reverted, 0); assert.equal(app.refetches(), 1); assert.ok(app.node(".academic-subject-list").replaced);
});

test("resize rechazado llama revert y muestra error", async () => {
    const app = setup({ rejected: true }), info = cambio(); app.options.eventResize(info); await confirmar(app);
    assert.equal(info.reverted, 1); assert.equal(app.node("calendar-message").textContent, "Conflicto backend");
});

test("resize menor una hora revierte antes de confirmación", () => {
    const app = setup(), info = cambio(); info.event.end = new Date(2000, 0, 3, 8, 30);
    app.options.eventResize(info);
    assert.equal(info.reverted, 1); assert.equal(app.modales.get("mover-horario-modal").visible, false);
    assert.equal(app.calls.length, 0);
});

test("eventDrop mantiene confirmación y cancelación", () => {
    const app = setup(), info = cambio(9); info.event.start = new Date(2000, 0, 4, 8); info.event.end = new Date(2000, 0, 4, 9);
    app.options.eventDrop(info);
    assert.equal(app.calls.length, 0); assert.match(app.node("mover-nuevo").textContent, /Martes/);
    app.modales.get("mover-horario-modal").hide(); assert.equal(info.reverted, 1);
});

test("confirmar movimiento usa endpoint de movimiento", async () => {
    const app = setup(), info = cambio(9); app.options.eventDrop(info); await confirmar(app);
    assert.equal(app.calls.find(c => c.method === "POST").url, "/mover/"); assert.equal(info.reverted, 0);
});

test("fallo de red al resize revierte", async () => {
    const app = setup({ networkError: true }), info = cambio(); app.options.eventResize(info); await confirmar(app);
    assert.equal(info.reverted, 1); assert.equal(app.node("calendar-message").textContent, "Error de red");
});

test("solo lectura tiene detalle pero no arrastre ni resize ni aula", () => {
    const app = setup({ canCreate: false, canEdit: false });
    assert.equal(app.draggableOptions, undefined); assert.equal(app.options.eventDurationEditable, false);
    abrirMenu(app); assert.equal(app.node("context-asignar-aula").hidden, true);
    app.node("context-ver-detalle").listeners.click(); assert.equal(app.modales.get("detalle-horario-modal").visible, true);
});
