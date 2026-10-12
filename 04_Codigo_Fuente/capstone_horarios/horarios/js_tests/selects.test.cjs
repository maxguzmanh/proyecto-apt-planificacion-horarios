const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/selects.js"), "utf8");
const orden = ["centro", "facultad", "programa", "modalidad", "sede", "periodo", "semestre"];
function setup(restaurar = false) {
    const nodes = new Map();
    const calls = [];
    class Node {
        constructor() { this.value = ""; this.listeners = {}; this.disabled = false; this.children = []; }
        addEventListener(name, fn) { this.listeners[name] = fn; }
        replaceChildren(...children) { this.children = children; this.value = ""; }
        appendChild(child) { this.children.push(child); }
        setAttribute() {}
        focus() {}
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
        return { ok: true, json: async () => [{ id: orden.indexOf(campo) + 1, nombre: campo }] };
    };
    vm.runInNewContext(source, { document: { getElementById: id => nodes.get(id),
        createElement: () => new Node(), addEventListener: (_name, fn) => fn() },
        Option: class { constructor(text, value) { this.text = text; this.value = value; } }, URLSearchParams, fetch });
    return { nodes, calls, form };
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
