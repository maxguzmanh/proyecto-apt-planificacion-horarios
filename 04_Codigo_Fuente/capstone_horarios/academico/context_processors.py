"""Navegación por permisos usando el catálogo CRUD existente."""

def menu_mantenedores(request):
    from .views import MANTENEDORES
    orden=["centros","sedes","facultades","programas","periodos","semestres","modalidades","areas","asignaturas","planes","profesores","disponibilidades","cargas_docentes","aulas","grupos"]
    actual=getattr(getattr(request,"resolver_match",None),"url_name",None)
    opciones=[]
    if request.user.is_authenticated:
        for clave in orden:
            c=MANTENEDORES[clave];meta=c["modelo"]._meta
            if request.user.has_perm(f"{meta.app_label}.view_{meta.model_name}"):
                nombre={"disponibilidades":"Disponibilidad Docente","cargas_docentes":"Carga Docente"}.get(clave,c["titulo"])
                opciones.append({"nombre":nombre,"ruta":c["listado_url"],"activa":actual in [c[k] for k in ("listado_url","crear_url","editar_url","eliminar_url")]})
    return {"menu_mantenedores":opciones,"mantenedores_abierto":actual=="mantenedores" or any(o["activa"] for o in opciones)}
