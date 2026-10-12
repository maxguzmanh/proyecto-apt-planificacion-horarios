document.addEventListener("DOMContentLoaded", function () {
    const element = document.getElementById("uniplan-calendar");
    if (!element) return;
    const message = document.getElementById("calendar-message");
    function mostrarMensaje(texto, tipo = "danger") {
        message.className = `alert alert-${tipo}`;
        message.textContent = texto;
        message.hidden = false;
    }
    if (!window.FullCalendar) {
        mostrarMensaje("No fue posible cargar el calendario. Compruebe su conexión y recargue la página.");
        return;
    }
    const editable = element.dataset.canEdit === "true";
    const puedeCrear = element.dataset.canCreate === "true";
    const dias = ["DO", "LU", "MA", "MI", "JU", "VI", "SA"];
    const nombresDias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    let guardando = false;
    let pendiente = null;
    let numeroSolicitud = 0;
    let enviandoCreacion = false;
    let movimientoPendiente = null;
    let enviandoMovimiento = false;
    const moverModalElement = document.getElementById("mover-horario-modal");
    const moverModal = moverModalElement && window.bootstrap ? new bootstrap.Modal(moverModalElement, { backdrop: "static", keyboard: false }) : null;
    const confirmarMovimiento = document.getElementById("mover-confirmar");
    const modalElement = document.getElementById("crear-horario-modal");
    const modal = modalElement && window.bootstrap ? new bootstrap.Modal(modalElement, { backdrop: "static", keyboard: false }) : null;
    const formulario = document.getElementById("crear-horario-form");
    const aula = document.getElementById("confirmar-aula");
    const horaFin = document.getElementById("confirmar-hora-fin");
    const guardar = document.getElementById("confirmar-guardar");
    const modalError = document.getElementById("crear-horario-error");
    const cargando = document.getElementById("crear-horario-cargando");
    function horaLocal(fecha) {
        return [fecha.getHours(), fecha.getMinutes(), fecha.getSeconds()].map(n => String(n).padStart(2, "0")).join(":") +
            (fecha.getMilliseconds() ? `.${String(fecha.getMilliseconds()).padStart(3, "0")}` : "");
    }
    function urlContexto(base) { return `${base}?${element.dataset.filters}`; }
    async function consultarJSON(url, opciones = {}) {
        const response = await fetch(url, { credentials: "same-origin", ...opciones });
        let datos;
        try { datos = await response.json(); }
        catch (_) { throw new Error("No se pudo confirmar la operación. Actualice el calendario para comprobar su estado."); }
        if (!response.ok) throw new Error(Object.values(datos.errors || {}).flat().join(" ") || "No fue posible completar la operación.");
        return datos;
    }
    function opcionesPOST(datos) {
        return { method: "POST", headers: { "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("#calendar-csrf [name=csrfmiddlewaretoken]").value },
            body: JSON.stringify(datos) };
    }
    async function refrescarPanel() {
        const abiertos = Array.from(document.querySelectorAll(".academic-subject-card[open] .subject-code")).map(n => n.textContent);
        try {
            const response = await fetch(window.location.href, { credentials: "same-origin" });
            if (!response.ok) throw new Error();
            const html = new DOMParser().parseFromString(await response.text(), "text/html");
            const panel = html.querySelector(".academic-subject-list");
            if (!panel) throw new Error();
            document.querySelector(".academic-subject-list").replaceWith(panel);
            panel.querySelectorAll(".academic-subject-card").forEach(card => {
                card.open = abiertos.includes(card.querySelector(".subject-code").textContent);
            });
        } catch (_) { mostrarMensaje("Horario guardado. Recargue la página para actualizar el panel académico.", "warning"); }
    }
    function bloquearCalendario(bloqueado) {
        guardando = bloqueado;
        calendar.setOption("editable", editable && !bloqueado);
        calendar.setOption("eventStartEditable", editable && !bloqueado);
        calendar.setOption("eventDurationEditable", false);
        calendar.setOption("droppable", puedeCrear && !bloqueado);
    }
    function ponerTexto(id, texto) { document.getElementById(id).textContent = texto; }
    function horas(valor) {
        return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 }).format(Number(valor))} h`;
    }
    async function recibirOferta(info) {
        if (!puedeCrear || guardando || !modal) { info.revert(); return; }
        bloquearCalendario(true);
        const solicitud = ++numeroSolicitud;
        pendiente = { evento: info.event, inicio: new Date(info.event.start), ofertaId: info.event.extendedProps.oferta_id };
        info.event.setProp("startEditable", false);
        info.event.setProp("durationEditable", false);
        formulario.reset();
        const finPropuesto = new Date(pendiente.inicio);
        finPropuesto.setHours(finPropuesto.getHours() + 1);
        pendiente.horaFinPropuesta = horaLocal(finPropuesto).slice(0, 5);
        horaFin.value = pendiente.horaFinPropuesta;
        document.getElementById("ajustar-hora-fin").open = false;
        aula.replaceChildren(new Option("Seleccione un aula…", ""));
        aula.disabled = horaFin.disabled = guardar.disabled = true;
        modalError.hidden = true;
        cargando.hidden = false;
        cargando.textContent = "Consultando la oferta…";
        for (const id of ["confirmar-asignatura", "confirmar-profesor", "confirmar-grupos", "confirmar-modalidad", "confirmar-carga", "confirmar-planificadas", "confirmar-pendientes"]) ponerTexto(id, "—");
        document.getElementById("confirmar-disponibilidad").replaceChildren();
        ponerTexto("confirmar-inicio", `${nombresDias[pendiente.inicio.getDay()]} · ${horaLocal(pendiente.inicio).slice(0, 5)}–${horaFin.value}`);
        modal.show();
        try {
            const url = element.dataset.offerBase.replace("/0/", `/${pendiente.ofertaId}/`);
            const datos = await consultarJSON(urlContexto(url));
            if (solicitud !== numeroSolicitud || !pendiente) return;
            ponerTexto("confirmar-asignatura", `${datos.codigo_asignatura} · ${datos.asignatura}`);
            ponerTexto("confirmar-profesor", datos.profesor);
            ponerTexto("confirmar-grupos", datos.grupos.map(g => `${g.codigo} (${g.programa})`).join(", "));
            ponerTexto("confirmar-modalidad", datos.modalidad);
            ponerTexto("confirmar-carga", datos.horas_asignadas === null ? "Carga docente no registrada" : horas(datos.horas_asignadas));
            ponerTexto("confirmar-planificadas", horas(datos.horas_planificadas));
            ponerTexto("confirmar-pendientes", datos.horas_pendientes === null ? "Sin calcular" : horas(datos.horas_pendientes));
            const bloques = document.getElementById("confirmar-disponibilidad");
            if (!datos.disponibilidad.length) {
                const li = document.createElement("li");
                li.textContent = "Disponibilidad no registrada";
                bloques.appendChild(li);
            }
            datos.disponibilidad.forEach(b => {
                const li = document.createElement("li");
                li.textContent = `${b.nombre_dia} ${b.hora_inicio.slice(0, 5)}–${b.hora_fin.slice(0, 5)}`;
                bloques.appendChild(li);
            });
            datos.aulas.forEach(a => aula.appendChild(new Option(`${a.nombre} · ${a.sede}`, a.id)));
            cargando.hidden = true;
            if (!datos.aulas.length) {
                modalError.textContent = "No hay aulas activas en el contexto seleccionado.";
                modalError.hidden = false;
                return;
            }
            aula.disabled = horaFin.disabled = guardar.disabled = false;
            aula.focus();
        } catch (error) {
            if (solicitud !== numeroSolicitud) return;
            if (pendiente) pendiente.evento.remove();
            pendiente = null;
            modal.hide();
            calendar.refetchEvents();
            mostrarMensaje(error.message);
        }
    }
    const calendar = new FullCalendar.Calendar(element, {
        initialView: "timeGridWeek", initialDate: element.dataset.referenceWeek,
        locale: "es", firstDay: 1, timeZone: "local", headerToolbar: false,
        dayHeaderFormat: { weekday: "long" }, allDaySlot: false,
        slotMinTime: "06:00:00", slotMaxTime: "22:00:00", scrollTime: "06:00:00",
        slotDuration: "00:30:00", snapDuration: "00:15:00",
        // La duración propuesta se confirma con el aula antes de guardar.
        defaultTimedEventDuration: "01:00:00", forceEventDuration: false,
        slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
        height: 760, nowIndicator: false, editable: editable,
        eventStartEditable: editable, eventDurationEditable: false,
        droppable: puedeCrear, dropAccept: ".offer-drag-card", selectable: false, eventResizableFromStart: false,
        eventReceive: recibirOferta,
        events: async function (_info, success, failure) {
            try { success(await consultarJSON(urlContexto(element.dataset.eventsUrl))); }
            catch (error) { mostrarMensaje(error.message); failure(error); }
        },
        eventContent: function (info) {
            const props = info.event.extendedProps;
            const content = document.createElement("div");
            content.className = "uniplan-event-content";
            const horarioTexto = props.provisional ? "1 hora propuesta · Sin guardar" : `${props.hora_inicio.slice(0, 5)}–${props.hora_fin.slice(0, 5)}`;
            for (const [clase, texto] of [
                ["uniplan-event-title", info.event.title], ["uniplan-event-time", horarioTexto],
                ["uniplan-event-detail", props.profesor], ["uniplan-event-detail", props.provisional ? "Sin guardar" : props.aula]
            ]) {
                const line = document.createElement("div");
                line.className = clase;
                line.textContent = texto;
                content.appendChild(line);
            }
            return { domNodes: [content] };
        },
        eventClick: function (info) {
            if (!editable || guardando || info.event.extendedProps.provisional) return;
            const url = element.dataset.editBase.replace("/0/", `/${info.event.id}/`);
            window.location.assign(`${url}?volver_a=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        },
        eventDrop: function (info) {
            if (!editable || guardando || info.event.extendedProps.provisional || !moverModal) { info.revert(); return; }
            bloquearCalendario(true);
            movimientoPendiente = info;
            const props = info.oldEvent.extendedProps;
            ponerTexto("mover-asignatura", `${props.codigo_asignatura || ""} · ${info.event.title}`);
            ponerTexto("mover-profesor", props.profesor);
            ponerTexto("mover-aula", props.aula);
            const diaOriginal = nombresDias[dias.indexOf(props.dia)];
            ponerTexto("mover-original", `${diaOriginal} · ${props.hora_inicio.slice(0, 5)}–${props.hora_fin.slice(0, 5)}`);
            ponerTexto("mover-nuevo", `${nombresDias[info.event.start.getDay()]} · ${horaLocal(info.event.start).slice(0, 5)}–${horaLocal(info.event.end).slice(0, 5)}`);
            moverModal.show();
        }
    });
    calendar.render();
    if (editable && moverModal) {
        moverModalElement.addEventListener("hidden.bs.modal", function () {
            if (movimientoPendiente && !enviandoMovimiento) {
                movimientoPendiente.revert();
                movimientoPendiente = null;
                bloquearCalendario(false);
            }
        });
        confirmarMovimiento.addEventListener("click", async function () {
            if (!movimientoPendiente || enviandoMovimiento) return;
            enviandoMovimiento = true;
            confirmarMovimiento.disabled = true;
            moverModalElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = true; });
            const info = movimientoPendiente;
            mostrarMensaje("Guardando horario…", "info");
            try {
                const datos = await consultarJSON(element.dataset.moveUrl, opcionesPOST({
                    horario_id: info.event.extendedProps.horario_id,
                    dia: dias[info.event.start.getDay()],
                    hora_inicio: horaLocal(info.event.start), hora_fin: horaLocal(info.event.end),
                    original: { dia: info.oldEvent.extendedProps.dia,
                        hora_inicio: info.oldEvent.extendedProps.hora_inicio, hora_fin: info.oldEvent.extendedProps.hora_fin }
                }));
                if (!datos.ok) throw new Error("No se pudo guardar el horario.");
                movimientoPendiente = null;
                moverModal.hide();
                mostrarMensaje("Horario actualizado correctamente.", "success");
                calendar.refetchEvents();
                await refrescarPanel();
            } catch (error) {
                info.revert();
                movimientoPendiente = null;
                moverModal.hide();
                mostrarMensaje(error.message);
                calendar.refetchEvents();
            } finally {
                enviandoMovimiento = false;
                confirmarMovimiento.disabled = false;
                moverModalElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = false; });
                bloquearCalendario(false);
            }
        });
    }
    if (puedeCrear && modal) {
        new FullCalendar.Draggable(document.querySelector(".academic-panel"), {
            itemSelector: ".offer-drag-card", minDistance: 5,
            eventData: function (handle) {
                return { title: handle.dataset.asignatura, duration: "01:00:00", classNames: ["evento-provisional"],
                    startEditable: false, durationEditable: false,
                    extendedProps: { oferta_id: Number(handle.dataset.ofertaId), profesor: handle.dataset.profesor,
                        grupos: handle.dataset.grupos, modalidad: handle.dataset.modalidad, provisional: true } };
            }
        });
        modalElement.addEventListener("hidden.bs.modal", function () {
            ++numeroSolicitud;
            if (pendiente) pendiente.evento.remove();
            pendiente = null;
            if (!enviandoCreacion) bloquearCalendario(false);
        });
        horaFin.addEventListener("input", function () {
            if (pendiente) ponerTexto("confirmar-inicio", `${nombresDias[pendiente.inicio.getDay()]} · ${horaLocal(pendiente.inicio).slice(0, 5)}–${horaFin.value || pendiente.horaFinPropuesta}`);
        });
        formulario.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (!pendiente || enviandoCreacion || !formulario.reportValidity()) return;
            enviandoCreacion = true;
            guardar.disabled = true;
            modalElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = true; });
            const actual = pendiente;
            try {
                const datos = await consultarJSON(urlContexto(element.dataset.createUrl), opcionesPOST({
                    oferta_id: actual.ofertaId, aula_id: Number(aula.value),
                    dia: dias[actual.inicio.getDay()], hora_inicio: horaLocal(actual.inicio), hora_fin: horaFin.value || actual.horaFinPropuesta
                }));
                if (!datos.ok) throw new Error("No se pudo crear el horario.");
                actual.evento.remove();
                pendiente = null;
                modal.hide();
                mostrarMensaje(datos.message, "success");
                calendar.refetchEvents();
                await refrescarPanel();
            } catch (error) {
                actual.evento.remove();
                pendiente = null;
                modal.hide();
                mostrarMensaje(error.message);
                calendar.refetchEvents();
            } finally {
                enviandoCreacion = false;
                modalElement.querySelectorAll("[data-bs-dismiss]").forEach(b => { b.disabled = false; });
                bloquearCalendario(false);
            }
        });
    }
});
