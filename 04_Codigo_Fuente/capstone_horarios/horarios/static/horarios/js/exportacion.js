document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("exportacion-form");
    if (!form) return;
    const campos = ["centro", "facultad", "programa", "semestre"];
    const selects = Object.fromEntries(["periodo", ...campos].map(c => [c, document.getElementById(`exportar-${c}`)]));
    const rutas = { facultad: "urlFacultades", programa: "urlProgramas", semestre: "urlSemestres" };
    const estado = document.getElementById("exportacion-estado");
    const filtrar = document.getElementById("exportacion-filtrar");
    let version = 0;
    function actualizar() {
        campos.forEach((c, i) => {
            selects[c].disabled = !selects.periodo.value || campos.slice(0, i).some(p => !selects[p].value);
        });
        filtrar.disabled = !selects.periodo.value;
    }
    function limpiarDesde(indice) {
        campos.slice(indice).forEach(c => selects[c].replaceChildren(new Option("Seleccione una opción...", "")));
    }
    async function cargar(campo, solicitud) {
        const i = campos.indexOf(campo);
        if (!selects.periodo.value || campos.slice(0, i).some(c => !selects[c].value)) return;
        const params = new URLSearchParams({ periodo: selects.periodo.value });
        campos.slice(0, i).forEach(c => params.set(c, selects[c].value));
        estado.textContent = "Cargando opciones académicas...";
        selects[campo].disabled = true;
        try {
            const response = await fetch(`${form.dataset[rutas[campo]]}?${params}`, { credentials: "same-origin" });
            if (!response.ok || response.redirected) throw new Error();
            const datos = await response.json();
            if (solicitud !== version) return;
            selects[campo].replaceChildren(new Option("Seleccione una opción...", ""));
            datos.forEach(d => selects[campo].appendChild(new Option(d.nombre, String(d.id))));
            estado.textContent = datos.length ? "" : "No hay opciones académicas para este contexto.";
        } catch (_) {
            if (solicitud === version) estado.textContent = "No fue posible cargar las opciones. Vuelva a seleccionar el filtro anterior.";
        }
        if (solicitud === version) actualizar();
    }
    selects.periodo.addEventListener("change", () => { ++version; limpiarDesde(1); selects.centro.value = ""; estado.textContent = ""; actualizar(); });
    campos.forEach((campo, i) => selects[campo].addEventListener("change", async () => {
        const solicitud = ++version;
        limpiarDesde(i + 1); actualizar();
        if (i < campos.length - 1) await cargar(campos[i + 1], solicitud);
    }));
    form.addEventListener("submit", event => {
        if (filtrar.disabled) { event.preventDefault(); estado.textContent = "Seleccione un periodo académico para filtrar."; }
    });
    actualizar();
    const tabla = document.getElementById("exportacion-tabla");
    if (!tabla) return;
    const tablaEstado = document.getElementById("exportacion-tabla-estado");
    const fallback = document.getElementById("exportacion-fallback");
    if (typeof DataTable !== "function" || !DataTable.Buttons) {
        tablaEstado.textContent = "La tabla interactiva no está disponible. Puede consultar las filas y usar el botón Exportar Excel.";
        return;
    }
    const dataTable = new DataTable(tabla, {
        scrollX: true, order: [], pageLength: 10, lengthMenu: [10, 25, 50, 100],
        search: { smart: false, regex: false, caseInsensitive: true },
        layout: {
            topStart: ["pageLength", { buttons: [{
                text: "Exportar Excel", className: "btn btn-primary", enabled: Number(tabla.dataset.rowCount) > 0,
                action: function (_event, dt) {
                    const busqueda = dt.search();
                    if (busqueda.length > 200) { tablaEstado.textContent = "La búsqueda admite hasta 200 caracteres."; return; }
                    const url = new URL(tabla.dataset.exportUrl, window.location.origin);
                    if (busqueda) url.searchParams.set("busqueda", busqueda); else url.searchParams.delete("busqueda");
                    // Exportar toda la consulta validada, nunca solo la página visible.
                    window.location.assign(url.toString());
                }
            }] }],
            topEnd: "search", bottomStart: "info", bottomEnd: "paging"
        },
        language: {
            search: "Buscar en resultados:", lengthMenu: "Mostrar _MENU_ filas", info: "_START_–_END_ de _TOTAL_ filas",
            infoEmpty: "0 filas", infoFiltered: "(de _MAX_ filas)", zeroRecords: "No hay coincidencias para esta búsqueda.",
            emptyTable: "No hay horarios para los filtros seleccionados.",
            paginate: { first: "Primera", last: "Última", next: "Siguiente", previous: "Anterior" }
        }
    });
    const accionesCabecera = document.getElementById("exportacion-header-actions");
    const botones = dataTable.buttons().container();
    const contenedorBotones = botones.nodeType ? botones : botones[0];
    if (accionesCabecera && contenedorBotones) accionesCabecera.appendChild(contenedorBotones);
    if (fallback) fallback.hidden = true;
    dataTable.on("draw", () => dataTable.button(0).enable(dataTable.rows({ search: "applied" }).count() > 0));
    const buscador = dataTable.table().container().querySelector('input[type="search"]');
    if (buscador) buscador.maxLength = 200;
});
