"""Cuenta docente ficticia explícita: contraseña interactiva, nunca en argumentos."""
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from academico.models import Profesor

class Command(BaseCommand):
    help="Crea y vincula una cuenta docente DEMO sin permisos administrativos. No modifica cuentas existentes."
    def add_arguments(self,parser):
        parser.add_argument("--profesor",required=True,help="Identificación ficticia DOC-DEMO-... existente.")
        parser.add_argument("--usuario",required=True,help="Nombre explícito para la nueva cuenta ficticia.")
    def handle(self,*args,**options):
        codigo=options["profesor"];nombre=options["usuario"]
        if not codigo.startswith("DOC-DEMO-"): raise CommandError("Este comando solo permite profesores explícitamente DEMO.")
        profesor=Profesor.objects.filter(identificacion=codigo,activo=True).select_related("usuario").first()
        if profesor is None: raise CommandError("El profesor demo no existe o está inactivo.")
        if profesor.usuario_id:
            u=profesor.usuario
            if u.get_username()==nombre and u.is_active and not u.is_staff and not u.is_superuser and not u.user_permissions.exists() and not u.groups.exists():
                self.stdout.write("La cuenta docente demo ya está vinculada. No se modificó su contraseña.");return
            raise CommandError("El perfil ya tiene una cuenta vinculada. No se reemplazará.")
        User=get_user_model()
        if User.objects.filter(**{User.USERNAME_FIELD:nombre}).exists(): raise CommandError("El usuario ya existe. No se modificará ni vinculará una cuenta existente.")
        password=getpass("Contraseña para la cuenta DEMO (entrada oculta): ")
        repetir=getpass("Repita la contraseña: ")
        if not password or password!=repetir: raise CommandError("Las contraseñas deben ser no vacías e iguales.")
        u=User(**{User.USERNAME_FIELD:nombre},is_staff=False,is_superuser=False,is_active=True)
        try:
            validate_password(password,u);u.set_password(password);u.full_clean()
        except ValidationError as error: raise CommandError(" ".join(error.messages)) from error
        with transaction.atomic():
            actual=Profesor.objects.select_for_update().get(pk=profesor.pk)
            if actual.usuario_id: raise CommandError("El perfil fue vinculado en otra sesión. No se modificó.")
            if User.objects.filter(**{User.USERNAME_FIELD:nombre}).exists(): raise CommandError("El usuario fue creado en otra sesión. No se modificó.")
            u.save();actual.usuario=u;actual.save(update_fields=["usuario"])
        self.stdout.write(self.style.SUCCESS(f"Cuenta ficticia {nombre} vinculada a {profesor}. Sin permisos administrativos."))
