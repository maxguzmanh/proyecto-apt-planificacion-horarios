const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/calendario.js"), "utf8");
function setup({ canCreate = true, canEdit = true, canDelete = true, rejected = false, networkError = false, disponibilidad = null, deferReferences = false } = {}) {
    const nodes = new Map(), calls = [], modales = new Map(), documentListeners = {}, tips = [], referenceResponses = [];
    let options, draggableOptions, refetches = 0; const added = []; const normalEvents = []; let removedReferences=0;
    class Node {
        constructor(id) { this.id = id; this.value = ""; this.listeners = {}; this.children = []; this.textContent = ""; this.style = {}; this.hidden = true; this.offsetWidth = 180; this.offsetHeight = 80; }
        addEventListener(name, fn) { this.listeners[name] = fn; }
        replaceChildren(...children) { this.children = children; this.value = ""; }
        appendChild(child) { this.children.push(child); }
        querySelectorAll(selector) { return this.id === ".academic-panel" && selector === ".teacher-compact-card" ? [node("teacher-card")] : []; }
        getAttribute(name) { return this[name] || null; }
        setAttribute(name, value) { this[name] = value; }
        getBoundingClientRect() { return { left: 10, bottom: 50 }; }
        contains(target) { return target === this; }
        focus() { this.focused = true; }
        reset() { node("asignar-aula-select").value = ""; }
        reportValidity() { return true; }
        replaceWith(other) { this.replaced = other; }
    }
    function node(id) { if (!nodes.has(id)) nodes.set(id, new Node(id)); return nodes.get(id); }
    node("uniplan-calendar").dataset = { canCreate: String(canCreate), canEdit: String(canEdit), canDelete: String(canDelete), deleteUrl: "/eliminar/",
        referenceWeek: "2000-01-03", eventsUrl: "/eventos/", moveUrl: "/mover/", resizeUrl: "/resize/",
        offerBase: "/ofertas/0/", occupationsBase: "/ofertas/0/ocupaciones/", createUrl: "/crear/", assignUrl: "/asignar/", aulasBase: "/horarios/0/aulas/", filters: "sede=1&semestre=5" };
    node("teacher-card").dataset={ofertaId:"7",asignatura:"Asignatura real",profesor:"Docente real",horas:"8"}; node("teacher-card").title="Docente real · 8 h pendientes\nLunes 08:00–12:00\nDoble clic para ver detalle";
    const document = { addEventListener: (name, fn) => name === "DOMContentLoaded" ? fn() : documentListeners[name] = fn,
        getElementById: id => !canEdit && ["mover-horario-modal", "asignar-aula-modal"].includes(id) ? null : node(id),
        querySelector: selector => selector.includes("csrfmiddlewaretoken") ? { value: "csrf-test" } : node(selector),
        querySelectorAll: () => [], createElement: () => new Node() };
    class Calendar { constructor(_el, config) { options = config; } render() {} setOption(k, v) { options[k] = v; } refetchEvents() { refetches++; } getEvents() { return normalEvents; } addEvent(e) { added.push(e); return { remove(){removedReferences++;} }; } }
    class Draggable { constructor(_el, config) { draggableOptions = config; } }
    class Modal { constructor(el) { this.el = el; this.visible = false; modales.set(el.id, this); } show() { this.visible = true; } hide() { this.visible = false; this.el.listeners["hidden.bs.modal"]?.(); } }
    const fetch = async (url, request = {}) => {
        calls.push({ url, ...request });
        if (request.method === "POST") {
            if (networkError) throw new Error("Error de red");
            return { ok: !rejected, json: async () => rejected ? { errors: { oferta: ["Conflicto backend"] } } : { ok: true, horario_id: 9, event: { classNames: url.includes("asignar") ? ["evento-completo"] : ["evento-pendiente"] } } };
        }
        if (url.includes("/ofertas/") && !url.includes("/ocupaciones/")) return {ok:true,json:async()=>({profesor:"Docente real",asignatura:"Asignatura real",codigo_asignatura:"ASIG",programas:["Programa"],facultades:["Facultad"],grupos:[{codigo:"G1"}],modalidad:"Presencial",horas_asignadas:"10",horas_planificadas:"2",horas_pendientes:"8",disponibilidad:[{nombre_dia:"Lunes",hora_inicio:"08:00:00",hora_fin:"12:00:00"}],ocupaciones:[]})};
        if (url.includes("/ocupaciones/")) return { ok:true, json:async()=>{const datos = ({profesor:"Docente real", disponibilidad: disponibilidad === null ? ["LU","MA","MI","JU","VI","SA","DO"].map(dia=>({dia,hora_inicio:"06:00:00",hora_fin:"22:00:00"})) : disponibilidad, ocupaciones:[ { ...evento(), id:"ocupacion-9", editable:false, startEditable:false, durationEditable:false, classNames:["evento-ocupacion-externa"], extendedProps:{...evento().extendedProps, ocupacion_externa:true} } ]}); if (deferReferences) return new Promise(resolve=>referenceResponses.push({resolve,datos})); return datos; } };
        if (url.includes("/aulas/")) return { ok: true, json: async () => ({ event: { extendedProps: { aula_id: null } }, aulas: [{ id: 3, nombre: "Aula real", sede: "Sede real" }] }) };
        return { ok: true, text: async () => "panel actualizado" };
    };
    class Tooltip { constructor(el, config) { this.el=el;this.config=config;this.visible=false;this.disposed=false;tips.push(this);el.addEventListener("mouseenter",()=>{this.visible=true;});el.addEventListener("mouseleave",()=>{this.visible=false;}); } hide(){this.visible=false;} dispose(){this.disposed=true;this.visible=false;} }
    const bootstrap = { Modal, Tooltip };
    vm.runInNewContext(source, { document, fetch, bootstrap, window: { FullCalendar: { Calendar, Draggable }, bootstrap,
        addEventListener() {}, innerWidth: 1200, innerHeight: 900, location: { href: "/planificacion/?sede=1" } },
        FullCalendar: { Calendar, Draggable }, Option: class { constructor(text, value) { this.text = text; this.value = value; } },
        DOMParser: class { parseFromString() { return { querySelector: () => node("nuevo-panel") }; } } });
    return { node, calls, modales, options, draggableOptions, documentListeners, referenceResponses, tips, added, normalEvents, removedReferences:()=>removedReferences, refetches: () => refetches };
}
function evento(aulaId = null) {
    return { id: "9", title: "Asignatura real", start: new Date(2000, 0, 3, 8), end: new Date(2000, 0, 3, 9),
        extendedProps: { horario_id: 9, oferta_id: 7, asignatura: "Asignatura real", codigo_asignatura: "ASIG", profesor: "Docente real",
            sede: "Sede real", grupos: [], modalidad: "Presencial", dia: "LU", hora_inicio: "08:00:00", hora_fin: "09:00:00",
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

function x(app) { return app.options.eventContent({ event: evento() }).domNodes[0].children.find(n => n.className === "uniplan-event-delete"); }
function pulsarX(app) { x(app).listeners.click({ preventDefault() {}, stopPropagation() {} }); }
test("X aparece con permiso y etiqueta accesible", () => { const b=x(setup()); assert.equal(b["aria-label"],"Eliminar horario"); assert.equal(b.title,"Eliminar horario"); assert.equal(b.textContent,"×"); });
test("X ausente sin permiso de eliminación", () => { assert.equal(x(setup({canDelete:false,canEdit:false})),undefined); });
test("X detiene inicio de arrastre, resize y propagación", () => { const b=x(setup()); for(const k of ["pointerdown","mousedown","touchstart","keydown"]) { let stopped=false; b.listeners[k]({stopPropagation(){stopped=true;}}); assert.ok(stopped); } });
test("X abre confirmación sin POST y muestra sede pendiente", () => { const a=setup(); pulsarX(a); assert.ok(a.modales.get("eliminar-horario-modal").visible); assert.equal(a.calls.length,0); assert.equal(a.node("eliminar-sede").textContent,"Sede real"); assert.equal(a.node("eliminar-aula").textContent,"Aula pendiente"); });
test("cancelar eliminación no modifica evento", () => { const a=setup(); pulsarX(a); a.modales.get("eliminar-horario-modal").hide(); assert.equal(a.calls.length,0); assert.equal(a.refetches(),0); });
test("confirmar envía únicamente horario_id con CSRF", async () => { const a=setup(); pulsarX(a); await a.node("eliminar-confirmar").listeners.click(); const p=a.calls.find(c=>c.method==="POST"); assert.equal(p.url,"/eliminar/"); assert.deepEqual(JSON.parse(p.body),{horario_id:9}); assert.equal(p.headers["X-CSRFToken"],"csrf-test"); });
test("eliminación exitosa refresca calendario", async () => { const a=setup(); pulsarX(a); await a.node("eliminar-confirmar").listeners.click(); assert.equal(a.refetches(),1); assert.equal(a.node("calendar-message").textContent,"Horario eliminado correctamente."); });
test("eliminación exitosa refresca panel", async () => { const a=setup(); pulsarX(a); await a.node("eliminar-confirmar").listeners.click(); assert.ok(a.node(".academic-subject-list").replaced); });
test("error backend conserva evento y permite cancelar", async () => { const a=setup({rejected:true}); pulsarX(a); await a.node("eliminar-confirmar").listeners.click(); assert.equal(a.refetches(),0); assert.ok(a.modales.get("eliminar-horario-modal").visible); assert.equal(a.node("eliminar-error").textContent,"Conflicto backend"); assert.equal(a.node("eliminar-confirmar").disabled,false); });
test("menú contextual reutiliza confirmación de X", async () => { const a=setup(); abrirMenu(a); a.node("context-eliminar-horario").listeners.click(); assert.ok(a.modales.get("eliminar-horario-modal").visible); assert.equal(a.calls.length,0); await a.node("eliminar-confirmar").listeners.click(); assert.equal(a.calls.find(c=>c.method==="POST").url,"/eliminar/"); });

async function iniciarDrag(a) { const card={dataset:{ofertaId:"7"}}; a.node(".academic-panel").listeners.pointerdown({target:{closest:()=>card},clientX:0,clientY:0,pointerId:1,button:0}); a.documentListeners.pointermove({clientX:10,clientY:0,pointerId:1}); await new Promise(r=>setImmediate(r)); }
test("iniciar drag carga ocupaciones desde oferta", async()=>{ const a=setup(); await iniciarDrag(a); assert.ok(a.calls.some(c=>c.url==="/ofertas/7/ocupaciones/?sede=1&semestre=5")); });
test("referencia externa no permite editar y no tiene X", async()=>{ const a=setup(); await iniciarDrag(a); assert.equal(a.added[0].editable,false); assert.equal(a.added[0].durationEditable,false); assert.equal(a.added[0].startEditable,false); const content=a.options.eventContent({event:a.added[0]}).domNodes[0]; assert.equal(content.children[0].textContent,"OCUPADO EN OTRO CONTEXTO"); assert.ok(!content.children.some(n=>n.className==="uniplan-event-delete")); });
test("horario normal no se duplica como referencia", async()=>{ const a=setup(); a.normalEvents.push(evento()); await iniciarDrag(a); assert.equal(a.added.length,0); });
test("terminar drag limpia referencias", async()=>{ const a=setup(); await iniciarDrag(a); a.documentListeners.pointerup(); assert.equal(a.removedReferences(),1); });
test("cancelar drag limpia referencias", async()=>{ const a=setup(); await iniciarDrag(a); a.documentListeners.pointercancel(); assert.equal(a.removedReferences(),1); });
test("ocupación abre detalle de solo lectura sin menú", async()=>{ const a=setup(); await iniciarDrag(a); const e=a.added[0]; a.options.eventClick({event:e}); assert.ok(a.modales.get("detalle-horario-modal").visible); abrirMenu(a,e); assert.equal(a.node("calendar-context-menu").hidden,true); });

test("respuesta tardía después de terminar drag no agrega referencias", async()=>{ const a=setup(); const card={dataset:{ofertaId:"7"}}; a.node(".academic-panel").listeners.pointerdown({target:{closest:()=>card},clientX:0,clientY:0,pointerId:1,button:0}); a.documentListeners.pointermove({clientX:10,clientY:0,pointerId:1}); a.documentListeners.pointerup(); await new Promise(r=>setImmediate(r)); assert.equal(a.added.length,0); });

async function doble(a) { a.node(".academic-panel").listeners.dblclick({target:{closest:()=>a.node("teacher-card")},preventDefault(){},stopPropagation(){}}); await new Promise(r=>setImmediate(r)); }
test("doble clic abre modal con horas reales",async()=>{ const a=setup(); await doble(a); assert.ok(a.modales.get("docente-modal").visible);assert.equal(a.node("docente-pendientes").textContent,"8 h");assert.equal(a.node("docente-carga").textContent,"10 h"); });
test("doble clic no crea horario ni inicia ocupaciones de drag",async()=>{ const a=setup(); await doble(a); assert.ok(!a.calls.some(c=>c.method==="POST"||c.url.includes("ocupaciones"))); });
test("drag real no abre modal docente",async()=>{ const a=setup();await iniciarDrag(a);assert.equal(a.modales.get("docente-modal").visible,false); });
test("doble clic posterior a un drag se ignora",async()=>{ const a=setup(); const card=a.node("teacher-card");a.node(".academic-panel").listeners.pointerdown({target:{closest:()=>card},clientX:0,clientY:0,pointerId:1,button:0});a.documentListeners.pointermove({clientX:10,clientY:0,pointerId:1});a.documentListeners.pointerup();await doble(a);assert.equal(a.modales.get("docente-modal").visible,false); });
test("tooltip docente muestra pendientes y se oculta al salir",()=>{ const a=setup();const tip=a.tips[0];a.node("teacher-card").listeners.mouseenter();assert.equal(tip.visible,true);assert.ok(tip.config.title.includes("8 h pendientes"));a.node("teacher-card").listeners.mouseleave();assert.equal(tip.visible,false); });
test("tooltip horario incluye contexto",()=>{ const a=setup();const el=a.node("box-tip");a.options.eventDidMount({event:evento(),el});const tip=a.tips.at(-1);assert.ok(tip.config.title.includes("Sede real"));assert.ok(tip.config.title.includes("08:00–09:00")); });
test("tooltip ocupación externa indica otro contexto",async()=>{ const a=setup();await iniciarDrag(a);a.options.eventDidMount({event:a.added[0],el:a.node("external-tip")});assert.ok(a.tips.at(-1).config.title.startsWith("OCUPADO EN OTRO CONTEXTO")); });
test("desmontar evento destruye tooltip",()=>{ const a=setup();const el=a.node("remove-tip");a.options.eventDidMount({event:evento(),el});const tip=a.tips.at(-1);a.options.eventWillUnmount({el});assert.equal(tip.disposed,true); });
test("cerrar modal docente no altera calendario",async()=>{const a=setup();await doble(a);a.modales.get("docente-modal").hide();assert.equal(a.refetches(),0);assert.ok(!a.calls.some(c=>c.method==="POST"));});
test("detalle docente accesible mediante Enter",async()=>{const a=setup();a.node(".academic-panel").listeners.keydown({target:{closest:()=>a.node("teacher-card")},key:"Enter",preventDefault(){}});await new Promise(r=>setImmediate(r));assert.ok(a.modales.get("docente-modal").visible);});

function grises(a){return a.added.filter(e=>e.display==="background");}
test("drag dibuja complemento de disponibilidad parcial",async()=>{const a=setup({disponibilidad:[{dia:"LU",hora_inicio:"09:00:00",hora_fin:"13:00:00"}]});await iniciarDrag(a);const lunes=grises(a).filter(e=>e.start.getDay()===1);assert.deepEqual(lunes.map(e=>[e.start.getHours(),e.end.getHours()]),[[6,9],[13,22]]);assert.ok(grises(a).every(e=>e.editable===false));});
test("día sin disponibilidad completamente gris en rango visual",async()=>{const a=setup({disponibilidad:[]});await iniciarDrag(a);assert.equal(grises(a).length,7);assert.ok(grises(a).every(e=>e.start.getHours()===6&&e.end.getHours()===22));});
test("varios bloques dejan varias franjas libres",async()=>{const a=setup({disponibilidad:[{dia:"LU",hora_inicio:"09:00:00",hora_fin:"11:00:00"},{dia:"LU",hora_inicio:"13:00:00",hora_fin:"15:00:00"}]});await iniciarDrag(a);assert.deepEqual(grises(a).filter(e=>e.start.getDay()===1).map(e=>[e.start.getHours(),e.end.getHours()]),[[6,9],[11,13],[15,22]]);});
test("disponibilidad se recorta al rango y une bloques consecutivos",async()=>{const a=setup({disponibilidad:[{dia:"LU",hora_inicio:"05:00:00",hora_fin:"10:00:00"},{dia:"LU",hora_inicio:"10:00:00",hora_fin:"23:00:00"}]});await iniciarDrag(a);assert.equal(grises(a).filter(e=>e.start.getDay()===1).length,0);});
test("gris convive con ocupaciones y conserva eventos normales",async()=>{const a=setup({disponibilidad:[]});a.normalEvents.push({...evento(),id:"otro",extendedProps:{...evento().extendedProps,horario_id:99}});await iniciarDrag(a);assert.ok(a.added.some(e=>e.extendedProps.ocupacion_externa));assert.equal(grises(a).length,7);assert.equal(a.normalEvents.length,1);});
test("fin y cancelación limpian gris y ocupación",async()=>{for(const nombre of ["pointerup","pointercancel"]){const a=setup({disponibilidad:[]});await iniciarDrag(a);a.documentListeners[nombre]();assert.equal(a.removedReferences(),a.added.length);}});
test("respuesta tardía no vuelve a pintar gris",async()=>{const a=setup({disponibilidad:[]});const card={dataset:{ofertaId:"7"}};a.node(".academic-panel").listeners.pointerdown({target:{closest:()=>card},clientX:0,clientY:0,pointerId:1});a.documentListeners.pointermove({clientX:10,clientY:0,pointerId:1});a.documentListeners.pointercancel();await new Promise(r=>setImmediate(r));assert.equal(a.added.length,0);});
test("drop gris llega al backend y su rechazo retira provisional",async()=>{const a=setup({disponibilidad:[],rejected:true});await iniciarDrag(a);const info=recibido();await a.options.eventReceive(info);assert.ok(a.calls.some(c=>c.method==="POST"));assert.equal(info.removed,1);assert.equal(a.removedReferences(),a.added.length);});
test("bloques externos contrastan y siguen diferenciados",()=>{const css=fs.readFileSync(path.join(__dirname,"../static/horarios/css/estilos.css"),"utf8");assert.ok(css.includes("opacity: 1"));assert.ok(css.includes("rgba(203, 216, 232, .90)"));assert.ok(css.includes("border: 2px dashed"));assert.ok(css.includes(".zona-no-disponible"));});
test("gris no abre detalle ni ofrece eliminación",async()=>{const a=setup({disponibilidad:[]});await iniciarDrag(a);const e=grises(a)[0];assert.equal(a.options.eventContent({event:e}).domNodes.length,0);a.options.eventClick({event:e});assert.equal(a.modales.get("detalle-horario-modal").visible,false);});

test("mover evento existente carga gris y ocupaciones sin permiso crear",async()=>{const a=setup({canCreate:false,disponibilidad:[]});await a.options.eventDragStart({event:evento()});assert.equal(grises(a).length,7);assert.ok(a.added.some(e=>e.extendedProps.ocupacion_externa));assert.equal(a.calls[0].url,"/ofertas/7/ocupaciones/?sede=1&semestre=5");});
test("resize carga las mismas referencias",async()=>{const a=setup({disponibilidad:[]});await a.options.eventResizeStart({event:evento()});assert.equal(grises(a).length,7);assert.ok(a.added.some(e=>e.extendedProps.ocupacion_externa));});
test("cancelar drag existente limpia referencias y respuestas pendientes",async()=>{const a=setup({disponibilidad:[]});await a.options.eventDragStart({event:evento()});a.options.eventDragStop();assert.equal(a.removedReferences(),a.added.length);assert.equal(a.calls.filter(c=>c.method==="POST").length,0);});
test("cancelar resize limpia referencias",async()=>{const a=setup({disponibilidad:[]});await a.options.eventResizeStart({event:evento()});a.options.eventResizeStop();assert.equal(a.removedReferences(),a.added.length);});
test("cancelar confirmación de movimiento revierte y limpia",async()=>{const a=setup({disponibilidad:[]});await a.options.eventDragStart({event:evento()});const info=cambio();a.options.eventDrop(info);a.modales.get("mover-horario-modal").hide();assert.equal(info.reverted,1);assert.equal(a.removedReferences(),a.added.length);});
test("rechazo backend en movimiento revierte y limpia",async()=>{const a=setup({disponibilidad:[],rejected:true});await a.options.eventDragStart({event:evento()});const info=cambio();a.options.eventDrop(info);await confirmar(a);assert.equal(info.reverted,1);assert.equal(a.removedReferences(),a.added.length);});
test("rechazo backend en resize revierte y limpia",async()=>{const a=setup({disponibilidad:[],rejected:true});await a.options.eventResizeStart({event:evento()});const info=cambio();a.options.eventResize(info);await confirmar(a);assert.equal(info.reverted,1);assert.equal(a.removedReferences(),a.added.length);});
test("respuesta tardía de drag anterior no contamina resize activo",async()=>{const a=setup({disponibilidad:[],deferReferences:true});a.options.eventDragStart({event:evento()});await new Promise(r=>setImmediate(r));a.options.eventDragStop();a.options.eventResizeStart({event:evento()});await new Promise(r=>setImmediate(r));a.referenceResponses[0].resolve(a.referenceResponses[0].datos);await new Promise(r=>setImmediate(r));assert.equal(a.added.length,0);a.referenceResponses[1].resolve(a.referenceResponses[1].datos);await new Promise(r=>setImmediate(r));assert.equal(grises(a).length,7);});
test("respuesta posterior al fin de resize no pinta referencias",async()=>{const a=setup({disponibilidad:[],deferReferences:true});a.options.eventResizeStart({event:evento()});await new Promise(r=>setImmediate(r));a.options.eventResizeStop();a.referenceResponses[0].resolve(a.referenceResponses[0].datos);await new Promise(r=>setImmediate(r));assert.equal(a.added.length,0);});
test("referencias de solo lectura no pueden iniciar interacción",async()=>{const a=setup();for(const p of [{ocupacion_externa:true},{disponibilidad_visual:true},{provisional:true}])await a.options.eventDragStart({event:{extendedProps:{oferta_id:7,...p}}});assert.equal(a.calls.length,0);});
test("confirmar resize limpia y actualiza sin revertir",async()=>{const a=setup({disponibilidad:[]});await a.options.eventResizeStart({event:evento()});const info=cambio();a.options.eventResize(info);await confirmar(a);assert.equal(info.reverted,0);assert.equal(a.removedReferences(),a.added.length);assert.equal(a.refetches(),1);});
