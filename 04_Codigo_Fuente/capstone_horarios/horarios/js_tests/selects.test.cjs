const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/selects.js"), "utf8");
const orden = ["centro", "sede", "facultad", "programa", "periodo", "semestre"];
function setup(restaurar = false, sedeCodigo = "SEDE-ACA") {
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
        urlSedes: "/sede", urlPeriodos: "/periodo", urlSemestres: "/semestre" });
    nodes.set("filtros-planificacion", form);
    const fetch = async url => {
        calls.push(url);
        const campo = url.split("?")[0].slice(1);
        return { ok: true, json: async () => [{ id: orden.indexOf(campo) + 1, nombre: campo, codigo: campo === "sede" ? sedeCodigo : "" }] };
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
    assert.deepEqual(app.calls.map(url => url.split("?")[0]), ["/sede", "/facultad", "/programa", "/periodo", "/semestre"]);
    assert.match(app.calls[3], /sede=2/);
    assert.match(app.calls[4], /periodo=5/);
});

test("restaura contexto en orden y conserva Sede explícita", async () => {
    const app = setup(true);
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(orden.map(id => app.nodes.get(id).value), ["1", "2", "3", "4", "5", "6"]);
    assert.deepEqual(app.calls.map(url => url.split("?")[0]), ["/sede", "/facultad", "/programa", "/periodo", "/semestre"]);
});

test("cambiar programa conserva sede y limpia periodo y semestre", async () => {
    const app = setup(true);
    await new Promise(resolve => setImmediate(resolve));
    await app.nodes.get("programa").listeners.change();
    assert.equal(app.nodes.get("sede").value, "2");
    assert.equal(app.nodes.get("periodo").disabled, false);
    assert.equal(app.nodes.get("periodo").value, "");
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
test("plantilla sin Aplicar filtros, Nueva asignación ni exportación redundante", () => { const html=fs.readFileSync(path.join(__dirname,"../templates/horarios/planificacion.html"),"utf8"); assert.ok(!html.includes("Aplicar filtros")); assert.ok(!html.includes("+ Nueva asignación")); assert.ok(!html.includes("excel-export")); });


test("Centro Tutorial carga Sede sin pedir modalidad", async () => {
    const app = setup(true);
    await new Promise(resolve => setImmediate(resolve));
    await app.nodes.get("centro").listeners.change();
    assert.ok(app.calls.at(-1).startsWith("/sede?"));
    assert.ok(app.calls.every(url => !url.includes("modalidad")));
    assert.equal(app.nodes.has("modalidad"), false);
});
test("Campus Virtual exige elección explícita como cualquier sede", async () => {
    const app = setup(true, "SEDE-VIR");
    await new Promise(resolve => setImmediate(resolve));
    await app.nodes.get("centro").listeners.change();
    assert.equal(app.nodes.get("sede").value, "");
    assert.equal(app.nodes.get("periodo").disabled, true);
    app.nodes.get("sede").value = "2";
    await app.nodes.get("sede").listeners.change();
    assert.equal(app.nodes.get("facultad").disabled, false);
    assert.equal(app.nodes.get("periodo").disabled, true);
});
test("plantilla sin selector ni dependencia de modalidad", () => {
    const html = fs.readFileSync(path.join(__dirname, "../templates/horarios/planificacion.html"), "utf8");
    assert.ok(!html.includes('id="modalidad"'));
    assert.ok(!html.includes("data-selected-modalidad"));
    assert.ok(!html.includes("data-url-modalidades"));
    assert.ok(html.includes("{{ oferta.modalidad.nombre }}"));
});
