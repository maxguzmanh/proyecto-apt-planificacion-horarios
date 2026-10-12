const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/calendario.js"), "utf8");

function setup({ canCreate = true, canEdit = true, rejected = false, networkError = false } = {}) {
    const nodes = new Map();
    const calls = [];
    const modales = new Map();
    let options, draggableOptions, modal, refetches = 0;
    class Node {
        constructor() { this.value = ""; this.listeners = {}; this.children = []; this.textContent = ""; }
        addEventListener(name, fn) { this.listeners[name] = fn; }
        replaceChildren(...children) { this.children = children; }
        appendChild(node) { this.children.push(node); }
        querySelectorAll() { return []; }
        focus() {}
        reset() { node("confirmar-aula").value = ""; node("confirmar-hora-fin").value = ""; }
        reportValidity() { return true; }
        replaceWith(other) { this.replaced = other; }
    }
    function node(id) { if (!nodes.has(id)) { const n = new Node(); n.id = id; nodes.set(id, n); } return nodes.get(id); }
    node("uniplan-calendar").dataset = { canCreate: String(canCreate), canEdit: String(canEdit),
        referenceWeek: "2000-01-03", eventsUrl: "/eventos/", moveUrl: "/mover/", createUrl: "/crear/",
        offerBase: "/ofertas/0/", editBase: "/editar/0/", filters: "semestre=5" };
    const document = {
        addEventListener: (_name, fn) => fn(), getElementById: node,
        querySelector: selector => selector.includes("csrfmiddlewaretoken") ? { value: "csrf-test" } : node(selector),
        querySelectorAll: () => [], createElement: () => new Node(),
    };
    class Calendar {
        constructor(_element, config) { options = config; }
        render() {}
        setOption(name, value) { options[name] = value; }
        refetchEvents() { refetches++; }
    }
    class Draggable { constructor(_element, config) { draggableOptions = config; } }
    class Modal {
        constructor(element) { modal = this; this.element = element; this.visible = false; modales.set(element.id, this); }
        show() { this.visible = true; }
        hide() { this.visible = false; this.element.listeners["hidden.bs.modal"]?.(); }
    }
    const fetch = async (url, request = {}) => {
        calls.push({ url, ...request });
        if (request.method === "POST") {
            if (networkError) throw new Error("Error de red");
            return { ok: !rejected, json: async () => rejected ? { errors: { aula: ["Aula ocupada"] } } : { ok: true, horario_id: 20, message: "Horario creado correctamente." } };
        }
        if (url.includes("/ofertas/")) return { ok: true, json: async () => ({
            oferta_id: 7, codigo_asignatura: "ASIG", asignatura: "Asignatura real", profesor: "Docente real",
            grupos: [{ codigo: "G1", programa: "Programa real" }], modalidad: "Presencial",
            horas_asignadas: null, horas_planificadas: "2", horas_pendientes: null, disponibilidad: [],
            aulas: [{ id: 3, nombre: "Aula real", sede: "Sede real" }],
        }) };
        return { ok: true, text: async () => "panel actualizado" };
    };
    const bootstrap = { Modal };
    vm.runInNewContext(source, { document, fetch, bootstrap, window: { FullCalendar: { Calendar, Draggable }, bootstrap,
        location: { href: "/planificacion/?semestre=5", pathname: "/planificacion/", search: "?semestre=5" } },
        FullCalendar: { Calendar, Draggable },
        Option: class { constructor(text, value) { this.text = text; this.value = value; } },
        DOMParser: class { parseFromString() { return { querySelector: () => node("nuevo-panel") }; } },
    });
    return { node, calls, options, draggableOptions, modal, moverModal: modales.get("mover-horario-modal"), refetches: () => refetches };
}
function recibido() {
    let removed = 0, reverted = 0;
    return { get removed() { return removed; }, get reverted() { return reverted; },
        revert() { reverted++; }, event: { start: new Date(2000, 0, 6, 8),
            extendedProps: { oferta_id: 7, provisional: true }, setProp() {}, remove() { removed++; } } };
}
async function confirmar(app) {
    app.node("confirmar-aula").value = "3";
    app.node("confirmar-hora-fin").value = "09:30";
    await app.node("crear-horario-form").listeners.submit({ preventDefault() {} });
}

test("external drag usa oferta y consulta datos; no guarda al soltar", async () => {
    const app = setup();
    assert.equal(app.draggableOptions.itemSelector, ".offer-drag-card");
    const datos = app.draggableOptions.eventData({ dataset: { ofertaId: "7", asignatura: "Asignatura", profesor: "Docente", grupos: "G1", modalidad: "Presencial" } });
    assert.equal(datos.extendedProps.oferta_id, 7);
    assert.equal(datos.duration, "01:00:00");
    const event = recibido();
    await app.options.eventReceive(event);
    assert.equal(app.calls.filter(c => c.method === "POST").length, 0);
    assert.equal(app.modal.visible, true);
    assert.equal(app.node("confirmar-hora-fin").value, "09:00");
    assert.equal(app.node("confirmar-profesor").textContent, "Docente real");
    assert.equal(app.node("confirmar-carga").textContent, "Carga docente no registrada");
    assert.equal(app.node("confirmar-disponibilidad").children[0].textContent, "Disponibilidad no registrada");
});

test("cancelar elimina provisional sin POST", async () => {
    const app = setup();
    const event = recibido();
    await app.options.eventReceive(event);
    app.modal.hide();
    assert.equal(event.removed, 1);
    assert.equal(app.calls.filter(c => c.method === "POST").length, 0);
    assert.equal(app.options.droppable, true);
});

