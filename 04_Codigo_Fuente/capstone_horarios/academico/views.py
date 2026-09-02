from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from horarios.models import Grupo

from .forms import (
    AreaAcademicaForm,
    AsignaturaForm,
    AulaForm,
    CentroTutorialForm,
    FacultadForm,
    GrupoForm,
    ModalidadForm,
    PeriodoAcademicoForm,
    PlanEstudioAsignaturaForm,
    ProfesorForm,
    ProgramaAcademicoForm,
    SedeForm,
    SemestreForm,
)

from .models import (
    AreaAcademica,
    Asignatura,
    Aula,
    CentroTutorial,
    Facultad,
    Modalidad,
    PeriodoAcademico,
    PlanEstudioAsignatura,
    Profesor,
    ProgramaAcademico,
    Sede,
    Semestre,
)

# ==========================================================
# CONFIGURACIÓN GENERAL DE MANTENEDORES
# ==========================================================


MANTENEDORES = {
    # ======================================================
    # PROFESORES
    # ======================================================
    "profesores": {
        "modelo": Profesor,
        "form": ProfesorForm,
        "titulo": "Profesores",
        "singular": "Profesor",
        "descripcion": (
            "Administre los docentes disponibles " "para la planificación académica."
        ),
        "columnas": [
            (
                "Identificación",
                "identificacion",
            ),
            (
                "Profesor",
                "__str__",
            ),
            (
                "Correo institucional",
                "correo_institucional",
            ),
        ],
        "crear_url": "profesor_crear",
        "editar_url": "profesor_editar",
        "eliminar_url": "profesor_eliminar",
        "listado_url": "profesores",
        "perm_add": "academico.add_profesor",
        "perm_change": "academico.change_profesor",
        "perm_delete": "academico.delete_profesor",
        "mostrar_estado": True,
        "queryset": lambda: (
            Profesor.objects.all().order_by(
                "apellido",
                "nombre",
            )
        ),
    },
    # ======================================================
    # CENTROS TUTORIALES
    # ======================================================
    "centros": {
        "modelo": CentroTutorial,
        "form": CentroTutorialForm,
        "titulo": "Centros Tutoriales",
        "singular": "Centro Tutorial",
        "descripcion": ("Administre los Centros Tutoriales " "de la institución."),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Centro Tutorial",
                "nombre",
            ),
        ],
        "crear_url": "centro_tutorial_crear",
        "editar_url": "centro_tutorial_editar",
        "eliminar_url": "centro_tutorial_eliminar",
        "listado_url": "centros_tutoriales",
        "perm_add": "academico.add_centrotutorial",
        "perm_change": "academico.change_centrotutorial",
        "perm_delete": "academico.delete_centrotutorial",
        "mostrar_estado": True,
        "queryset": lambda: (CentroTutorial.objects.all().order_by("nombre")),
    },
    # ======================================================
    # SEDES
    # ======================================================
    "sedes": {
        "modelo": Sede,
        "form": SedeForm,
        "titulo": "Sedes",
        "singular": "Sede",
        "descripcion": (
            "Administre las sedes pertenecientes " "a los Centros Tutoriales."
        ),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Sede",
                "nombre",
            ),
            (
                "Centro Tutorial",
                "centro_tutorial.nombre",
            ),
        ],
        "crear_url": "sede_crear",
        "editar_url": "sede_editar",
        "eliminar_url": "sede_eliminar",
        "listado_url": "sedes",
        "perm_add": "academico.add_sede",
        "perm_change": "academico.change_sede",
        "perm_delete": "academico.delete_sede",
        "mostrar_estado": True,
        "queryset": lambda: (
            Sede.objects.select_related("centro_tutorial")
            .all()
            .order_by(
                "centro_tutorial__nombre",
                "nombre",
            )
        ),
    },
    # ======================================================
    # FACULTADES
    # ======================================================
    "facultades": {
        "modelo": Facultad,
        "form": FacultadForm,
        "titulo": "Facultades",
        "singular": "Facultad",
        "descripcion": ("Administre las Facultades " "académicas de la institución."),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Facultad",
                "nombre",
            ),
        ],
        "crear_url": "facultad_crear",
        "editar_url": "facultad_editar",
        "eliminar_url": "facultad_eliminar",
        "listado_url": "facultades",
        "perm_add": "academico.add_facultad",
        "perm_change": "academico.change_facultad",
        "perm_delete": "academico.delete_facultad",
        "mostrar_estado": True,
        "queryset": lambda: (Facultad.objects.all().order_by("nombre")),
    },
    # ======================================================
    # PROGRAMAS ACADÉMICOS
    # ======================================================
    "programas": {
        "modelo": ProgramaAcademico,
        "form": ProgramaAcademicoForm,
        "titulo": "Programas Académicos",
        "singular": "Programa Académico",
        "descripcion": (
            "Administre los programas académicos, " "su Facultad y Centros Tutoriales."
        ),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Programa Académico",
                "nombre",
            ),
            (
                "Facultad",
                "facultad.nombre",
            ),
        ],
        "crear_url": "programa_crear",
        "editar_url": "programa_editar",
        "eliminar_url": "programa_eliminar",
        "listado_url": "programas_academicos",
        "perm_add": "academico.add_programaacademico",
        "perm_change": "academico.change_programaacademico",
        "perm_delete": "academico.delete_programaacademico",
        "mostrar_estado": True,
        "queryset": lambda: (
            ProgramaAcademico.objects.select_related("facultad")
            .all()
            .order_by(
                "facultad__nombre",
                "nombre",
            )
        ),
    },
    # ======================================================
    # PERIODOS ACADÉMICOS
    # ======================================================
    "periodos": {
        "modelo": PeriodoAcademico,
        "form": PeriodoAcademicoForm,
        "titulo": "Periodos Académicos",
        "singular": "Periodo Académico",
        "descripcion": (
            "Administre los periodos utilizados " "en la planificación académica."
        ),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Periodo",
                "nombre",
            ),
            (
                "Fecha inicio",
                "fecha_inicio",
            ),
            (
                "Fecha término",
                "fecha_fin",
            ),
        ],
        "crear_url": "periodo_crear",
        "editar_url": "periodo_editar",
        "eliminar_url": "periodo_eliminar",
        "listado_url": "periodos_academicos",
        "perm_add": "academico.add_periodoacademico",
        "perm_change": "academico.change_periodoacademico",
        "perm_delete": "academico.delete_periodoacademico",
        "mostrar_estado": True,
        "queryset": lambda: (
            PeriodoAcademico.objects.all().order_by(
                "-fecha_inicio",
                "codigo",
            )
        ),
    },
    # ======================================================
    # SEMESTRES
    # ======================================================
    "semestres": {
        "modelo": Semestre,
        "form": SemestreForm,
        "titulo": "Semestres",
        "singular": "Semestre",
        "descripcion": ("Administre el catálogo de " "semestres académicos."),
        "columnas": [
            (
                "Número",
                "numero",
            ),
            (
                "Semestre",
                "get_numero_display",
            ),
        ],
        "crear_url": "semestre_crear",
        "editar_url": "semestre_editar",
        "eliminar_url": "semestre_eliminar",
        "listado_url": "semestres",
        "perm_add": "academico.add_semestre",
        "perm_change": "academico.change_semestre",
        "perm_delete": "academico.delete_semestre",
        "mostrar_estado": False,
        "queryset": lambda: (Semestre.objects.all().order_by("numero")),
    },
    # ======================================================
    # MODALIDADES
    # ======================================================
    "modalidades": {
        "modelo": Modalidad,
        "form": ModalidadForm,
        "titulo": "Modalidades",
        "singular": "Modalidad",
        "descripcion": ("Administre las modalidades " "académicas disponibles."),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Modalidad",
                "nombre",
            ),
        ],
        "crear_url": "modalidad_crear",
        "editar_url": "modalidad_editar",
        "eliminar_url": "modalidad_eliminar",
        "listado_url": "modalidades",
        "perm_add": "academico.add_modalidad",
        "perm_change": "academico.change_modalidad",
        "perm_delete": "academico.delete_modalidad",
        "mostrar_estado": True,
        "queryset": lambda: (Modalidad.objects.all().order_by("nombre")),
    },
    # ======================================================
    # ÁREAS ACADÉMICAS
    # ======================================================
    "areas": {
        "modelo": AreaAcademica,
        "form": AreaAcademicaForm,
        "titulo": "Áreas Académicas",
        "singular": "Área Académica",
        "descripcion": (
            "Administre las áreas académicas " "utilizadas por los planes de estudio."
        ),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Área Académica",
                "nombre",
            ),
        ],
        "crear_url": "area_crear",
        "editar_url": "area_editar",
        "eliminar_url": "area_eliminar",
        "listado_url": "areas_academicas",
        "perm_add": "academico.add_areaacademica",
        "perm_change": "academico.change_areaacademica",
        "perm_delete": "academico.delete_areaacademica",
        "mostrar_estado": True,
        "queryset": lambda: (AreaAcademica.objects.all().order_by("nombre")),
    },
    # ======================================================
    # ASIGNATURAS
    # ======================================================
    "asignaturas": {
        "modelo": Asignatura,
        "form": AsignaturaForm,
        "titulo": "Asignaturas",
        "singular": "Asignatura",
        "descripcion": ("Administre el catálogo institucional " "de asignaturas."),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Asignatura",
                "nombre",
            ),
        ],
        "crear_url": "asignatura_crear",
        "editar_url": "asignatura_editar",
        "eliminar_url": "asignatura_eliminar",
        "listado_url": "asignaturas",
        "perm_add": "academico.add_asignatura",
        "perm_change": "academico.change_asignatura",
        "perm_delete": "academico.delete_asignatura",
        "mostrar_estado": True,
        "queryset": lambda: (Asignatura.objects.all().order_by("nombre")),
    },
    # ======================================================
    # PLANES DE ESTUDIO
    # ======================================================
    "planes": {
        "modelo": PlanEstudioAsignatura,
        "form": PlanEstudioAsignaturaForm,
        "titulo": "Planes de Estudio",
        "singular": "Asignatura del Plan",
        "descripcion": (
            "Administre las asignaturas, créditos, "
            "semestres y áreas de cada programa."
        ),
        "columnas": [
            (
                "Programa",
                "programa.nombre",
            ),
            (
                "Asignatura",
                "asignatura.nombre",
            ),
            (
                "Semestre",
                "semestre.get_numero_display",
            ),
            (
                "Créditos",
                "creditos",
            ),
            (
                "Área Académica",
                "area_academica.nombre",
            ),
        ],
        "crear_url": "plan_estudio_crear",
        "editar_url": "plan_estudio_editar",
        "eliminar_url": "plan_estudio_eliminar",
        "listado_url": "planes_estudio",
        "perm_add": ("academico.add_planestudioasignatura"),
        "perm_change": ("academico.change_planestudioasignatura"),
        "perm_delete": ("academico.delete_planestudioasignatura"),
        "mostrar_estado": True,
        "queryset": lambda: (
            PlanEstudioAsignatura.objects.select_related(
                "programa",
                "asignatura",
                "semestre",
                "area_academica",
            )
            .all()
            .order_by(
                "programa__nombre",
                "semestre__numero",
                "asignatura__nombre",
            )
        ),
    },
    # ======================================================
    # AULAS
    # ======================================================
    "aulas": {
        "modelo": Aula,
        "form": AulaForm,
        "titulo": "Aulas",
        "singular": "Aula",
        "descripcion": ("Administre los espacios físicos " "y virtuales disponibles."),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Aula",
                "nombre",
            ),
            (
                "Sede",
                "sede.nombre",
            ),
            (
                "Capacidad",
                "capacidad",
            ),
            (
                "Tipo",
                "get_tipo_display",
            ),
        ],
        "crear_url": "aula_crear",
        "editar_url": "aula_editar",
        "eliminar_url": "aula_eliminar",
        "listado_url": "aulas",
        "perm_add": "academico.add_aula",
        "perm_change": "academico.change_aula",
        "perm_delete": "academico.delete_aula",
        "mostrar_estado": True,
        "queryset": lambda: (
            Aula.objects.select_related(
                "sede",
                "sede__centro_tutorial",
            )
            .all()
            .order_by(
                "sede__nombre",
                "nombre",
            )
        ),
    },
    # ======================================================
    # GRUPOS
    # ======================================================
    "grupos": {
        "modelo": Grupo,
        "form": GrupoForm,
        "titulo": "Grupos",
        "singular": "Grupo",
        "descripcion": (
            "Administre los grupos académicos " "por programa, periodo y semestre."
        ),
        "columnas": [
            (
                "Código",
                "codigo",
            ),
            (
                "Programa",
                "programa.nombre",
            ),
            (
                "Centro Tutorial",
                "centro_tutorial.nombre",
            ),
            (
                "Periodo",
                "periodo.nombre",
            ),
            (
                "Semestre",
                "semestre.get_numero_display",
            ),
        ],
        "crear_url": "grupo_crear",
        "editar_url": "grupo_editar",
        "eliminar_url": "grupo_eliminar",
        "listado_url": "grupos",
        "perm_add": "horarios.add_grupo",
        "perm_change": "horarios.change_grupo",
        "perm_delete": "horarios.delete_grupo",
        "mostrar_estado": True,
        "queryset": lambda: (
            Grupo.objects.select_related(
                "programa",
                "centro_tutorial",
                "periodo",
                "semestre",
            )
            .all()
            .order_by(
                "programa__nombre",
                "semestre__numero",
                "codigo",
            )
        ),
    },
}


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================


