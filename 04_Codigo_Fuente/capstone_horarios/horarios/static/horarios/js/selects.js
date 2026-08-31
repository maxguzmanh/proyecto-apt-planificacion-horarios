document.addEventListener("DOMContentLoaded", function () {

    const centro = document.getElementById("centro");
    const sede = document.getElementById("sede");
    const facultad = document.getElementById("facultad");
    const carrera = document.getElementById("carrera");
    const periodo = document.getElementById("periodo");
    const semestre = document.getElementById("semestre");


    function limpiarSelect(select, mensaje) {
        select.innerHTML = "";

        const option = document.createElement("option");

        option.value = "";
        option.textContent = mensaje;

        select.appendChild(option);
        select.disabled = true;
    }


    function cargarOpciones(select, datos, campoTexto) {

        select.innerHTML = "";

        const opcionInicial = document.createElement("option");

        opcionInicial.value = "";
        opcionInicial.textContent = "Seleccione...";

        select.appendChild(opcionInicial);


        datos.forEach(function (item) {

            const option = document.createElement("option");

            option.value = item.id;
            option.textContent = item[campoTexto];

            select.appendChild(option);

        });


        select.disabled = false;
    }


    centro.addEventListener("change", async function () {

        limpiarSelect(
            sede,
            "Seleccione primero un Centro Tutorial..."
        );

        limpiarSelect(
            facultad,
            "Seleccione primero una Sede..."
        );

        limpiarSelect(
            carrera,
            "Seleccione primero una Facultad..."
        );

        limpiarSelect(
            periodo,
            "Seleccione primero una Carrera..."
        );

        limpiarSelect(
            semestre,
            "Seleccione primero un Periodo..."
        );


        if (!centro.value) {
            return;
        }


        const response = await fetch(
            `/ajax/sedes/?centro=${centro.value}`
        );

        const datos = await response.json();

        cargarOpciones(
            sede,
            datos,
            "nombre"
        );

    });


    sede.addEventListener("change", async function () {

        limpiarSelect(
            facultad,
            "Seleccione primero una Sede..."
        );

        limpiarSelect(
            carrera,
            "Seleccione primero una Facultad..."
        );

        limpiarSelect(
            periodo,
            "Seleccione primero una Carrera..."
        );

        limpiarSelect(
            semestre,
            "Seleccione primero un Periodo..."
        );


        if (!sede.value) {
            return;
        }


        const response = await fetch(
            `/ajax/facultades/?sede=${sede.value}`
        );

        const datos = await response.json();

        cargarOpciones(
            facultad,
            datos,
            "nombre"
        );

    });


    facultad.addEventListener("change", async function () {

        limpiarSelect(
            carrera,
            "Seleccione primero una Facultad..."
        );

        limpiarSelect(
            periodo,
            "Seleccione primero una Carrera..."
        );

        limpiarSelect(
            semestre,
            "Seleccione primero un Periodo..."
        );


        if (!facultad.value) {
            return;
        }


        const response = await fetch(
            `/ajax/carreras/?facultad=${facultad.value}`
        );

        const datos = await response.json();

        cargarOpciones(
            carrera,
            datos,
            "nombre"
        );

    });


    carrera.addEventListener("change", async function () {

        limpiarSelect(
            periodo,
            "Seleccione primero una Carrera..."
        );

        limpiarSelect(
            semestre,
            "Seleccione primero un Periodo..."
        );


        if (!carrera.value) {
            return;
        }


        const response = await fetch(
            `/ajax/periodos/?carrera=${carrera.value}`
        );

        const datos = await response.json();

        cargarOpciones(
            periodo,
            datos,
            "nombre"
        );

    });


    periodo.addEventListener("change", async function () {

        limpiarSelect(
            semestre,
            "Seleccione primero un Periodo..."
        );


        if (!periodo.value || !carrera.value) {
            return;
        }


        const response = await fetch(
            `/ajax/semestres/?carrera=${carrera.value}&periodo=${periodo.value}`
        );

        const datos = await response.json();


        semestre.innerHTML = "";

        const opcionInicial = document.createElement("option");

        opcionInicial.value = "";
        opcionInicial.textContent = "Seleccione...";

        semestre.appendChild(opcionInicial);


        datos.forEach(function (item) {

            const option = document.createElement("option");

            option.value = item.id;
            option.textContent = `Semestre ${item.numero}`;

            semestre.appendChild(option);

        });


        semestre.disabled = false;

    });

});