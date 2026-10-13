document.addEventListener("DOMContentLoaded", function () {
    const element = document.getElementById("profesor-calendar");
    if (!element) return;
    const periodo = document.getElementById("profesor-periodo"), mensaje = document.getElementById("profesor-calendar-message"), vacio = document.getElementById("profesor-empty");
    function error(texto) { mensaje.className = "alert alert-danger"; mensaje.textContent = texto; mensaje.hidden = false; }
    if (!window.FullCalendar) { error("No fue posible cargar el calendario. Recargue la página."); return; }
    const modalElement = document.getElementById("detalle-horario-modal");
    const modal = window.bootstrap ? new bootstrap.Modal(modalElement) : null;
    const dias = {LU:"Lunes",MA:"Martes",MI:"Miércoles",JU:"Jueves",VI:"Viernes",SA:"Sábado",DO:"Domingo"};
    const tips = new Map(); let version = 0, detalleVersion = 0;
    async function json(url) {
        const r = await fetch(url, {credentials:"same-origin"});
        if (r.redirected) throw new Error("Su sesión terminó. Inicie sesión nuevamente.");
        const d = await r.json(); if (!r.ok) throw new Error(Object.values(d.errors || {}).flat().join(" ") || "No fue posible consultar el horario."); return d;
    }
    function texto(id, valor) { document.getElementById(id).textContent = valor; }
    const calendar = new FullCalendar.Calendar(element, {
        initialView:"timeGridWeek", initialDate:element.dataset.referenceWeek, locale:"es", firstDay:1, timeZone:"local", headerToolbar:false,
        allDaySlot:false, dayHeaderFormat:{weekday:"long"}, slotMinTime:"06:00:00", slotMaxTime:"22:00:00", scrollTime:"06:00:00", slotDuration:"00:30:00", height:760,
        slotLabelFormat:{hour:"2-digit",minute:"2-digit",hour12:false}, editable:false, eventStartEditable:false, eventDurationEditable:false, droppable:false, selectable:false,
        events:async function (_info, success, failure) {
            const actual = ++version;
            if (!periodo.value) { vacio.hidden = false; success([]); return; }
            try {
                const datos = await json(`${element.dataset.eventsUrl}?periodo_id=${encodeURIComponent(periodo.value)}`);
                if (actual !== version) { success([]); return; }
                mensaje.hidden = true; vacio.hidden = datos.length > 0; success(datos);
            } catch (e) { if (actual === version) error(e.message); failure(e); }
        },
        eventContent:function (info) {
            const p = info.event.extendedProps, content = document.createElement("div"); content.className = "uniplan-event-content";
            for (const [clase, valor] of [["uniplan-event-title",info.event.title],["uniplan-event-time",`${p.hora_inicio.slice(0,5)}–${p.hora_fin.slice(0,5)}`],["uniplan-event-detail",p.aula || "Aula pendiente"]]) {
                const line = document.createElement("div"); line.className=clase; line.textContent=valor; content.appendChild(line);
            }
            return {domNodes:[content]};
        },
        eventDidMount:function (info) {
            const p=info.event.extendedProps;
            const resumen=[info.event.title,`${p.programas.join(", ")} · Semestre ${p.semestres.join(", ")}`,p.grupos.map(g=>g.codigo).join(", "),p.modalidad,`${p.sede} · ${p.aula || "Aula pendiente"}`,`${dias[p.dia]} ${p.hora_inicio.slice(0,5)}–${p.hora_fin.slice(0,5)}`].join("\n");
            info.el.setAttribute("tabindex","0"); info.el.setAttribute("aria-label",`${resumen}. Pulse Enter para ver detalle.`);
            if (window.bootstrap && bootstrap.Tooltip) tips.set(info.el,new bootstrap.Tooltip(info.el,{title:resumen,html:false,trigger:"hover focus",container:"body"}));
            else info.el.setAttribute("title",resumen);
            info.el.addEventListener("keydown",ev=>{if(ev.key==="Enter"){ev.preventDefault();abrirDetalle(info.event);}});
        },
        eventWillUnmount:function (info) { const t=tips.get(info.el); if(t)t.dispose();tips.delete(info.el); },
        eventClick:function (info) { abrirDetalle(info.event); }
    });
    async function abrirDetalle(evento) {
        if (!modal) return;
        const actual=++detalleVersion;
        tips.forEach(t=>t.hide());
        try {
            const datos=await json(element.dataset.detailBase.replace("/0/",`/${evento.extendedProps.horario_id}/`));
            if(actual!==detalleVersion)return;
            const e=datos.event,p=e.extendedProps;
            texto("detalle-asignatura",`${p.codigo_asignatura} · ${e.title}`);texto("detalle-profesor",p.profesor);
            texto("detalle-centro",p.centros.join(", "));texto("detalle-facultad",p.facultades.join(", "));texto("detalle-programa",p.programas.join(", "));
            texto("detalle-semestre",p.semestres.join(", "));texto("detalle-grupos",p.grupos.map(g=>`${g.codigo} (${g.programa})`).join(", "));
            texto("detalle-modalidad",p.modalidad);texto("detalle-periodo",p.periodo);texto("detalle-sede",p.sede);texto("detalle-aula",p.aula || "Aula pendiente");
            texto("detalle-bloque",`${dias[p.dia]} · ${p.hora_inicio.slice(0,5)}–${p.hora_fin.slice(0,5)}`);modal.show();
        } catch(e) { if(actual===detalleVersion)error(e.message); }
    }
    modalElement.addEventListener("hidden.bs.modal",()=>{++detalleVersion;});
    periodo.addEventListener("change",function () {
        ++version; ++detalleVersion; if(modal)modal.hide(); tips.forEach(t=>t.hide());
        calendar.removeAllEvents();
        const url=new URL(window.location.href);url.search="";if(periodo.value)url.searchParams.set("periodo_id",periodo.value);window.history.replaceState({},"",url);
        calendar.refetchEvents();
    });
    calendar.render();
});
