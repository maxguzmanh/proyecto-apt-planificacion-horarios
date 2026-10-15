document.addEventListener("DOMContentLoaded", function () {
    if (typeof DataTable !== "function") return;

    document.querySelectorAll("table.maintenance-datatable").forEach(function (tabla) {
        const columnas = tabla.querySelectorAll("thead th");
        const definiciones = columnas.length ? [{ targets: columnas.length - 1, orderable: false, searchable: false }] : [];
        if (tabla.dataset.maintainer === "semestres") {
            definiciones.unshift({ targets: 0, width: "120px", className: "maintenance-column-left" });
            definiciones.unshift({ targets: 1, className: "maintenance-column-left" });
        }
        new DataTable(tabla, {
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100],
            order: [],
            scrollX: true,
            columnDefs: definiciones,
            layout: {
                topStart: "pageLength",
                topEnd: "search",
                bottomStart: "info",
                bottomEnd: "paging"
            },
            language: {
                search: "Buscar:",
                lengthMenu: "Mostrar _MENU_ filas",
                info: "_START_–_END_ de _TOTAL_ registros",
                infoEmpty: "0 registros",
                zeroRecords: "No se encontraron registros",
                emptyTable: "No existen registros",
                paginate: { previous: "Anterior", next: "Siguiente" }
            }
        });
        tabla.closest(".table-responsive")?.classList.add("maintenance-datatable-wrapper");
    });
});