def obtener_valor(
    objeto,
    ruta,
):
    """
    Obtiene valores dinámicos para construir
    las columnas de los mantenedores.
    """

    if ruta == "__str__":
        return str(objeto)

    valor = objeto

    for atributo in ruta.split("."):

        if valor is None:
            return "—"

        valor = getattr(
            valor,
            atributo,
            None,
        )

        if callable(valor):
            valor = valor()

    if valor is None:
        return "—"

    # Fechas
    if hasattr(
        valor,
        "strftime",
    ):

        try:
            return valor.strftime("%d-%m-%Y")

        except (
            TypeError,
            ValueError,
        ):
            pass

    # Booleanos
    if isinstance(
        valor,
        bool,
    ):

        if valor:
            return "Sí"

        return "No"

    return str(valor)


# ==========================================================
# LISTADO GENÉRICO
# ==========================================================


def listado_generico(
    request,
    clave,
):

    config = MANTENEDORES[clave]

    objetos = config["queryset"]()

    registros = []

    for objeto in objetos:

        valores = []

        for _, ruta in config["columnas"]:

            valores.append(
                obtener_valor(
                    objeto,
                    ruta,
                )
            )

        registros.append(
            {
                "id": objeto.pk,
                "valores": valores,
                "activo": getattr(
                    objeto,
                    "activo",
                    None,
                ),
            }
        )

    context = {
        "titulo": config["titulo"],
        "descripcion": config["descripcion"],
        "columnas": [columna[0] for columna in config["columnas"]],
        "registros": registros,
        "crear_url": config["crear_url"],
        "editar_url": config["editar_url"],
        "eliminar_url": config["eliminar_url"],
        "mostrar_estado": config["mostrar_estado"],
        "puede_crear": (request.user.has_perm(config["perm_add"])),
        "puede_editar": (request.user.has_perm(config["perm_change"])),
        "puede_eliminar": (request.user.has_perm(config["perm_delete"])),
    }

    return render(
        request,
        ("academico/mantenedores/" "lista_generica.html"),
        context,
    )


