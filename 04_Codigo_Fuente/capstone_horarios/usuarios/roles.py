"""Prioridad de capacidades existentes; no crea roles ni permisos nuevos."""
from academico.models import Profesor


def puede_dashboard(usuario):
    return usuario.is_authenticated and usuario.is_active and (usuario.is_superuser or (
        usuario.has_perm("horarios.view_horario") and any(usuario.has_perm(f"horarios.{accion}_horario") for accion in ("add", "change", "delete"))))


def puede_mantenedores(usuario):
    from academico.views import MANTENEDORES
    return usuario.is_authenticated and any(usuario.has_perm(f"{c['modelo']._meta.app_label}.view_{c['modelo']._meta.model_name}") for c in MANTENEDORES.values())


def profesor_de_usuario(usuario):
    if not usuario.is_authenticated: return None
    return Profesor.objects.filter(usuario=usuario, activo=True).first()


def destino_usuario(usuario):
    if puede_dashboard(usuario): return "inicio"
    # Los usuarios con acceso solo a catálogos conservan ese acceso administrativo.
    if puede_mantenedores(usuario): return "mantenedores"
    if profesor_de_usuario(usuario): return "profesor_horario"
    return "acceso_no_configurado"
