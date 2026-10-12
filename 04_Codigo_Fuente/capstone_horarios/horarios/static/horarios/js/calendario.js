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
    const dias = ["DO", "LU", "MA", "MI", "JU", "VI", "SA"];
    let guardando = false;
    function horaLocal(fecha) {
        return [fecha.getHours(), fecha.getMinutes(), fecha.getSeconds()].map(n => String(n).padStart(2, "0")).join(":") +
            (fecha.getMilliseconds() ? `.${String(fecha.getMilliseconds()).padStart(3, "0")}` : "");
    }
    const calendar = new FullCalendar.Calendar(element, {
        initialView: "timeGridWeek", initialDate: element.dataset.referenceWeek,
        locale: "es", firstDay: 1, timeZone: "local", headerToolbar: false,
        dayHeaderFormat: { weekday: "long" }, allDaySlot: false,
        slotMinTime: "06:00:00", slotMaxTime: "22:00:00", scrollTime: "06:00:00",
        slotDuration: "00:30:00", snapDuration: "00:15:00",
        slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
        height: 760, nowIndicator: false, editable: editable,
        eventStartEditable: editable, eventDurationEditable: false,
        droppable: false, selectable: false, eventResizableFromStart: false,
        events: async function (_info, success, failure) {
            try {
                const response = await fetch(`${element.dataset.eventsUrl}?${element.dataset.filters}`, { credentials: "same-origin" });
                const datos = await response.json();
                if (!response.ok) throw new Error(Object.values(datos.errors || {}).flat().join(" ") || "No fue posible cargar los horarios.");
                success(datos);
            } catch (error) {
                mostrarMensaje(error.message);
                failure(error);
            }
        },
        eventContent: function (info) {
            const props = info.event.extendedProps;
            const content = document.createElement("div");
            content.className = "uniplan-event-content";
            for (const [clase, texto] of [
                ["uniplan-event-title", info.event.title],
                ["uniplan-event-time", `${props.hora_inicio.slice(0, 5)}–${props.hora_fin.slice(0, 5)}`],
                ["uniplan-event-detail", props.profesor], ["uniplan-event-detail", props.aula]
            ]) {
                const line = document.createElement("div");
                line.className = clase;
                line.textContent = texto;
                content.appendChild(line);
            }
            return { domNodes: [content] };
        },
        eventClick: function (info) {
            if (!editable || guardando) return;
            const url = element.dataset.editBase.replace("/0/", `/${info.event.id}/`);
            window.location.assign(`${url}?volver_a=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        },
        eventDrop: async function (info) {
            if (guardando) { info.revert(); return; }
            guardando = true;
            calendar.setOption("editable", false);
            calendar.setOption("eventStartEditable", false);
            mostrarMensaje("Guardando horario…", "info");
            try {
                const response = await fetch(element.dataset.moveUrl, {
                    method: "POST", credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": document.querySelector("#calendar-csrf [name=csrfmiddlewaretoken]").value },
                    body: JSON.stringify({
                        horario_id: info.event.extendedProps.horario_id,
                        dia: dias[info.event.start.getDay()],
                        hora_inicio: horaLocal(info.event.start), hora_fin: horaLocal(info.event.end),
                        original: { dia: info.oldEvent.extendedProps.dia,
                            hora_inicio: info.oldEvent.extendedProps.hora_inicio,
                            hora_fin: info.oldEvent.extendedProps.hora_fin }
                    })
                });
                let datos;
                try { datos = await response.json(); }
                catch (_) { throw new Error("No se pudo confirmar el cambio. Actualice el calendario para comprobar su estado."); }
                if (!response.ok || !datos.ok) throw new Error(Object.values(datos.errors || {}).flat().join(" ") || "No se pudo guardar el horario.");
                // Refrescar también el panel académico y conservar los acordeones abiertos.
                const abiertos = Array.from(document.querySelectorAll(".academic-subject-card[open] .subject-code")).map(n => n.textContent);
                mostrarMensaje("Horario actualizado correctamente.", "success");
                calendar.refetchEvents();
                try {
                    const page = await fetch(window.location.href, { credentials: "same-origin" });
                    if (page.ok) {
                        const html = new DOMParser().parseFromString(await page.text(), "text/html");
                        const panel = html.querySelector(".academic-subject-list");
                        if (panel) {
                            document.querySelector(".academic-subject-list").replaceWith(panel);
                            panel.querySelectorAll(".academic-subject-card").forEach(card => {
                                card.open = abiertos.includes(card.querySelector(".subject-code").textContent);
                            });
                        }
                    }
                } catch (_) { mostrarMensaje("Horario guardado. Recargue la página para actualizar el panel académico.", "warning"); }
            } catch (error) {
                info.revert();
                mostrarMensaje(error.message);
                calendar.refetchEvents();
            } finally {
                guardando = false;
                calendar.setOption("editable", editable);
                calendar.setOption("eventStartEditable", editable);
                calendar.setOption("eventDurationEditable", false);
            }
        }
    });
    calendar.render();
});