# ==========================================================
# CREAR GENÉRICO
# ==========================================================


def crear_generico(
    request,
    clave,
):

    config = MANTENEDORES[clave]

    form_class = config["form"]

    if request.method == "POST":

        form = form_class(request.POST)

        if form.is_valid():

            try:

                objeto = form.save()

            except IntegrityError:

                messages.error(
                    request,
                    (
                        "No fue posible guardar el registro "
                        "porque existe información duplicada "
                        "o incompatible."
                    ),
                )

            else:

                messages.success(
                    request,
                    (f'{config["singular"]} ' f'"{objeto}" creado ' "correctamente."),
                )

                return redirect(config["listado_url"])

    else:

        form = form_class()

    context = {
        "form": form,
        "titulo": (f"Nuevo " f'{config["singular"]}'),
        "descripcion": ("Complete la información " "solicitada."),
        "texto_boton": ("Guardar"),
        "listado_url": config["listado_url"],
    }

    return render(
        request,
        ("academico/mantenedores/" "formulario_generico.html"),
        context,
    )


# ==========================================================
# EDITAR GENÉRICO
# ==========================================================


def editar_generico(
    request,
    clave,
    objeto_id,
):

    config = MANTENEDORES[clave]

    objeto = get_object_or_404(
        config["modelo"],
        pk=objeto_id,
    )

    form_class = config["form"]

    if request.method == "POST":

        form = form_class(
            request.POST,
            instance=objeto,
        )

        if form.is_valid():

            try:

                objeto = form.save()

            except IntegrityError:

                messages.error(
                    request,
                    (
                        "No fue posible guardar los cambios "
                        "porque existe información duplicada "
                        "o incompatible."
                    ),
                )

            else:

                messages.success(
                    request,
                    (
                        f'{config["singular"]} '
                        f'"{objeto}" actualizado '
                        "correctamente."
                    ),
                )

                return redirect(config["listado_url"])

    else:

        form = form_class(instance=objeto)

    context = {
        "form": form,
        "titulo": (f"Editar " f'{config["singular"]}'),
        "descripcion": ("Modifique la información " "necesaria."),
        "texto_boton": ("Guardar cambios"),
        "listado_url": config["listado_url"],
    }

    return render(
        request,
        ("academico/mantenedores/" "formulario_generico.html"),
        context,
    )


