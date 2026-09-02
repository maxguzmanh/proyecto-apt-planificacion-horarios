from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import (
    CentroTutorialForm,
    ProfesorForm,
    SedeForm,
)

from .models import (
    CentroTutorial,
    Profesor,
    Sede,
)

from django.db.models.deletion import ProtectedError

# ==========================================================
# MANTENEDORES
# ==========================================================


@login_required
def mantenedores(request):

    return render(
        request,
        "academico/mantenedores.html",
    )


# ==========================================================
# PROFESORES - LISTADO
# ==========================================================


@login_required
@permission_required(
    "academico.view_profesor",
    raise_exception=True,
)
def profesores(request):

    profesores_lista = Profesor.objects.all().order_by(
        "apellido",
        "nombre",
    )

    context = {
        "profesores": profesores_lista,
    }

    return render(
        request,
        "academico/profesores/lista.html",
        context,
    )


# ==========================================================
# PROFESORES - CREAR
# ==========================================================


@login_required
@permission_required(
    "academico.add_profesor",
    raise_exception=True,
)
def profesor_crear(request):

    if request.method == "POST":

        form = ProfesorForm(request.POST)

        if form.is_valid():

            profesor = form.save()

            messages.success(
                request,
                (f'Profesor "{profesor}" ' "creado correctamente."),
            )

            return redirect("profesores")

    else:

        form = ProfesorForm()

    context = {
        "form": form,
        "titulo": "Nuevo profesor",
        "texto_boton": "Guardar profesor",
    }

    return render(
        request,
        "academico/profesores/formulario.html",
        context,
    )


# ==========================================================
# PROFESORES - EDITAR
# ==========================================================


@login_required
@permission_required(
    "academico.change_profesor",
    raise_exception=True,
)
def profesor_editar(
    request,
    profesor_id,
):

    profesor = get_object_or_404(
        Profesor,
        pk=profesor_id,
    )

    if request.method == "POST":

        form = ProfesorForm(
            request.POST,
            instance=profesor,
        )

        if form.is_valid():

            profesor = form.save()

            messages.success(
                request,
                (f'Profesor "{profesor}" ' "actualizado correctamente."),
            )

            return redirect("profesores")

    else:

        form = ProfesorForm(instance=profesor)

    context = {
        "form": form,
        "profesor": profesor,
        "titulo": "Editar profesor",
        "texto_boton": "Guardar cambios",
    }

    return render(
        request,
        "academico/profesores/formulario.html",
        context,
    )


# ==========================================================
# PROFESORES - ELIMINAR
# ==========================================================


@login_required
@permission_required(
    "academico.delete_profesor",
    raise_exception=True,
)
def profesor_eliminar(
    request,
    profesor_id,
):

    profesor = get_object_or_404(
        Profesor,
        pk=profesor_id,
    )

    if request.method == "POST":

        nombre = str(profesor)

        try:

            profesor.delete()

        except ProtectedError:

            messages.error(
                request,
                (
                    f"No es posible eliminar al profesor "
                    f'"{nombre}" porque posee información '
                    "académica asociada. Puede marcarlo "
                    "como inactivo en su lugar."
                ),
            )

            return redirect("profesores")

        messages.success(
            request,
            (f'Profesor "{nombre}" ' "eliminado correctamente."),
        )

        return redirect("profesores")

    context = {
        "profesor": profesor,
    }

    return render(
        request,
        "academico/profesores/eliminar.html",
        context,
    )


# ==========================================================
# CENTROS TUTORIALES - LISTADO
# ==========================================================


@login_required
@permission_required(
    "academico.view_centrotutorial",
    raise_exception=True,
)
def centros_tutoriales(request):

    centros = CentroTutorial.objects.all().order_by(
        "nombre",
    )

    context = {
        "centros": centros,
    }

    return render(
        request,
        "academico/centros_tutoriales/lista.html",
        context,
    )


# ==========================================================
# CENTROS TUTORIALES - CREAR
# ==========================================================


