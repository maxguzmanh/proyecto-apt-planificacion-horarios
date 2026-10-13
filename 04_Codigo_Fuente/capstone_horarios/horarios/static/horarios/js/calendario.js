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
        } catch (_) { mostrarMensaje("Cambio guardado. Recargue la página para actualizar el panel académico.", "warning"); }
    }
    function confirmarBloque(info, tipo) {
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
        cerrarMenu();
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
            limpiarOcupaciones();
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
            info.el.setAttribute("tabindex", "0");
            info.el.setAttribute("aria-label", `${info.event.title}. Clic derecho o Mayús F10 para opciones.`);
            info.el.addEventListener("contextmenu", function (ev) { ev.preventDefault(); abrirMenu(info.event, ev.clientX, ev.clientY); });
            info.el.addEventListener("keydown", function (ev) {
                if (ev.key === "ContextMenu" || (ev.shiftKey && ev.key === "F10")) {
                    ev.preventDefault(); const rect = info.el.getBoundingClientRect(); abrirMenu(info.event, rect.left, rect.bottom);
                }
            });
        },
        eventClick: function (info) { if (!guardando && !info.event.extendedProps.provisional) verDetalle(info.event); },
        eventDrop: function (info) { confirmarBloque(info, "move"); },
        eventResize: function (info) { confirmarBloque(info, "resize"); }
    });
    calendar.render();
    let versionOcupaciones = 0, gesto = null;
    const referencias = [];
    function limpiarOcupaciones() {
        ++versionOcupaciones;
        referencias.splice(0).forEach(evento => evento.remove());
    }
    async function cargarOcupaciones(ofertaId) {
        limpiarOcupaciones(); const version = versionOcupaciones;
        try {
            const datos = await json(urlContexto(element.dataset.occupationsBase.replace("/0/", `/${ofertaId}/`)));
            if (version !== versionOcupaciones) return;
            const normales = new Set(calendar.getEvents().filter(e => !e.extendedProps.ocupacion_externa).map(e => String(e.extendedProps.horario_id || e.id)));
            datos.filter(e => !normales.has(String(e.extendedProps.horario_id))).forEach(e => referencias.push(calendar.addEvent(e)));
        } catch (error) { if (version === versionOcupaciones) mostrarMensaje(error.message); }
    }
    if (puedeCrear) {
        document.querySelector(".academic-panel").addEventListener("pointerdown", function (ev) {
            const card = ev.target.closest(".offer-drag-card");
            if (!card || guardando || (ev.button !== undefined && ev.button !== 0)) return;
            limpiarOcupaciones(); gesto = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, oferta: card.dataset.ofertaId, iniciado: false };
        });
        document.addEventListener("pointermove", function (ev) {
            if (!gesto || ev.pointerId !== gesto.id || gesto.iniciado) return;
            if (Math.hypot(ev.clientX - gesto.x, ev.clientY - gesto.y) >= 5) { gesto.iniciado = true; cargarOcupaciones(gesto.oferta); }
        });
        for (const nombre of ["pointerup", "pointercancel"]) document.addEventListener(nombre, function () { gesto = null; limpiarOcupaciones(); });
        window.addEventListener("blur", function () { gesto = null; limpiarOcupaciones(); });
        document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { gesto = null; limpiarOcupaciones(); } });
        document.getElementById("filtros-planificacion").addEventListener("change", limpiarOcupaciones);
    }
    document.addEventListener("click", function (ev) { if (menu && !menu.contains(ev.target)) cerrarMenu(); });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") cerrarMenu(); });
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
            if (cambio && !enviandoCambio) { cambio.info.revert(); cambio = null; bloquear(false); }
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