# ==========================================================
# ELIMINAR GENÉRICO
# ==========================================================


def eliminar_generico(
    request,
    clave,
    objeto_id,
):

    config = MANTENEDORES[clave]

    objeto = get_object_or_404(
        config["modelo"],
        pk=objeto_id,
    )

    detalles = []

    for etiqueta, ruta in config["columnas"]:

        detalles.append(
            (
                etiqueta,
                obtener_valor(
                    objeto,
                    ruta,
                ),
            )
        )

    if request.method == "POST":

        nombre = str(objeto)

        try:

            objeto.delete()

        except (
            ProtectedError,
            IntegrityError,
        ):

            messages.error(
                request,
                (
                    f"No es posible eliminar "
                    f'{config["singular"].lower()} '
                    f'"{nombre}" porque posee '
                    "información asociada. "
                    "Si el mantenedor posee estado, "
                    "puede marcar el registro como "
                    "inactivo en su lugar."
                ),
            )

        else:

            messages.success(
                request,
                (f'{config["singular"]} ' f'"{nombre}" eliminado ' "correctamente."),
            )

        return redirect(config["listado_url"])

    context = {
        "titulo": (f"Eliminar " f'{config["singular"]}'),
        "singular": config["singular"],
        "detalles": detalles,
        "listado_url": config["listado_url"],
    }

    return render(
        request,
        ("academico/mantenedores/" "eliminar_generico.html"),
        context,
    )


