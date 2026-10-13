const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/selects.js"), "utf8");
const orden = ["centro", "facultad", "programa", "modalidad", "sede", "periodo", "semestre"];
function setup(restaurar = false, modalidadCodigo = "PRE", sedeCodigo = "SEDE-ACA") {
    const nodes = new Map();
    const calls = []; let submissions = 0;
    class Node {
        constructor() { this.value = ""; this.listeners = {}; this.disabled = false; this.children = []; }
        addEventListener(name, fn) { this.listeners[name] = fn; }
        get options() { return this.children; }
        replaceChildren(...children) { this.children = children; this.value = ""; }
        appendChild(child) { this.children.push(child); }
        setAttribute() {}
        focus() {}
        requestSubmit() { submissions++; }
    }
    orden.forEach(id => nodes.set(id, new Node()));
    const form = new Node();
    form.dataset = {};
    orden.forEach((id, i) => {
        const mayuscula = id[0].toUpperCase() + id.slice(1);
        form.dataset["selected" + mayuscula] = restaurar ? String(i + 1) : "";
        form.dataset["url" + mayuscula + (id === "facultad" ? "es" : "s")] = "/" + id;
    });
    Object.assign(form.dataset, { urlFacultades: "/facultad", urlProgramas: "/programa",
        urlModalidades: "/modalidad", urlSedes: "/sede", urlPeriodos: "/periodo", urlSemestres: "/semestre" });
    nodes.set("filtros-planificacion", form);
    const fetch = async url => {
        calls.push(url);
        const campo = url.split("?")[0].slice(1);
        return { ok: true, json: async () => [{ id: orden.indexOf(campo) + 1, nombre: campo, codigo: campo === "modalidad" ? modalidadCodigo : campo === "sede" ? sedeCodigo : "" }] };
    };
    vm.runInNewContext(source, { document: { getElementById: id => nodes.get(id),
        querySelector: () => null, createElement: () => new Node(), addEventListener: (_name, fn) => fn() },
        Option: class { constructor(text, value) { this.text = text; this.value = value; this.dataset = {}; } }, URLSearchParams, fetch });
    return { nodes, calls, form, submissions: () => submissions };
}

test("solo habilita el siguiente filtro; Sede no se selecciona automáticamente", async () => {
    const app = setup();
    for (let i = 0; i < orden.length - 1; i++) {
        const nodo = app.nodes.get(orden[i]);
        nodo.value = String(i + 1);
        await nodo.listeners.change();
        assert.equal(app.nodes.get(orden[i + 1]).disabled, false);
        assert.equal(app.nodes.get(orden[i + 1]).value, "");
        for (let j = i + 2; j < orden.length; j++) assert.equal(app.nodes.get(orden[j]).disabled, true);
    }
    assert.deepEqual(app.calls.map(url => url.split("?")[0]), ["/facultad", "/programa", "/modalidad", "/sede", "/periodo", "/semestre"]);
    assert.match(app.calls[4], /sede=5/);
    assert.match(app.calls[5], /periodo=6/);
});

test("restaura contexto en orden y conserva Sede explícita", async () => {
    const app = setup(true);
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(orden.map(id => app.nodes.get(id).value), ["1", "2", "3", "4", "5", "6", "7"]);
    assert.deepEqual(app.calls.map(url => url.split("?")[0]), ["/facultad", "/programa", "/modalidad", "/sede", "/periodo", "/semestre"]);
});

test("cambiar modalidad limpia sede, periodo y semestre", async () => {
    const app = setup(true);
    await new Promise(resolve => setImmediate(resolve));
    await app.nodes.get("modalidad").listeners.change();
    assert.equal(app.nodes.get("sede").value, "");
    assert.equal(app.nodes.get("periodo").disabled, true);
    assert.equal(app.nodes.get("semestre").disabled, true);
});

test("no permite aplicar un contexto incompleto", () => {
    const app = setup();
    let bloqueado = false;
    app.form.listeners.submit({ preventDefault() { bloqueado = true; } });
    assert.equal(bloqueado, true);
    assert.equal(app.nodes.has("grupo"), false);
});

test("contexto completo se aplica al seleccionar semestre", async () => { const a=setup(true); await new Promise(r=>setImmediate(r)); await a.nodes.get("semestre").listeners.change(); assert.equal(a.submissions(),1); });
test("cambiar semestre vuelve a aplicar sin botón", async () => { const a=setup(true); await new Promise(r=>setImmediate(r)); a.nodes.get("semestre").value="8"; await a.nodes.get("semestre").listeners.change(); assert.equal(a.submissions(),1); });
test("contexto incompleto no envía formulario", async () => { const a=setup(); a.nodes.get("centro").value="1"; await a.nodes.get("centro").listeners.change(); assert.equal(a.submissions(),0); });
test("plantilla sin Aplicar filtros ni Nueva asignación y Excel accesible", () => { const html=fs.readFileSync(path.join(__dirname,"../templates/horarios/planificacion.html"),"utf8"); assert.ok(!html.includes("Aplicar filtros")); assert.ok(!html.includes("+ Nueva asignación")); assert.ok(html.includes("{% url 'exportar_excel' %}?{{ request.GET.urlencode }}")); assert.ok(html.includes('aria-label="Exportar planificación a Excel"')); assert.ok(html.includes("<svg")); });

test("Virtual elige SEDE-VIR y carga automáticamente periodos", async()=>{const a=setup(true,"VIR","SEDE-VIR");await new Promise(r=>setImmediate(r));await a.nodes.get("modalidad").listeners.change();assert.equal(a.nodes.get("sede").value,"5");assert.equal(a.nodes.get("periodo").disabled,false);assert.ok(a.calls.at(-1).startsWith("/periodo"));});
test("Híbrida mantiene selección manual de sede",async()=>{const a=setup(true,"HIB");await new Promise(r=>setImmediate(r));await a.nodes.get("modalidad").listeners.change();assert.equal(a.nodes.get("sede").value,"");assert.equal(a.nodes.get("periodo").disabled,true);});
test("Virtual sin código estable no inventa Campus Virtual",async()=>{const a=setup(true,"VIR","OTRA");await new Promise(r=>setImmediate(r));await a.nodes.get("modalidad").listeners.change();assert.equal(a.nodes.get("sede").value,"");assert.equal(a.nodes.get("periodo").disabled,true);});

test("Presencial no muestra SEDE-VIR incluso ante respuesta incompatible",async()=>{const a=setup(true,"PRE","SEDE-VIR");await new Promise(r=>setImmediate(r));assert.equal(a.nodes.get("sede").disabled,true);assert.equal(a.nodes.get("sede").options.length,1);});
