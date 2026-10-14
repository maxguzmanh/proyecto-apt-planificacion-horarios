document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("filtros-planificacion");
    if (!form) return;
    const orden = ["centro", "sede", "facultad", "programa", "periodo", "semestre"];
    const selects = orden.map(id => document.getElementById(id));
    const nombres = ["Centro Tutorial", "sede", "facultad", "programa", "periodo", "semestre"];
    const rutas = [null, "urlSedes", "urlFacultades", "urlProgramas", "urlPeriodos", "urlSemestres"];
    const seleccion = orden.map(id => form.dataset["selected" + id[0].toUpperCase() + id.slice(1)] || "");
    let version = 0;
    const estado = document.createElement("p");
    estado.className = "form-help mt-2 mb-0";
    estado.setAttribute("role", "status");
    form.appendChild(estado);
    function limpiarDesde(indice) {
        for (let i = indice; i < selects.length; i++) {
            selects[i].replaceChildren(new Option(`Seleccione ${nombres[i]}...`, ""));
            selects[i].disabled = true;
        }
    }
    async function cargar(indice, actual = "", solicitud = version) {
        if (!selects.slice(0, indice).every(s => s.value)) return false;
        const params = new URLSearchParams();
        orden.slice(0, indice).forEach((campo, i) => params.set(campo, selects[i].value));
        estado.textContent = `Cargando ${nombres[indice]}...`;
        try {
            const response = await fetch(`${form.dataset[rutas[indice]]}?${params}`, { credentials: "same-origin" });
            if (!response.ok) throw new Error();
            let datos = await response.json();
            if (solicitud !== version) return false;
            limpiarDesde(indice);
            datos.forEach(item => { const option = new Option(item.nombre, item.id); option.dataset.codigo = item.codigo || ""; selects[indice].appendChild(option); });
            selects[indice].disabled = datos.length === 0;
            if (actual && datos.some(item => String(item.id) === actual)) selects[indice].value = actual;
            estado.textContent = datos.length ? "" : `No hay opciones de ${nombres[indice]} para este contexto.`;
            return Boolean(selects[indice].value);
        } catch (_) {
            if (solicitud === version) estado.textContent = `No fue posible cargar ${nombres[indice]}. Vuelva a seleccionar el filtro anterior.`;
            return false;
        }
    }
    selects.forEach((select, indice) => select.addEventListener("change", async function () {
        const solicitud = ++version;
        limpiarDesde(indice + 1);
        if (indice + 1 < selects.length && select.value) {
            await cargar(indice + 1, "", solicitud);
        }
        if (solicitud === version && selects.every(s => !s.disabled && s.value)) form.requestSubmit();
        else {
            const calendario = document.getElementById("uniplan-calendar");
            if (calendario) calendario.closest(".planning-calendar-panel").hidden = true;
            const lista = document.querySelector(".academic-subject-list");
            if (lista) lista.replaceChildren();
        }
    }));
    form.addEventListener("submit", function (event) {
        if (selects.some(s => s.disabled || !s.value)) {
            event.preventDefault();
            estado.textContent = "Complete Centro Tutorial, Sede, Facultad, Programa, Periodo y Semestre.";
            const pendiente = selects.find(s => !s.disabled && !s.value);
            if (pendiente) pendiente.focus();
        }
    });
    async function restaurar() {
        limpiarDesde(1);
        if (!seleccion[0]) return;
        selects[0].value = seleccion[0];
        for (let i = 1; i < selects.length; i++) {
            if (!await cargar(i, seleccion[i], version)) break;
        }
    }
    restaurar();
});