# ==========================================================
# PANEL DE MANTENEDORES
# ==========================================================


@login_required
def mantenedores(
    request,
):

    return render(
        request,
        "academico/mantenedores.html",
    )


# ==========================================================
# PROFESORES
# ==========================================================


@login_required
@permission_required(
    "academico.view_profesor",
    raise_exception=True,
)
def profesores(
    request,
):

    return listado_generico(
        request,
        "profesores",
    )


@login_required
@permission_required(
    "academico.add_profesor",
    raise_exception=True,
)
def profesor_crear(
    request,
):

    return crear_generico(
        request,
        "profesores",
    )


@login_required
@permission_required(
    "academico.change_profesor",
    raise_exception=True,
)
def profesor_editar(
    request,
    profesor_id,
):

    return editar_generico(
        request,
        "profesores",
        profesor_id,
    )


@login_required
@permission_required(
    "academico.delete_profesor",
    raise_exception=True,
)
def profesor_eliminar(
    request,
    profesor_id,
):

    return eliminar_generico(
        request,
        "profesores",
        profesor_id,
    )


# ==========================================================
# CENTROS TUTORIALES
# ==========================================================


@login_required
@permission_required(
    "academico.view_centrotutorial",
    raise_exception=True,
)
def centros_tutoriales(
    request,
):

    return listado_generico(
        request,
        "centros",
    )