test("confirmar envía solo cinco campos y refresca calendario y panel", async () => {
    const app = setup();
    const event = recibido();
    await app.options.eventReceive(event);
    await confirmar(app);
    const post = app.calls.find(c => c.method === "POST");
    assert.deepEqual(JSON.parse(post.body), { oferta_id: 7, aula_id: 3, dia: "JU", hora_inicio: "08:00:00", hora_fin: "09:30" });
    assert.equal(post.headers["X-CSRFToken"], "csrf-test");
    assert.equal(event.removed, 1);
    assert.equal(app.modal.visible, false);
    assert.equal(app.refetches(), 1);
    assert.ok(app.node(".academic-subject-list").replaced);
    assert.equal(app.options.eventDurationEditable, false);
});

test("conflicto elimina provisional y muestra el error backend", async () => {
    const app = setup({ rejected: true });
    const event = recibido();
    await app.options.eventReceive(event);
    await confirmar(app);
    assert.equal(event.removed, 1);
    assert.equal(app.refetches(), 1);
    assert.equal(app.modal.visible, false);
    assert.equal(app.node("calendar-message").textContent, "Aula ocupada");
});

test("error de red elimina provisional y recarga eventos", async () => {
    const app = setup({ networkError: true });
    const event = recibido();
    await app.options.eventReceive(event);
    await confirmar(app);
    assert.equal(event.removed, 1);
    assert.equal(app.refetches(), 1);
    assert.equal(app.node("calendar-message").textContent, "Error de red");
});

test("solo lectura no registra Draggable; add permite crear sin change", async () => {
    const lector = setup({ canCreate: false, canEdit: false });
    assert.equal(lector.draggableOptions, undefined);
    assert.equal(lector.options.droppable, false);
    const creador = setup({ canCreate: true, canEdit: false });
    await creador.options.eventReceive(recibido());
    await confirmar(creador);
    assert.equal(creador.options.eventStartEditable, false);
    assert.equal(creador.options.eventDurationEditable, false);
    assert.equal(creador.options.droppable, true);
});


function movimiento() {
    let reverted = 0;
    return { get reverted() { return reverted; }, revert() { reverted++; },
        event: { title: "Asignatura real", start: new Date(2000, 0, 6, 10), end: new Date(2000, 0, 6, 12), extendedProps: { horario_id: 9 } },
        oldEvent: { extendedProps: { codigo_asignatura: "ASIG", profesor: "Docente real", aula: "Sala real",
            dia: "LU", hora_inicio: "08:00:00", hora_fin: "10:00:00" } }
    };
}

test("crear a las 10 propone 11 y solo requiere elegir aula", async () => {
    const app = setup();
    const info = recibido();
    info.event.start = new Date(2000, 0, 6, 10);
    await app.options.eventReceive(info);
    assert.equal(app.node("confirmar-hora-fin").value, "11:00");
    assert.match(app.node("confirmar-inicio").textContent, /10:00–11:00/);
    app.node("confirmar-aula").value = "3";
    await app.node("crear-horario-form").listeners.submit({ preventDefault() {} });
    assert.equal(JSON.parse(app.calls.find(c => c.method === "POST").body).hora_fin, "11:00");
});

test("mover muestra original y propuesta sin POST; cancelar revierte", () => {
    const app = setup();
    const info = movimiento();
    app.options.eventDrop(info);
    assert.equal(app.moverModal.visible, true);
    assert.equal(app.calls.filter(c => c.method === "POST").length, 0);
    assert.equal(app.node("mover-original").textContent, "Lunes · 08:00–10:00");
    assert.equal(app.node("mover-nuevo").textContent, "Jueves · 10:00–12:00");
    assert.equal(app.node("mover-aula").textContent, "Sala real");
    app.moverModal.hide();
    assert.equal(info.reverted, 1);
    assert.equal(app.calls.filter(c => c.method === "POST").length, 0);
    assert.equal(app.options.eventStartEditable, true);
});

test("mover envía POST solo al confirmar y refresca ambos paneles", async () => {
    const app = setup();
    const info = movimiento();
    app.options.eventDrop(info);
    await app.node("mover-confirmar").listeners.click();
    const datos = JSON.parse(app.calls.find(c => c.method === "POST").body);
    assert.equal(datos.horario_id, 9);
    assert.equal(datos.dia, "JU");
    assert.equal(datos.hora_inicio, "10:00:00");
    assert.equal(datos.hora_fin, "12:00:00");
    assert.equal(datos.original.dia, "LU");
    assert.equal(info.reverted, 0);
    assert.equal(app.moverModal.visible, false);
    assert.equal(app.refetches(), 1);
    assert.ok(app.node(".academic-subject-list").replaced);
});

test("mover rechazado revierte y mantiene el error backend", async () => {
    const app = setup({ rejected: true });
    const info = movimiento();
    app.options.eventDrop(info);
    await app.node("mover-confirmar").listeners.click();
    assert.equal(info.reverted, 1);
    assert.equal(app.moverModal.visible, false);
    assert.equal(app.node("calendar-message").textContent, "Aula ocupada");
    assert.equal(app.options.eventDurationEditable, false);
});

test("mover con error de red también revierte", async () => {
    const app = setup({ networkError: true });
    const info = movimiento();
    app.options.eventDrop(info);
    await app.node("mover-confirmar").listeners.click();
    assert.equal(info.reverted, 1);
    assert.equal(app.node("calendar-message").textContent, "Error de red");
    assert.equal(app.options.eventStartEditable, true);
});
