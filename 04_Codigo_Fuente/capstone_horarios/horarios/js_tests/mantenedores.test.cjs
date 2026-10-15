const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/horarios/js/mantenedores.js"), "utf8");

test("inicializa todas las tablas de mantenedores con 10 filas", () => {
    const tablas = [tabla(), tabla()];
    const configuraciones = [];
    function tabla() {
        return {
            dataset: {},
            querySelectorAll: selector => selector === "thead th" ? [{}, {}, {}] : [],
            closest: () => ({ classList: { add() {} } })
        };
    }
    function DataTable(_tabla, opciones) { configuraciones.push(opciones); }
    vm.runInNewContext(source, { DataTable, document: {
        addEventListener: (_evento, callback) => callback(),
        querySelectorAll: selector => selector === "table.maintenance-datatable" ? tablas : []
    }});
    assert.equal(configuraciones.length, 2);
    for (const opciones of configuraciones) {
        assert.equal(opciones.pageLength, 10);
        assert.deepEqual(Array.from(opciones.lengthMenu), [10, 25, 50, 100]);
        assert.equal(opciones.layout.topEnd, "search");
        assert.equal(opciones.columnDefs[0].targets, 2);
        assert.equal(opciones.columnDefs[0].orderable, false);
    }
});

test("semestres alinea número a la izquierda en una columna compacta", () => {
    let opciones;
    const tabla = {
        dataset: { maintainer: "semestres" },
        querySelectorAll: () => [{}, {}, {}],
        closest: () => ({ classList: { add() {} } })
    };
    function DataTable(_tabla, configuracion) { opciones = configuracion; }
    vm.runInNewContext(source, { DataTable, document: {
        addEventListener: (_evento, callback) => callback(),
        querySelectorAll: () => [tabla]
    }});
    const numero = opciones.columnDefs.find(definicion => definicion.targets === 0);
    assert.equal(numero.width, "120px");
    assert.equal(numero.className, "maintenance-column-left");
});

test("los cuatro listados renderizados usan la clase DataTable", () => {
    const archivos = [
        "../../academico/templates/academico/mantenedores/lista_generica.html",
        "../../academico/templates/academico/centros_tutoriales/lista.html",
        "../../academico/templates/academico/sedes/lista.html",
        "../../academico/templates/academico/profesores/lista.html"
    ];
    for (const archivo of archivos) {
        const html = fs.readFileSync(path.join(__dirname, archivo), "utf8");
        assert.match(html, /<table[^>]+maintenance-datatable/);
    }
});