@login_required
@permission_required(
    "academico.add_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_crear(
    request,
):

    return crear_generico(
        request,
        "centros",
    )


@login_required
@permission_required(
    "academico.change_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_editar(
    request,
    centro_id,
):

    return editar_generico(
        request,
        "centros",
        centro_id,
    )


@login_required
@permission_required(
    "academico.delete_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_eliminar(
    request,
    centro_id,
):

    return eliminar_generico(
        request,
        "centros",
        centro_id,
    )


# ==========================================================
# SEDES
# ==========================================================


@login_required
@permission_required(
    "academico.view_sede",
    raise_exception=True,
)
def sedes(
    request,
):

    return listado_generico(
        request,
        "sedes",
    )


@login_required
@permission_required(
    "academico.add_sede",
    raise_exception=True,
)
def sede_crear(
    request,
):

    return crear_generico(
        request,
        "sedes",
    )


@login_required
@permission_required(
    "academico.change_sede",
    raise_exception=True,
)
def sede_editar(
    request,
    sede_id,
):

    return editar_generico(
        request,
        "sedes",
        sede_id,
    )


@login_required
@permission_required(
    "academico.delete_sede",
    raise_exception=True,
)
def sede_eliminar(
    request,
    sede_id,
):

    return eliminar_generico(
        request,
        "sedes",
        sede_id,
    )


# ==========================================================
# FACULTADES
# ==========================================================


@login_required
@permission_required(
    "academico.view_facultad",
    raise_exception=True,
)
def facultades(
    request,
):

    return listado_generico(
        request,
        "facultades",
    )


@login_required
@permission_required(
    "academico.add_facultad",
    raise_exception=True,
)
def facultad_crear(
    request,
):

    return crear_generico(
        request,
        "facultades",
    )


@login_required
@permission_required(
    "academico.change_facultad",
    raise_exception=True,
)
def facultad_editar(
    request,
    facultad_id,
):

    return editar_generico(
        request,
        "facultades",
        facultad_id,
    )


@login_required
@permission_required(
    "academico.delete_facultad",
    raise_exception=True,
)
def facultad_eliminar(
    request,
    facultad_id,
):

    return eliminar_generico(
        request,
        "facultades",
        facultad_id,
    )


# ==========================================================
# PROGRAMAS ACADÉMICOS
# ==========================================================


@login_required
@permission_required(
    "academico.view_programaacademico",
    raise_exception=True,
)
def programas_academicos(
    request,
):

    return listado_generico(
        request,
        "programas",
    )


@login_required
@permission_required(
    "academico.add_programaacademico",
    raise_exception=True,
)
def programa_crear(
    request,
):

    return crear_generico(
        request,
        "programas",
    )


