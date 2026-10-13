from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from .roles import destino_usuario

class UniPlanLoginView(LoginView):
    template_name = "usuarios/login.html"
    def get_success_url(self):
        destino = destino_usuario(self.request.user)
        if destino in ("inicio", "mantenedores"):
            return self.get_redirect_url() or reverse(destino)
        return reverse(destino)

@login_required
def acceso_no_configurado(request):
    return render(request, "usuarios/acceso_no_configurado.html", {"sidebar_solo_lectura": True}, status=403)
