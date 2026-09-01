document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // ELEMENTOS
    // =====================================================

    const form = document.getElementById(
        "filtros-planificacion"
    );

    const centro = document.getElementById("centro");
    const sede = document.getElementById("sede");
    const facultad = document.getElementById("facultad");
    const programa = document.getElementById("programa");
    const periodo = document.getElementById("periodo");
    const semestre = document.getElementById("semestre");
    const grupo = document.getElementById("grupo");


    if (!form || !centro) {
        return;
    }


    // =====================================================
    // SELECCIONES ACTUALES
    // =====================================================

    const seleccion = {

        centro:
            form.dataset.selectedCentro || "",

        sede:
            form.dataset.selectedSede || "",

        facultad:
            form.dataset.selectedFacultad || "",

        programa:
            form.dataset.selectedPrograma || "",

        periodo:
            form.dataset.selectedPeriodo || "",

        semestre:
            form.dataset.selectedSemestre || "",

        grupo:
            form.dataset.selectedGrupo || "",
    };


    // =====================================================
    // UTILIDADES
    // =====================================================

    function limpiarSelect(
        select,
        texto
    ) {

        if (!select) {
            return;
        }

        select.innerHTML = "";

        const option =
            document.createElement("option");

        option.value = "";
        option.textContent = texto;

        select.appendChild(option);

        select.disabled = true;
    }


    function prepararSelect(
        select,
        texto
    ) {

        if (!select) {
            return;
        }

        select.innerHTML = "";

        const option =
            document.createElement("option");

        option.value = "";
        option.textContent = texto;

        select.appendChild(option);
    }


    async function obtenerDatos(url) {

        const response = await fetch(url);

        if (!response.ok) {

            throw new Error(
                "No fue posible obtener los datos."
            );
        }

        return await response.json();
    }


    function cargarOpciones(
        select,
        datos,
        campoTexto,
        valorSeleccionado = "",
        textoVacio = "No hay opciones disponibles"
    ) {

        if (!select) {
            return;
        }


        if (!datos.length) {

            limpiarSelect(
                select,
                textoVacio
            );

            return;
        }


        datos.forEach(
            function (registro) {

                const option =
                    document.createElement("option");

                option.value =
                    registro.id;

                option.textContent =
                    registro[campoTexto];

                select.appendChild(option);
            }
        );


        select.disabled = false;


        if (valorSeleccionado) {

            select.value =
                String(valorSeleccionado);
        }
    }


    // =====================================================
    // CARGAR SEDES
    // =====================================================

    async function cargarSedes(
        centroId,
        seleccionado = ""
    ) {

        prepararSelect(
            sede,
            "Todas las sedes"
        );


        const datos = await obtenerDatos(
            `/ajax/sedes/?centro=${centroId}`
        );


        cargarOpciones(
            sede,
            datos,
            "nombre",
            seleccionado,
            "No hay sedes disponibles"
        );
    }


    // =====================================================
    // CARGAR FACULTADES
    // =====================================================

    async function cargarFacultades(
        centroId,
        seleccionado = ""
    ) {

        prepararSelect(
            facultad,
            "Seleccione una facultad..."
        );


        const datos = await obtenerDatos(
            `/ajax/facultades/?centro=${centroId}`
        );


        cargarOpciones(
            facultad,
            datos,
            "nombre",
            seleccionado,
            "No hay facultades disponibles"
        );
    }


    // =====================================================
    // CARGAR PROGRAMAS
    // =====================================================

    async function cargarProgramas(
        centroId,
        facultadId,
        seleccionado = ""
    ) {

        prepararSelect(
            programa,
            "Seleccione un programa..."
        );


        const datos = await obtenerDatos(
            `/ajax/programas/`
            + `?centro=${centroId}`
            + `&facultad=${facultadId}`
        );


        cargarOpciones(
            programa,
            datos,
            "nombre",
            seleccionado,
            "No hay programas disponibles"
        );
    }


    // =====================================================
    // CARGAR PERIODOS
    // =====================================================

    async function cargarPeriodos(
        centroId,
        programaId,
        seleccionado = ""
    ) {

        prepararSelect(
            periodo,
            "Seleccione un periodo..."
        );


        const datos = await obtenerDatos(
            `/ajax/periodos/`
            + `?centro=${centroId}`
            + `&programa=${programaId}`
        );


        cargarOpciones(
            periodo,
            datos,
            "nombre",
            seleccionado,
            "No hay periodos disponibles"
        );
    }


    // =====================================================
    // CARGAR SEMESTRES
    // =====================================================

    async function cargarSemestres(
        centroId,
        programaId,
        periodoId,
        seleccionado = ""
    ) {

        prepararSelect(
            semestre,
            "Seleccione un semestre..."
        );


        const datos = await obtenerDatos(
            `/ajax/semestres/`
            + `?centro=${centroId}`
            + `&programa=${programaId}`
            + `&periodo=${periodoId}`
        );


        cargarOpciones(
            semestre,
            datos,
            "nombre",
            seleccionado,
            "No hay semestres disponibles"
        );
    }


    // =====================================================
    // CARGAR GRUPOS
    // =====================================================

    async function cargarGrupos(
        centroId,
        programaId,
        periodoId,
        semestreId,
        seleccionado = ""
    ) {

        prepararSelect(
            grupo,
            "Todos los grupos"
        );


        const datos = await obtenerDatos(
            `/ajax/grupos/`
            + `?centro=${centroId}`
            + `&programa=${programaId}`
            + `&periodo=${periodoId}`
            + `&semestre=${semestreId}`
        );


        if (!datos.length) {

            limpiarSelect(
                grupo,
                "No hay grupos disponibles"
            );

            return;
        }


        cargarOpciones(
            grupo,
            datos,
            "codigo",
            seleccionado
        );


        grupo.disabled = false;
    }


    // =====================================================
    // EVENTO CENTRO
    // =====================================================

    centro.addEventListener(
        "change",
        async function () {

            const centroId =
                centro.value;


            limpiarSelect(
                sede,
                "Todas las sedes"
            );

            limpiarSelect(
                facultad,
                "Seleccione una facultad..."
            );

            limpiarSelect(
                programa,
                "Seleccione un programa..."
            );

            limpiarSelect(
                periodo,
                "Seleccione un periodo..."
            );

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            limpiarSelect(
                grupo,
                "Todos los grupos"
            );


            if (!centroId) {
                return;
            }


            try {

                await Promise.all(
                    [
                        cargarSedes(
                            centroId
                        ),

                        cargarFacultades(
                            centroId
                        ),
                    ]
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // EVENTO FACULTAD
    // =====================================================

    facultad.addEventListener(
        "change",
        async function () {

            limpiarSelect(
                programa,
                "Seleccione un programa..."
            );

            limpiarSelect(
                periodo,
                "Seleccione un periodo..."
            );

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            limpiarSelect(
                grupo,
                "Todos los grupos"
            );


            if (
                !centro.value
                || !facultad.value
            ) {
                return;
            }


            try {

                await cargarProgramas(
                    centro.value,
                    facultad.value
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // EVENTO PROGRAMA
    // =====================================================

    programa.addEventListener(
        "change",
        async function () {

            limpiarSelect(
                periodo,
                "Seleccione un periodo..."
            );

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            limpiarSelect(
                grupo,
                "Todos los grupos"
            );


            if (
                !centro.value
                || !programa.value
            ) {
                return;
            }


            try {

                await cargarPeriodos(
                    centro.value,
                    programa.value
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // EVENTO PERIODO
    // =====================================================

    periodo.addEventListener(
        "change",
        async function () {

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            limpiarSelect(
                grupo,
                "Todos los grupos"
            );


            if (
                !centro.value
                || !programa.value
                || !periodo.value
            ) {
                return;
            }


            try {

                await cargarSemestres(
                    centro.value,
                    programa.value,
                    periodo.value
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // EVENTO SEMESTRE
    // =====================================================

    semestre.addEventListener(
        "change",
        async function () {

            limpiarSelect(
                grupo,
                "Todos los grupos"
            );


            if (
                !centro.value
                || !programa.value
                || !periodo.value
                || !semestre.value
            ) {
                return;
            }


            try {

                await cargarGrupos(
                    centro.value,
                    programa.value,
                    periodo.value,
                    semestre.value
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // RESTAURAR FILTROS AL RECARGAR
    // =====================================================

    async function restaurarSeleccion() {

        if (!seleccion.centro) {
            return;
        }


        centro.value =
            seleccion.centro;


        try {

            // ----------------------------------------------
            // SEDE + FACULTAD
            // ----------------------------------------------

            await Promise.all(
                [
                    cargarSedes(
                        seleccion.centro,
                        seleccion.sede
                    ),

                    cargarFacultades(
                        seleccion.centro,
                        seleccion.facultad
                    ),
                ]
            );


            // ----------------------------------------------
            // PROGRAMA
            // ----------------------------------------------

            if (seleccion.facultad) {

                await cargarProgramas(
                    seleccion.centro,
                    seleccion.facultad,
                    seleccion.programa
                );
            }


            // ----------------------------------------------
            // PERIODO
            // ----------------------------------------------

            if (seleccion.programa) {

                await cargarPeriodos(
                    seleccion.centro,
                    seleccion.programa,
                    seleccion.periodo
                );
            }


            // ----------------------------------------------
            // SEMESTRE
            // ----------------------------------------------

            if (
                seleccion.programa
                && seleccion.periodo
            ) {

                await cargarSemestres(
                    seleccion.centro,
                    seleccion.programa,
                    seleccion.periodo,
                    seleccion.semestre
                );
            }


            // ----------------------------------------------
            // GRUPO
            // ----------------------------------------------

            if (
                seleccion.programa
                && seleccion.periodo
                && seleccion.semestre
            ) {

                await cargarGrupos(
                    seleccion.centro,
                    seleccion.programa,
                    seleccion.periodo,
                    seleccion.semestre,
                    seleccion.grupo
                );
            }

        } catch (error) {

            console.error(
                "Error restaurando filtros:",
                error
            );
        }
    }


    restaurarSeleccion();

});