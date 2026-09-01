document.addEventListener("DOMContentLoaded", function () {

    const centro = document.getElementById("centro");
    const sede = document.getElementById("sede");
    const facultad = document.getElementById("facultad");
    const programa = document.getElementById("programa");
    const periodo = document.getElementById("periodo");
    const semestre = document.getElementById("semestre");

    if (!centro) {
        return;
    }


    // =====================================================
    // FUNCIONES AUXILIARES
    // =====================================================

    function limpiarSelect(
        select,
        texto = "Seleccione..."
    ) {

        select.innerHTML = "";

        const option = document.createElement("option");

        option.value = "";
        option.textContent = texto;

        select.appendChild(option);

        select.disabled = true;
    }


    function habilitarSelect(select) {
        select.disabled = false;
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
        campoTexto = "nombre"
    ) {

        datos.forEach((registro) => {

            const option = document.createElement("option");

            option.value = registro.id;
            option.textContent = registro[campoTexto];

            select.appendChild(option);
        });

        habilitarSelect(select);
    }


    // =====================================================
    // CENTRO TUTORIAL
    // =====================================================

    centro.addEventListener(
        "change",
        async function () {

            const centroId = this.value;

            limpiarSelect(
                sede,
                "Seleccione una sede..."
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

            if (!centroId) {
                return;
            }

            try {

                // -----------------------------------------
                // SEDES
                // -----------------------------------------

                const sedes = await obtenerDatos(
                    `/ajax/sedes/?centro=${centroId}`
                );

                cargarOpciones(
                    sede,
                    sedes
                );


                // -----------------------------------------
                // FACULTADES
                // -----------------------------------------

                const facultades = await obtenerDatos(
                    `/ajax/facultades/?centro=${centroId}`
                );

                cargarOpciones(
                    facultad,
                    facultades
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // FACULTAD
    // =====================================================

    facultad.addEventListener(
        "change",
        async function () {

            const facultadId = this.value;
            const centroId = centro.value;

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

            if (
                !facultadId
                || !centroId
            ) {
                return;
            }

            try {

                const programas = await obtenerDatos(
                    `/ajax/programas/`
                    + `?facultad=${facultadId}`
                    + `&centro=${centroId}`
                );

                cargarOpciones(
                    programa,
                    programas
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // PROGRAMA ACADÉMICO
    // =====================================================

    programa.addEventListener(
        "change",
        async function () {

            const programaId = this.value;
            const centroId = centro.value;

            limpiarSelect(
                periodo,
                "Seleccione un periodo..."
            );

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            if (
                !programaId
                || !centroId
            ) {
                return;
            }

            try {

                const periodos = await obtenerDatos(
                    `/ajax/periodos/`
                    + `?programa=${programaId}`
                    + `&centro=${centroId}`
                );

                cargarOpciones(
                    periodo,
                    periodos
                );

            } catch (error) {

                console.error(error);
            }
        }
    );


    // =====================================================
    // PERIODO ACADÉMICO
    // =====================================================

    periodo.addEventListener(
        "change",
        async function () {

            const periodoId = this.value;
            const programaId = programa.value;
            const centroId = centro.value;

            limpiarSelect(
                semestre,
                "Seleccione un semestre..."
            );

            if (
                !periodoId
                || !programaId
                || !centroId
            ) {
                return;
            }

            try {

                const semestres = await obtenerDatos(
                    `/ajax/semestres/`
                    + `?programa=${programaId}`
                    + `&centro=${centroId}`
                    + `&periodo=${periodoId}`
                );

                cargarOpciones(
                    semestre,
                    semestres,
                    "nombre"
                );

            } catch (error) {

                console.error(error);
            }
        }
    );

});