@login_required
@permission_required(
    "academico.change_programaacademico",
    raise_exception=True,
)
def programa_editar(
    request,
    programa_id,
):

    return editar_generico(
        request,
        "programas",
        programa_id,
    )


@login_required
@permission_required(
    "academico.delete_programaacademico",
    raise_exception=True,
)
def programa_eliminar(
    request,
    programa_id,
):

    return eliminar_generico(
        request,
        "programas",
        programa_id,
    )


# ==========================================================
# PERIODOS ACADÉMICOS
# ==========================================================


@login_required
@permission_required(
    "academico.view_periodoacademico",
    raise_exception=True,
)
def periodos_academicos(
    request,
):

    return listado_generico(
        request,
        "periodos",
    )


@login_required
@permission_required(
    "academico.add_periodoacademico",
    raise_exception=True,
)
def periodo_crear(
    request,
):

    return crear_generico(
        request,
        "periodos",
    )


@login_required
@permission_required(
    "academico.change_periodoacademico",
    raise_exception=True,
)
def periodo_editar(
    request,
    periodo_id,
):

    return editar_generico(
        request,
        "periodos",
        periodo_id,
    )


@login_required
@permission_required(
    "academico.delete_periodoacademico",
    raise_exception=True,
)
def periodo_eliminar(
    request,
    periodo_id,
):

    return eliminar_generico(
        request,
        "periodos",
        periodo_id,
    )


# ==========================================================
# SEMESTRES
# ==========================================================


@login_required
@permission_required(
    "academico.view_semestre",
    raise_exception=True,
)
def semestres(
    request,
):

    return listado_generico(
        request,
        "semestres",
    )


@login_required
@permission_required(
    "academico.add_semestre",
    raise_exception=True,
)
def semestre_crear(
    request,
):

    return crear_generico(
        request,
        "semestres",
    )


@login_required
@permission_required(
    "academico.change_semestre",
    raise_exception=True,
)
def semestre_editar(
    request,
    semestre_id,
):

    return editar_generico(
        request,
        "semestres",
        semestre_id,
    )


@login_required
@permission_required(
    "academico.delete_semestre",
    raise_exception=True,
)
def semestre_eliminar(
    request,
    semestre_id,
):

    return eliminar_generico(
        request,
        "semestres",
        semestre_id,
    )


# ==========================================================
# MODALIDADES
# ==========================================================


@login_required
@permission_required(
    "academico.view_modalidad",
    raise_exception=True,
)
def modalidades(
    request,
):

    return listado_generico(
        request,
        "modalidades",
    )


@login_required
@permission_required(
    "academico.add_modalidad",
    raise_exception=True,
)
def modalidad_crear(
    request,
):

    return crear_generico(
        request,
        "modalidades",
    )


@login_required
@permission_required(
    "academico.change_modalidad",
    raise_exception=True,
)
def modalidad_editar(
    request,
    modalidad_id,
):

    return editar_generico(
        request,
        "modalidades",
        modalidad_id,
    )


@login_required
@permission_required(
    "academico.delete_modalidad",
    raise_exception=True,
)
def modalidad_eliminar(
    request,
    modalidad_id,
):

    return eliminar_generico(
        request,
        "modalidades",
        modalidad_id,
    )


# ==========================================================
# ÁREAS ACADÉMICAS
# ==========================================================


@login_required
@permission_required(
    "academico.view_areaacademica",
    raise_exception=True,
)
def areas_academicas(
    request,
):

    return listado_generico(
        request,
        "areas",
    )


@login_required
@permission_required(
    "academico.add_areaacademica",
    raise_exception=True,
)
def area_crear(
    request,
):

    return crear_generico(
        request,
        "areas",
    )


@login_required
@permission_required(
    "academico.change_areaacademica",
    raise_exception=True,
)
def area_editar(
    request,
    area_id,
):

    return editar_generico(
        request,
        "areas",
        area_id,
    )


