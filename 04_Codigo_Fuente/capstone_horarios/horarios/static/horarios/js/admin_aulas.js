document.addEventListener("DOMContentLoaded", function () {
    const sede = document.getElementById("id_sede"), aula = document.getElementById("id_aula");
    if (!sede || !aula || !aula.dataset.urlAulas) return;
    let version = 0;
    sede.addEventListener("change", async function () {
        const actual = ++version;
        aula.replaceChildren(new Option("Aula pendiente", "")); aula.disabled = true;
        try {
            if (!sede.value) return;
            const response = await fetch(`${aula.dataset.urlAulas}?sede=${encodeURIComponent(sede.value)}`, { credentials: "same-origin" });
            if (!response.ok) throw new Error();
            const datos = await response.json(); if (actual !== version) return;
            datos.forEach(a => aula.appendChild(new Option(a.nombre, a.id)));
        } catch (_) { aula.replaceChildren(new Option("No se pudieron cargar aulas; puede guardar con aula pendiente", "")); }
        finally { if (actual === version) aula.disabled = false; }
    });
});
