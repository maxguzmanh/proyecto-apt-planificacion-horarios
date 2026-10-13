"""Portal de consulta: identidad del servidor y consultas aisladas por usuario."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from academico.models import PeriodoAcademico
from usuarios.roles import profesor_de_usuario, puede_dashboard, puede_mantenedores, destino_usuario
from .models import Horario, OfertaAcademica
from .presentacion import horarios_con_contexto, evento_con_contexto
from .calendario import SEMANA_REFERENCIA


def periodos_del_profesor(profesor):
    ofertas=OfertaAcademica.objects.filter(profesor=profesor, periodo_id=OuterRef("pk"), activo=True)
    horarios=Horario.objects.filter(oferta__profesor=profesor, oferta__periodo_id=OuterRef("pk"), activo=True, oferta__activo=True)
    return PeriodoAcademico.objects.all().annotate(tiene_ofertas=Exists(ofertas), tiene_horarios=Exists(horarios)).filter(Q(tiene_ofertas=True)|Q(tiene_horarios=True)).order_by("-tiene_horarios", "-fecha_inicio", "-pk")


def horarios_del_profesor(profesor):
    return horarios_con_contexto(Horario.objects.filter(activo=True, oferta__activo=True,
        oferta__profesor=profesor)).order_by("dia", "hora_inicio", "pk")


def periodo_solicitado(request, profesor):
    valor=request.GET.get("periodo_id", "")
    if not valor.isdigit() or int(valor)<=0: raise ValidationError("Seleccione un periodo académico válido.")
    return get_object_or_404(periodos_del_profesor(profesor), pk=int(valor))

@login_required
@require_GET
def profesor_inicio(request):
    return redirect("profesor_horario")

@login_required
@require_GET
def profesor_horario(request):
    if puede_dashboard(request.user) or puede_mantenedores(request.user): return redirect(destino_usuario(request.user))
    profesor=profesor_de_usuario(request.user)
    if profesor is None:
        from usuarios.views import acceso_no_configurado
        return acceso_no_configurado(request)
    periodos=list(periodos_del_profesor(profesor))
    valor=request.GET.get("periodo_id")
    if valor:
        periodo=get_object_or_404(periodos_del_profesor(profesor), pk=valor) if valor.isdigit() else None
        if periodo is None:
            from django.http import Http404
            raise Http404("Periodo no disponible.")
    else: periodo=periodos[0] if periodos else None
    return render(request,"horarios/profesor/mi_horario.html",{"portal_profesor":True,"perfil_docente":profesor,
        "periodos":periodos,"periodo":periodo,"semana_referencia":SEMANA_REFERENCIA.isoformat()})

@login_required
@require_GET
def profesor_eventos(request):
    profesor=profesor_de_usuario(request.user)
    if profesor is None: return JsonResponse({"errors":{"__all__":["Su usuario no tiene un perfil docente asociado."]}},status=403)
    try: periodo=periodo_solicitado(request,profesor)
    except ValidationError as error: return JsonResponse({"errors":{"periodo_id":error.messages}},status=400)
    except Http404: return JsonResponse({"errors":{"periodo_id":["Periodo no disponible para su perfil."]}},status=404)
    return JsonResponse([evento_con_contexto(h) for h in horarios_del_profesor(profesor).filter(oferta__periodo=periodo)],safe=False)

@login_required
@require_GET
def profesor_detalle(request, horario_id):
    profesor=profesor_de_usuario(request.user)
    if profesor is None: return JsonResponse({"errors":{"__all__":["Su usuario no tiene un perfil docente asociado."]}},status=403)
    try: horario=get_object_or_404(horarios_del_profesor(profesor),pk=horario_id)
    except Http404: return JsonResponse({"errors":{"__all__":["Horario no disponible para su perfil."]}},status=404)
    return JsonResponse({"event":evento_con_contexto(horario)})