@login_required
@permission_required(
    "academico.add_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_crear(request):

    if request.method == "POST":

        form = CentroTutorialForm(request.POST)

        if form.is_valid():

            centro = form.save()

            messages.success(
                request,
                (f'Centro Tutorial "{centro.nombre}" ' "creado correctamente."),
            )

            return redirect("centros_tutoriales")

    else:

        form = CentroTutorialForm()

    context = {
        "form": form,
        "titulo": "Nuevo Centro Tutorial",
        "texto_boton": "Guardar Centro Tutorial",
    }

    return render(
        request,
        "academico/centros_tutoriales/formulario.html",
        context,
    )


# ==========================================================
# CENTROS TUTORIALES - EDITAR
# ==========================================================


@login_required
@permission_required(
    "academico.change_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_editar(
    request,
    centro_id,
):

    centro = get_object_or_404(
        CentroTutorial,
        pk=centro_id,
    )

    if request.method == "POST":

        form = CentroTutorialForm(
            request.POST,
            instance=centro,
        )

        if form.is_valid():

            centro = form.save()

            messages.success(
                request,
                (f'Centro Tutorial "{centro.nombre}" ' "actualizado correctamente."),
            )

            return redirect("centros_tutoriales")

    else:

        form = CentroTutorialForm(
            instance=centro,
        )

    context = {
        "form": form,
        "centro": centro,
        "titulo": "Editar Centro Tutorial",
        "texto_boton": "Guardar cambios",
    }

    return render(
        request,
        "academico/centros_tutoriales/formulario.html",
        context,
    )


# ==========================================================
# CENTROS TUTORIALES - ELIMINAR
# ==========================================================


@login_required
@permission_required(
    "academico.delete_centrotutorial",
    raise_exception=True,
)
def centro_tutorial_eliminar(
    request,
    centro_id,
):

    centro = get_object_or_404(
        CentroTutorial,
        pk=centro_id,
    )

    if request.method == "POST":

        nombre = centro.nombre

        try:

            centro.delete()

        except ProtectedError:

            messages.error(
                request,
                (
                    f"No es posible eliminar el Centro Tutorial "
                    f'"{nombre}" porque posee información '
                    "académica asociada. Puede marcarlo como "
                    "inactivo en su lugar."
                ),
            )

            return redirect("centros_tutoriales")

        messages.success(
            request,
            (f'Centro Tutorial "{nombre}" ' "eliminado correctamente."),
        )

        return redirect("centros_tutoriales")

    context = {
        "centro": centro,
    }

    return render(
        request,
        "academico/centros_tutoriales/eliminar.html",
        context,
    )


# ==========================================================
# SEDES - LISTADO
# ==========================================================


@login_required
@permission_required(
    "academico.view_sede",
    raise_exception=True,
)
def sedes(request):

    sedes_lista = (
        Sede.objects.select_related(
            "centro_tutorial",
        )
        .all()
        .order_by(
            "centro_tutorial__nombre",
            "nombre",
        )
    )

    context = {
        "sedes": sedes_lista,
    }

    return render(
        request,
        "academico/sedes/lista.html",
        context,
    )


# ==========================================================
# SEDES - CREAR
# ==========================================================


@login_required
@permission_required(
    "academico.add_sede",
    raise_exception=True,
)
def sede_crear(request):

    if request.method == "POST":

        form = SedeForm(request.POST)

        if form.is_valid():

            sede = form.save()

            messages.success(
                request,
                (f'Sede "{sede.nombre}" ' "creada correctamente."),
            )

            return redirect("sedes")

    else:

        form = SedeForm()

    context = {
        "form": form,
        "titulo": "Nueva Sede",
        "texto_boton": "Guardar Sede",
    }

    return render(
        request,
        "academico/sedes/formulario.html",
        context,
    )


# ==========================================================
# SEDES - EDITAR
# ==========================================================


@login_required
@permission_required(
    "academico.change_sede",
    raise_exception=True,
)
def sede_editar(
    request,
    sede_id,
):

    sede = get_object_or_404(
        Sede,
        pk=sede_id,
    )

    if request.method == "POST":

        form = SedeForm(
            request.POST,
            instance=sede,
        )

        if form.is_valid():

            sede = form.save()

            messages.success(
                request,
                (f'Sede "{sede.nombre}" ' "actualizada correctamente."),
            )

            return redirect("sedes")

    else:

        form = SedeForm(
            instance=sede,
        )

    context = {
        "form": form,
        "sede": sede,
        "titulo": "Editar Sede",
        "texto_boton": "Guardar cambios",
    }

    return render(
        request,
        "academico/sedes/formulario.html",
        context,
    )


# ==========================================================
# SEDES - ELIMINAR
# ==========================================================


@login_required
@permission_required(
    "academico.delete_sede",
    raise_exception=True,
)
def sede_eliminar(
    request,
    sede_id,
):

    sede = get_object_or_404(
        Sede.objects.select_related("centro_tutorial"),
        pk=sede_id,
    )

    if request.method == "POST":

        nombre = sede.nombre

        try:

            sede.delete()

        except ProtectedError:

            messages.error(
                request,
                (
                    f"No es posible eliminar la sede "
                    f'"{nombre}" porque posee información '
                    "académica asociada. Puede marcarla "
                    "como inactiva en su lugar."
                ),
            )

            return redirect("sedes")

        messages.success(
            request,
            (f'Sede "{nombre}" ' "eliminada correctamente."),
        )

        return redirect("sedes")

    context = {
        "sede": sede,
    }

    return render(
        request,
        "academico/sedes/eliminar.html",
        context,
    )


# Create your views here.
