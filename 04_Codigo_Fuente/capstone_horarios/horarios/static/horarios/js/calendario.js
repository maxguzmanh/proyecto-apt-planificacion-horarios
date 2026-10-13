document.addEventListener("DOMContentLoaded", function () {
    const element = document.getElementById("uniplan-calendar");
    if (!element) return;
    const message = document.getElementById("calendar-message");
    function mostrarMensaje(texto, tipo = "danger") {
        message.className = `alert alert-${tipo}`;
        message.textContent = texto;
        message.hidden = false;
    }
    if (!window.FullCalendar) { mostrarMensaje("No fue posible cargar el calendario. Recargue la página."); return; }
    const editable = element.dataset.canEdit === "true";
    const puedeEliminar = element.dataset.canDelete === "true";
    const puedeCrear = element.dataset.canCreate === "true";
    const dias = ["DO", "LU", "MA", "MI", "JU", "VI", "SA"];
    const nombresDias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    let guardando = false, cambio = null, enviandoCambio = false;
    let eventoMenu = null, aulaPendiente = null, solicitudAula = 0, enviandoAula = false;
    const menu = document.getElementById("calendar-context-menu");
    const menuAula = document.getElementById("context-asignar-aula");
    const moverElement = document.getElementById("mover-horario-modal");
    const moverModal = moverElement && window.bootstrap ? new bootstrap.Modal(moverElement, { backdrop: "static", keyboard: false }) : null;
    const confirmarCambio = document.getElementById("mover-confirmar");
    const aulaElement = document.getElementById("asignar-aula-modal");
    const aulaModal = aulaElement && window.bootstrap ? new bootstrap.Modal(aulaElement, { backdrop: "static", keyboard: false }) : null;
    const aulaForm = document.getElementById("asignar-aula-form");
    const aulaSelect = document.getElementById("asignar-aula-select");
    const aulaGuardar = document.getElementById("asignar-aula-guardar");
    const detalleElement = document.getElementById("detalle-horario-modal");
    const detalleModal = detalleElement && window.bootstrap ? new bootstrap.Modal(detalleElement) : null;
    let eventoEliminar = null, enviandoEliminar = false;
    const eliminarElement = document.getElementById("eliminar-horario-modal");
    const eliminarModal = puedeEliminar && eliminarElement && window.bootstrap ? new bootstrap.Modal(eliminarElement, { backdrop: "static", keyboard: false }) : null;
    const eliminarConfirmar = document.getElementById("eliminar-confirmar");
    function abrirEliminar(evento) {
        if (!puedeEliminar || guardando || (evento.extendedProps.provisional || evento.extendedProps.ocupacion_externa) || !eliminarModal) return;
        bloquear(true); eventoEliminar = evento;
        const p = evento.extendedProps;
        texto("eliminar-asignatura", `${p.codigo_asignatura} · ${evento.title}`);
        texto("eliminar-profesor", p.profesor);
        texto("eliminar-programa", [...new Set(p.grupos.map(g => g.programa))].join(", ") || "Sin programa relacionado");
        texto("eliminar-grupos", p.grupos.map(g => g.codigo).join(", ") || "Sin grupos relacionados");
        texto("eliminar-sede", p.sede); texto("eliminar-aula", p.aula || "Aula pendiente");
        texto("eliminar-dia", nombresDias[dias.indexOf(p.dia)]);
        texto("eliminar-inicio", p.hora_inicio.slice(0, 5)); texto("eliminar-fin", p.hora_fin.slice(0, 5));
        document.getElementById("eliminar-error").hidden = true;
        eliminarModal.show();
    }
    if (eliminarModal) {
        eliminarElement.addEventListener("hidden.bs.modal", function () { eventoEliminar = null; if (!enviandoEliminar) bloquear(false); });
        eliminarConfirmar.addEventListener("click", async function () {
            if (!eventoEliminar || enviandoEliminar) return;
            enviandoEliminar = true; eliminarConfirmar.disabled = true;
            eliminarElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = true; });
            try {
                const datos = await json(element.dataset.deleteUrl, post({ horario_id: Number(eventoEliminar.id) }));
                if (!datos.ok) throw new Error("No se pudo eliminar el horario.");
                eventoEliminar = null; eliminarModal.hide();
                mostrarMensaje("Horario eliminado correctamente.", "success"); await refrescar();
            } catch (error) {
                const aviso = document.getElementById("eliminar-error"); aviso.textContent = error.message; aviso.hidden = false;
            } finally {
                enviandoEliminar = false; eliminarConfirmar.disabled = false;
                eliminarElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = false; });
                if (!eventoEliminar) bloquear(false);
            }
        });
    }
    const panelDocente = document.querySelector(".academic-panel");
    const docenteElement = document.getElementById("docente-modal");
    const docenteModal = docenteElement && window.bootstrap ? new bootstrap.Modal(docenteElement) : null;
    let versionDocente = 0, ultimoDrag = null;
    const tooltipsDocentes = new Map(), tooltipsEventos = new Map();
    function tooltip(nodo, contenido) {
        if (window.bootstrap && bootstrap.Tooltip) return new bootstrap.Tooltip(nodo, { title: contenido, html: false, trigger: "hover focus", container: "body" });
        nodo.setAttribute("title", contenido); return null;
    }
    function prepararTooltipsDocentes() {
        tooltipsDocentes.forEach(t => t && t.dispose()); tooltipsDocentes.clear();
        panelDocente.querySelectorAll(".teacher-compact-card").forEach(card => {
            tooltipsDocentes.set(card, tooltip(card, card.getAttribute("data-bs-original-title") || card.getAttribute("title") || ""));
        });
    }
    function ocultarTooltips() {
        tooltipsDocentes.forEach(t => t && t.hide()); tooltipsEventos.forEach(t => t && t.hide());
    }
    function lista(id, valores, vacio) {
        const nodo = document.getElementById(id); nodo.replaceChildren();
        (valores.length ? valores : [vacio]).forEach(valor => { const li = document.createElement("li"); li.textContent = valor; nodo.appendChild(li); });
    }
    function horas(valor, ausencia) { return valor === null ? ausencia : `${Number(valor)} h`; }
    async function verDocente(card) {
        if (guardando || !docenteModal || (gesto && gesto.iniciado) || (ultimoDrag && ultimoDrag.card === card && Date.now() - ultimoDrag.fecha < 500)) return;
        const version = ++versionDocente;
        limpiarReferencias(); ocultarTooltips();
        texto("docente-estado", "Consultando detalle…");
        for (const id of ["profesor","area","asignatura","codigo","programa","facultad","grupos","modalidad","carga","planificadas","pendientes"]) texto(`docente-${id}`, "");
        lista("docente-disponibilidad", [], "Consultando…"); lista("docente-ocupaciones", [], "Consultando…");
        docenteModal.show();
        try {
            const d = await json(urlContexto(element.dataset.offerBase.replace("/0/", `/${card.dataset.ofertaId}/`)));
            if (version !== versionDocente) return;
            texto("docente-area", d.area_academica || "Área académica no registrada");
            texto("docente-estado", ""); texto("docente-profesor", d.profesor); texto("docente-asignatura", d.asignatura); texto("docente-codigo", d.codigo_asignatura);
            texto("docente-programa", d.programas.join(", ")); texto("docente-facultad", d.facultades.join(", "));
            texto("docente-grupos", d.grupos.map(g => g.codigo).join(", ")); texto("docente-modalidad", d.modalidad);
            texto("docente-carga", horas(d.horas_asignadas, "Carga docente no registrada")); texto("docente-planificadas", horas(d.horas_planificadas, "Sin calcular")); texto("docente-pendientes", horas(d.horas_pendientes, "Sin carga"));
            lista("docente-disponibilidad", d.disponibilidad.map(b => `${b.nombre_dia} ${b.hora_inicio.slice(0,5)}–${b.hora_fin.slice(0,5)}`), "Disponibilidad no registrada");
            lista("docente-ocupaciones", d.ocupaciones.map(e => `${e.title} · ${e.extendedProps.sede} · ${nombresDias[dias.indexOf(e.extendedProps.dia)]} ${e.extendedProps.hora_inicio.slice(0,5)}–${e.extendedProps.hora_fin.slice(0,5)}`), "Sin horarios planificados");
        } catch (error) { if (version === versionDocente) texto("docente-estado", error.message); }
    }
    if (docenteModal) docenteElement.addEventListener("hidden.bs.modal", () => { ++versionDocente; });
    panelDocente.addEventListener("dblclick", function (ev) { const card = ev.target.closest(".teacher-compact-card"); if (!card) return; ev.preventDefault(); ev.stopPropagation(); verDocente(card); });
    panelDocente.addEventListener("keydown", function (ev) { const card = ev.target.closest(".teacher-compact-card"); if (card && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); verDocente(card); } });
    prepararTooltipsDocentes();
    function texto(id, valor) { document.getElementById(id).textContent = valor; }
    function hora(fecha) { return [fecha.getHours(), fecha.getMinutes(), fecha.getSeconds()].map(n => String(n).padStart(2, "0")).join(":"); }
    function urlContexto(url) { return `${url}?${element.dataset.filters}`; }
    function post(datos) { return { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": document.querySelector("#calendar-csrf [name=csrfmiddlewaretoken]").value }, body: JSON.stringify(datos) }; }
    async function json(url, opciones = {}) {
        const response = await fetch(url, { credentials: "same-origin", ...opciones });
        let datos;
        try { datos = await response.json(); }
        catch (_) { throw new Error("No se pudo confirmar la operación. Actualice el calendario para comprobar su estado."); }
        if (!response.ok) {
            let mensaje = Object.values(datos.errors || {}).flat().join(" ") || "No fue posible guardar.";
            if (datos.conflicto_profesor) {
                const c = datos.conflicto_profesor.extendedProps;
                mensaje += ` ${c.codigo_asignatura} · ${datos.conflicto_profesor.title}. Centro: ${c.centros.join(", ")}. Facultad: ${c.facultades.join(", ")}. Programa: ${c.programas.join(", ")}. Modalidad: ${c.modalidad}. Sede: ${c.sede}. Periodo: ${c.periodo}. Semestre: ${c.semestres.join(", ")}. Grupos: ${c.grupos.map(g => g.codigo).join(", ")}. Aula: ${c.aula}.`;
            }
            throw new Error(mensaje);
        }
        return datos;
    }
    function cerrarMenu() { if (menu) menu.hidden = true; }
    function bloquear(valor) {
        guardando = valor; cerrarMenu();
        if (valor) ocultarTooltips();
        calendar.setOption("editable", editable && !valor);
        calendar.setOption("eventStartEditable", editable && !valor);
        calendar.setOption("eventDurationEditable", editable && !valor);
        calendar.setOption("droppable", puedeCrear && !valor);
    }
    async function refrescar() {
        calendar.refetchEvents();
        const abiertos = Array.from(document.querySelectorAll(".academic-subject-card[open] .subject-code")).map(n => n.textContent);
        try {
            const response = await fetch(window.location.href, { credentials: "same-origin" });
            if (!response.ok) throw new Error();
            const panel = new DOMParser().parseFromString(await response.text(), "text/html").querySelector(".academic-subject-list");
            if (!panel) throw new Error();
            document.querySelector(".academic-subject-list").replaceWith(panel);
            panel.querySelectorAll(".academic-subject-card").forEach(card => { card.open = abiertos.includes(card.querySelector(".subject-code").textContent); });
            prepararTooltipsDocentes();
        } catch (_) { mostrarMensaje("Cambio guardado. Recargue la página para actualizar el panel académico.", "warning"); }
    }
    function confirmarBloque(info, tipo) {
        limpiarReferencias();
        if (!editable || guardando || (info.event.extendedProps.provisional || info.event.extendedProps.ocupacion_externa) || !moverModal) { info.revert(); return; }
        if (tipo === "resize" && info.event.end - info.event.start < 3600000) {
            info.revert(); mostrarMensaje("La duración mínima de un horario es 1 hora."); return;
        }
        bloquear(true); cambio = { info, tipo };
        const props = info.oldEvent.extendedProps;
        texto("mover-asignatura", `${props.codigo_asignatura || ""} · ${info.event.title}`);
        texto("mover-profesor", props.profesor); texto("mover-aula", props.aula || "Aula pendiente");
        texto("mover-original", `${nombresDias[dias.indexOf(props.dia)]} · ${props.hora_inicio.slice(0, 5)}–${props.hora_fin.slice(0, 5)}`);
        texto("mover-nuevo", `${nombresDias[info.event.start.getDay()]} · ${hora(info.event.start).slice(0, 5)}–${hora(info.event.end).slice(0, 5)}`);
        moverModal.show();
    }
    function abrirMenu(evento, x, y) {
        if (guardando || (evento.extendedProps.provisional || evento.extendedProps.ocupacion_externa) || !menu) return;
        eventoMenu = evento;
        menuAula.textContent = evento.extendedProps.aula_id ? "Cambiar aula" : "Asignar aula";
        menuAula.hidden = !editable;
        menu.hidden = false;
        menu.style.left = `${Math.max(8, Math.min(x, window.innerWidth - menu.offsetWidth - 8))}px`;
        menu.style.top = `${Math.max(8, Math.min(y, window.innerHeight - menu.offsetHeight - 8))}px`;
        const primero = editable ? menuAula : document.getElementById("context-ver-detalle");
        primero.focus();
    }
    function verDetalle(evento) {
        cerrarMenu(); ocultarTooltips();
        if (!detalleModal) return;
        const props = evento.extendedProps;
        texto("detalle-asignatura", `${props.codigo_asignatura} · ${evento.title}`);
        texto("detalle-profesor", props.profesor); texto("detalle-modalidad", props.modalidad);
        texto("detalle-centro", (props.centros || []).join(", ") || "No determinado");
        texto("detalle-facultad", (props.facultades || []).join(", ") || "No determinada");
        texto("detalle-programa", (props.programas || [...new Set(props.grupos.map(g => g.programa))]).join(", ") || "No determinado");
        texto("detalle-periodo", props.periodo || "No determinado");
        texto("detalle-semestre", (props.semestres || []).join(", ") || "No determinado");
        texto("detalle-grupos", props.grupos.map(g => `${g.codigo} (${g.programa})`).join(", "));
        texto("detalle-bloque", `${nombresDias[dias.indexOf(props.dia)]} · ${props.hora_inicio.slice(0, 5)}–${props.hora_fin.slice(0, 5)}`);
        texto("detalle-sede", props.sede); texto("detalle-aula", props.aula || "Aula pendiente"); detalleModal.show();
    }
    const calendar = new FullCalendar.Calendar(element, {
        initialView: "timeGridWeek", initialDate: element.dataset.referenceWeek,
        locale: "es", firstDay: 1, timeZone: "local", headerToolbar: false,
        dayHeaderFormat: { weekday: "long" }, allDaySlot: false,
        slotMinTime: "06:00:00", slotMaxTime: "22:00:00", scrollTime: "06:00:00",
        slotDuration: "00:30:00", snapDuration: "00:30:00", defaultTimedEventDuration: "01:00:00", forceEventDuration: false,
        slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false }, height: 760,
        editable: editable, eventStartEditable: editable, eventDurationEditable: editable,
        droppable: puedeCrear, dropAccept: ".offer-drag-card", selectable: false, eventResizableFromStart: false,
        events: async function (_info, success, failure) {
            try { success(await json(urlContexto(element.dataset.eventsUrl))); }
            catch (error) { mostrarMensaje(error.message); failure(error); }
        },
        eventReceive: async function (info) {
            if (!puedeCrear || guardando) { info.revert(); return; }
            limpiarReferencias();
            bloquear(true); info.event.setProp("startEditable", false); info.event.setProp("durationEditable", false);
            const inicio = new Date(info.event.start), fin = new Date(inicio);
            fin.setHours(fin.getHours() + 1);
            mostrarMensaje("Creando horario…", "info");
            try {
                const datos = await json(urlContexto(element.dataset.createUrl), post({
                    oferta_id: info.event.extendedProps.oferta_id, dia: dias[inicio.getDay()], hora_inicio: hora(inicio), hora_fin: hora(fin)
                }));
                if (!datos.ok) throw new Error("No se pudo crear el horario.");
                info.event.remove(); mostrarMensaje("Horario creado · Aula pendiente.", "success"); await refrescar();
            } catch (error) { info.event.remove(); mostrarMensaje(error.message); calendar.refetchEvents(); }
            finally { bloquear(false); }
        },
        eventContent: function (info) {
            const p = info.event.extendedProps, content = document.createElement("div");
            content.className = "uniplan-event-content";
            if (p.disponibilidad_visual) return { domNodes: [] };
            if (p.ocupacion_externa) {
                for (const valor of ["OCUPADO EN OTRO CONTEXTO", info.event.title, p.sede, `${p.hora_inicio.slice(0, 5)}–${p.hora_fin.slice(0, 5)}`]) {
                    const line = document.createElement("div"); line.textContent = valor; content.appendChild(line);
                }
                return { domNodes: [content] };
            }
            const horario = p.provisional ? "1 hora · Sin guardar" : `${p.hora_inicio.slice(0, 5)}–${p.hora_fin.slice(0, 5)}`;
            for (const [clase, valor] of [["uniplan-event-title", info.event.title], ["uniplan-event-time", horario],
                ["uniplan-event-detail", p.profesor], ["uniplan-event-detail", p.aula || "Aula pendiente"]]) {
                const line = document.createElement("div"); line.className = clase; line.textContent = valor; content.appendChild(line);
            }
            if (puedeEliminar && !p.provisional && !p.ocupacion_externa) {
                const boton = document.createElement("button");
                boton.type = "button"; boton.className = "uniplan-event-delete"; boton.textContent = "×";
                boton.setAttribute("title", "Eliminar horario"); boton.setAttribute("aria-label", "Eliminar horario");
                ["pointerdown", "mousedown", "touchstart", "dblclick", "contextmenu"].forEach(nombre => {
                    boton.addEventListener(nombre, ev => { ev.stopPropagation(); if (nombre === "contextmenu") ev.preventDefault(); });
                });
                boton.addEventListener("keydown", ev => { ev.stopPropagation(); });
                boton.addEventListener("click", ev => { ev.preventDefault(); ev.stopPropagation(); abrirEliminar(info.event); });
                content.appendChild(boton);
            }
            return { domNodes: [content] };
        },
        eventDidMount: function (info) {
            const p = info.event.extendedProps;
            if (p.disponibilidad_visual) {
                info.el.setAttribute("title", `Fuera de disponibilidad de ${p.profesor}.`);
                return;
            }
            if (!p.provisional) {
                const contenido = [p.ocupacion_externa ? "OCUPADO EN OTRO CONTEXTO" : "", info.event.title, p.profesor,
                    `${nombresDias[dias.indexOf(p.dia)]} · ${p.hora_inicio.slice(0,5)}–${p.hora_fin.slice(0,5)}`,
                    `${(p.programas || p.grupos.map(g => g.programa)).join(", ")} · Semestre ${(p.semestres || []).join(", ")}`,
                    p.grupos.map(g => g.codigo).join(", "), p.modalidad, `${p.sede} · ${p.aula || "Aula pendiente"}`].filter(Boolean).join("\n");
                tooltipsEventos.set(info.el, tooltip(info.el, contenido));
            }
            info.el.setAttribute("tabindex", "0");
            info.el.setAttribute("aria-label", `${info.event.title}. Clic derecho o Mayús F10 para opciones.`);
            info.el.addEventListener("contextmenu", function (ev) { ev.preventDefault(); abrirMenu(info.event, ev.clientX, ev.clientY); });
            info.el.addEventListener("keydown", function (ev) {
                if (ev.key === "ContextMenu" || (ev.shiftKey && ev.key === "F10")) {
                    ev.preventDefault(); const rect = info.el.getBoundingClientRect(); abrirMenu(info.event, rect.left, rect.bottom);
                }
            });
        },
        eventWillUnmount: function (info) { const t = tooltipsEventos.get(info.el); if (t) t.dispose(); tooltipsEventos.delete(info.el); },
        eventDragStart: iniciarReferenciasEvento,
        eventDragStop: limpiarReferencias,
        eventResizeStart: iniciarReferenciasEvento,
        eventResizeStop: limpiarReferencias,
        eventClick: function (info) { if (!guardando && !info.event.extendedProps.provisional && !info.event.extendedProps.disponibilidad_visual) verDetalle(info.event); },
        eventDrop: function (info) { confirmarBloque(info, "move"); },
        eventResize: function (info) { confirmarBloque(info, "resize"); }
    });
    calendar.render();
    let versionOcupaciones = 0, gesto = null;
    const referencias = [];
    function limpiarReferencias() {
        ++versionOcupaciones;
        referencias.splice(0).forEach(evento => evento.remove());
    }
    function sombrearDisponibilidad(bloques, profesor) {
        // Complemento visual dentro de 06:00–22:00; no impide ningún drop.
        const segundos = valor => { const p = valor.split(":").map(Number); return p[0] * 3600 + p[1] * 60 + (p[2] || 0); };
        const minimo = 6 * 3600, maximo = 22 * 3600;
        ["LU", "MA", "MI", "JU", "VI", "SA", "DO"].forEach((dia, offset) => {
            const disponibles = bloques.filter(b => b.dia === dia).map(b => [Math.max(minimo, segundos(b.hora_inicio)), Math.min(maximo, segundos(b.hora_fin))]).filter(b => b[0] < b[1]).sort((a,b) => a[0] - b[0]);
            const fecha = new Date(`${element.dataset.referenceWeek}T00:00:00`); fecha.setDate(fecha.getDate() + offset);
            function gris(inicio, fin) {
                if (inicio >= fin) return;
                const start = new Date(fecha), end = new Date(fecha);
                start.setMilliseconds(inicio * 1000); end.setMilliseconds(fin * 1000);
                referencias.push(calendar.addEvent({ id: `no-disponible-${versionOcupaciones}-${dia}-${inicio}`, start, end,
                    display: "background", allDay: false, editable: false, startEditable: false, durationEditable: false,
                    classNames: ["zona-no-disponible"], extendedProps: { disponibilidad_visual: true, profesor } }));
            }
            let hasta = minimo;
            disponibles.forEach(([inicio, fin]) => { gris(hasta, inicio); hasta = Math.max(hasta, fin); });
            gris(hasta, maximo);
        });
    }
    function iniciarReferenciasEvento(info) {
        const p = info.event.extendedProps;
        if (!editable || guardando || p.provisional || p.ocupacion_externa || p.disponibilidad_visual) return;
        ocultarTooltips();
        if (p.oferta_id) return cargarReferencias(p.oferta_id);
    }
    function pintarReferencias(datos) {
        const normales = new Set(calendar.getEvents().filter(e => !e.extendedProps.ocupacion_externa && !e.extendedProps.disponibilidad_visual).map(e => String(e.extendedProps.horario_id || e.id)));
        datos.ocupaciones.filter(e => !normales.has(String(e.extendedProps.horario_id))).forEach(e => referencias.push(calendar.addEvent(e)));
        sombrearDisponibilidad(datos.disponibilidad, datos.profesor);
    }
    async function cargarReferencias(ofertaId) {
        limpiarReferencias(); const version = versionOcupaciones;
        try {
            const datos = await json(urlContexto(element.dataset.occupationsBase.replace("/0/", `/${ofertaId}/`)));
            if (version !== versionOcupaciones) return;
            pintarReferencias(datos);
        } catch (error) { if (version === versionOcupaciones) mostrarMensaje(error.message); }
    }
    if (puedeCrear) {
        document.querySelector(".academic-panel").addEventListener("pointerdown", function (ev) {
            const card = ev.target.closest(".offer-drag-card");
            if (!card || guardando || (ev.button !== undefined && ev.button !== 0)) return;
            limpiarReferencias(); gesto = { card, id: ev.pointerId, x: ev.clientX, y: ev.clientY, oferta: card.dataset.ofertaId, iniciado: false };
        });
        document.addEventListener("pointermove", function (ev) {
            if (!gesto || ev.pointerId !== gesto.id || gesto.iniciado) return;
            if (Math.hypot(ev.clientX - gesto.x, ev.clientY - gesto.y) >= 5) { gesto.iniciado = true; ultimoDrag = { card: gesto.card, fecha: Date.now() }; ocultarTooltips(); cargarReferencias(gesto.oferta); }
        });
        for (const nombre of ["pointerup", "pointercancel"]) document.addEventListener(nombre, function () { if (gesto && gesto.iniciado) ultimoDrag = { card: gesto.card, fecha: Date.now() }; gesto = null; limpiarReferencias(); });
        document.getElementById("filtros-planificacion").addEventListener("change", limpiarReferencias);
    }
    window.addEventListener("blur", function () { gesto = null; limpiarReferencias(); });
    document.addEventListener("click", function (ev) { if (menu && !menu.contains(ev.target)) cerrarMenu(); });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { gesto = null; limpiarReferencias(); cerrarMenu(); } });
    if (menu) {
        const eliminarOpcion = document.getElementById("context-eliminar-horario");
        if (puedeEliminar && eliminarOpcion) eliminarOpcion.addEventListener("click", function () { if (eventoMenu) abrirEliminar(eventoMenu); });
        document.getElementById("context-ver-detalle").addEventListener("click", function () { if (eventoMenu) verDetalle(eventoMenu); });
        menuAula.addEventListener("click", async function () {
            if (!editable || guardando || !eventoMenu || !aulaModal) return;
            const evento = eventoMenu; bloquear(true); aulaPendiente = evento.id;
            const solicitud = ++solicitudAula;
            aulaForm.reset(); aulaSelect.replaceChildren(new Option("Seleccione un aula…", ""));
            aulaSelect.disabled = aulaGuardar.disabled = true;
            texto("aula-horario-resumen", `${evento.title} · ${evento.extendedProps.profesor}`);
            texto("aula-cargando", "Consultando aulas de la sede seleccionada…"); aulaModal.show();
            try {
                const datos = await json(urlContexto(element.dataset.aulasBase.replace("/0/", `/${evento.id}/`)));
                if (solicitud !== solicitudAula || !aulaPendiente) return;
                datos.aulas.forEach(a => aulaSelect.appendChild(new Option(`${a.nombre} · ${a.sede}`, a.id)));
                if (datos.event.extendedProps.aula_id) aulaSelect.value = String(datos.event.extendedProps.aula_id);
                aulaSelect.disabled = aulaGuardar.disabled = !datos.aulas.length;
                texto("aula-cargando", datos.aulas.length ? "" : "No hay aulas activas en esta sede.");
                aulaSelect.focus();
            } catch (error) { aulaPendiente = null; aulaModal.hide(); bloquear(false); mostrarMensaje(error.message); }
        });
    }
    if (editable && moverModal) {
        moverElement.addEventListener("hidden.bs.modal", function () {
            if (cambio && !enviandoCambio) { limpiarReferencias(); cambio.info.revert(); cambio = null; bloquear(false); }
        });
        confirmarCambio.addEventListener("click", async function () {
            if (!cambio || enviandoCambio) return;
            enviandoCambio = true; confirmarCambio.disabled = true;
            moverElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = true; });
            const { info, tipo } = cambio;
            try {
                const datos = await json(tipo === "resize" ? element.dataset.resizeUrl : element.dataset.moveUrl, post({
                    horario_id: info.event.extendedProps.horario_id, dia: dias[info.event.start.getDay()],
                    hora_inicio: hora(info.event.start), hora_fin: hora(info.event.end),
                    original: { dia: info.oldEvent.extendedProps.dia, hora_inicio: info.oldEvent.extendedProps.hora_inicio, hora_fin: info.oldEvent.extendedProps.hora_fin }
                }));
                if (!datos.ok) throw new Error("No se pudo guardar el horario.");
                cambio = null; moverModal.hide(); mostrarMensaje("Horario actualizado correctamente.", "success"); await refrescar();
            } catch (error) { info.revert(); cambio = null; moverModal.hide(); mostrarMensaje(error.message); calendar.refetchEvents(); }
            finally {
                limpiarReferencias();
                enviandoCambio = false; confirmarCambio.disabled = false;
                moverElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = false; }); bloquear(false);
            }
        });
    }
    if (editable && aulaModal) {
        aulaElement.addEventListener("hidden.bs.modal", function () { ++solicitudAula; aulaPendiente = null; if (!enviandoAula) bloquear(false); });
        aulaForm.addEventListener("submit", async function (ev) {
            ev.preventDefault(); if (!aulaPendiente || enviandoAula || !aulaForm.reportValidity()) return;
            enviandoAula = true; aulaGuardar.disabled = true;
            aulaElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = true; });
            try {
                const datos = await json(urlContexto(element.dataset.assignUrl), post({ horario_id: Number(aulaPendiente), aula_id: Number(aulaSelect.value) }));
                if (!datos.ok) throw new Error("No se pudo asignar el aula.");
                aulaPendiente = null; aulaModal.hide(); mostrarMensaje("Aula actualizada correctamente.", "success"); await refrescar();
            } catch (error) { aulaPendiente = null; aulaModal.hide(); mostrarMensaje(error.message); calendar.refetchEvents(); }
            finally {
                enviandoAula = false; aulaGuardar.disabled = false;
                aulaElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = false; }); bloquear(false);
            }
        });
    }
    if (puedeCrear) new FullCalendar.Draggable(document.querySelector(".academic-panel"), {
        itemSelector: ".offer-drag-card", minDistance: 5,
        eventData: function (card) { return { title: card.dataset.asignatura, duration: "01:00:00", classNames: ["evento-provisional"],
            startEditable: false, durationEditable: false,
            extendedProps: { oferta_id: Number(card.dataset.ofertaId), profesor: card.dataset.profesor, provisional: true } }; }
    });
});