@login_required
@permission_required(
    "academico.delete_areaacademica",
    raise_exception=True,
)
def area_eliminar(
    request,
    area_id,
):

    return eliminar_generico(
        request,
        "areas",
        area_id,
    )


# ==========================================================
# ASIGNATURAS
# ==========================================================


@login_required
@permission_required(
    "academico.view_asignatura",
    raise_exception=True,
)
def asignaturas(
    request,
):

    return listado_generico(
        request,
        "asignaturas",
    )


@login_required
@permission_required(
    "academico.add_asignatura",
    raise_exception=True,
)
def asignatura_crear(
    request,
):

    return crear_generico(
        request,
        "asignaturas",
    )


@login_required
@permission_required(
    "academico.change_asignatura",
    raise_exception=True,
)
def asignatura_editar(
    request,
    asignatura_id,
):

    return editar_generico(
        request,
        "asignaturas",
        asignatura_id,
    )


@login_required
@permission_required(
    "academico.delete_asignatura",
    raise_exception=True,
)
def asignatura_eliminar(
    request,
    asignatura_id,
):

    return eliminar_generico(
        request,
        "asignaturas",
        asignatura_id,
    )


# ==========================================================
# PLANES DE ESTUDIO
# ==========================================================


@login_required
@permission_required(
    "academico.view_planestudioasignatura",
    raise_exception=True,
)
def planes_estudio(
    request,
):

    return listado_generico(
        request,
        "planes",
    )


@login_required
@permission_required(
    "academico.add_planestudioasignatura",
    raise_exception=True,
)
def plan_estudio_crear(
    request,
):

    return crear_generico(
        request,
        "planes",
    )


@login_required
@permission_required(
    "academico.change_planestudioasignatura",
    raise_exception=True,
)
def plan_estudio_editar(
    request,
    plan_id,
):

    return editar_generico(
        request,
        "planes",
        plan_id,
    )


@login_required
@permission_required(
    "academico.delete_planestudioasignatura",
    raise_exception=True,
)
def plan_estudio_eliminar(
    request,
    plan_id,
):

    return eliminar_generico(
        request,
        "planes",
        plan_id,
    )


# ==========================================================
# AULAS
# ==========================================================


@login_required
@permission_required(
    "academico.view_aula",
    raise_exception=True,
)
def aulas(
    request,
):

    return listado_generico(
        request,
        "aulas",
    )


@login_required
@permission_required(
    "academico.add_aula",
    raise_exception=True,
)
def aula_crear(
    request,
):

    return crear_generico(
        request,
        "aulas",
    )


@login_required
@permission_required(
    "academico.change_aula",
    raise_exception=True,
)
def aula_editar(
    request,
    aula_id,
):

    return editar_generico(
        request,
        "aulas",
        aula_id,
    )


@login_required
@permission_required(
    "academico.delete_aula",
    raise_exception=True,
)
def aula_eliminar(
    request,
    aula_id,
):

    return eliminar_generico(
        request,
        "aulas",
        aula_id,
    )


# ==========================================================
# GRUPOS
# ==========================================================


@login_required
@permission_required(
    "horarios.view_grupo",
    raise_exception=True,
)
def grupos(
    request,
):

    return listado_generico(
        request,
        "grupos",
    )


@login_required
@permission_required(
    "horarios.add_grupo",
    raise_exception=True,
)
def grupo_crear(
    request,
):

    return crear_generico(
        request,
        "grupos",
    )


@login_required
@permission_required(
    "horarios.change_grupo",
    raise_exception=True,
)
def grupo_editar(
    request,
    grupo_id,
):

    return editar_generico(
        request,
        "grupos",
        grupo_id,
    )


@login_required
@permission_required(
    "horarios.delete_grupo",
    raise_exception=True,
)
def grupo_eliminar(
    request,
    grupo_id,
):

    return eliminar_generico(
        request,
        "grupos",
        grupo_id,
    )
