from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from django import forms
from .models import Prestamo
from herramientas.models import Herramienta


SCANNER_PRESTAMO_HTML = """
<style>
#scanner-wrap { display:flex; gap:8px; margin-bottom:6px; }
#scanner-input {
  padding:6px 10px; border:2px solid #417690; border-radius:4px;
  font-size:14px; width:280px;
}
#scanner-btn {
  padding:6px 14px; background:#417690; color:white;
  border:none; border-radius:4px; cursor:pointer; font-size:14px;
}
#scanner-msg { font-size:13px; margin-top:4px; min-height:20px; }
</style>
<div id="scanner-wrap">
  <input id="scanner-input" type="text"
         placeholder="Escanea o escribe el código del artículo" />
  <button id="scanner-btn" type="button">Agregar</button>
</div>
<div id="scanner-msg"></div>
<script>
(function(){
  function agregar(){
    var codigo = document.getElementById('scanner-input').value.trim();
    var msg    = document.getElementById('scanner-msg');
    if(!codigo) return;
    fetch('/api/herramientas/' + encodeURIComponent(codigo) + '/?format=json', {
      headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
    .then(function(r){
      if(!r.ok) throw new Error('not_found');
      return r.json();
    })
    .then(function(found){
      var select = document.getElementById('id_herramientas');
      var ya = false;
      for(var i = 0; i < select.options.length; i++){
        if(select.options[i].value == found.id){
          select.options[i].selected = true;
          ya = true;
          break;
        }
      }
      if(ya){
        msg.style.color = 'green';
        msg.textContent = '\u2705 Agregado: ' + found.nombre + ' [' + found.codigo + ']';
      } else {
        msg.style.color = 'red';
        msg.textContent = '\u26A0\uFE0F Art\u00EDculo no disponible o ya prestado.';
      }
      document.getElementById('scanner-input').value = '';
      document.getElementById('scanner-input').focus();
    })
    .catch(function(){
      msg.style.color = 'red';
      msg.textContent = '\u274C No se encontr\u00F3 ning\u00FAn art\u00EDculo con ese c\u00F3digo.';
      document.getElementById('scanner-input').value = '';
      document.getElementById('scanner-input').focus();
    });
  }

  document.getElementById('scanner-btn').addEventListener('click', agregar);
  document.getElementById('scanner-input').addEventListener('keydown', function(e){
    if(e.key === 'Enter'){ e.preventDefault(); agregar(); }
  });
})();
</script>
"""


class ScannerWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(SCANNER_PRESTAMO_HTML)


class PrestamoAdminForm(forms.ModelForm):
    escaner = forms.Field(
        required=False,
        label="Agregar herramienta por código de barras",
        widget=ScannerWidget(),
    )

    class Meta:
        model = Prestamo
        fields = "__all__"


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    form = PrestamoAdminForm

    list_display = (
        "id", "lista_herramientas", "lista_solicitantes",
        "lugar_uso", "estado", "fecha_prestamo", "fecha_devolucion_esperada",
        "boton_devolver",
    )
    actions = None
    list_filter = ("estado",)
    search_fields = ("herramientas__nombre", "solicitantes__username", "lugar_uso")
    readonly_fields = ("fecha_prestamo",)
    filter_horizontal = ("solicitantes",)

    fieldsets = (
        ("Agregar herramientas", {
            "fields": ("escaner", "herramientas"),
            "description": "Escanea el código de barras de cada artículo y presiona Enter para agregarlo.",
        }),
        ("Solicitantes", {
            "fields": ("responsable", "solicitantes",),
        }),
        ("Detalles del préstamo", {
            "fields": (
                "descripcion_uso", "lugar_uso",
                "fecha_devolucion_esperada",
            ),
        }),
        ("Estado", {
            "fields": ("fecha_prestamo",),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/devolucion/",
                self.admin_site.admin_view(self.view_devolucion),
                name="prestamos_prestamo_devolucion",
            ),
            path(
                "<int:pk>/devolucion/confirmar/",
                self.admin_site.admin_view(self.view_confirmar_devolucion),
                name="prestamos_prestamo_confirmar_devolucion",
            ),
        ]
        return custom + urls

    def view_devolucion(self, request, pk):
        """Vista de escaneo de herramientas para devolver un préstamo."""
        prestamo = get_object_or_404(Prestamo, pk=pk)

        if prestamo.estado != Prestamo.Estado.ACTIVO:
            messages.warning(request, f"El préstamo #{pk} ya fue cerrado ({prestamo.get_estado_display()}).")
            return redirect("admin:prestamos_prestamo_changelist")

        herramientas = list(prestamo.herramientas.all().values("id", "codigo", "nombre"))
        confirmar_url = reverse("admin:prestamos_prestamo_confirmar_devolucion", args=[pk])
        lista_url = reverse("admin:prestamos_prestamo_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": f"Devolución — Préstamo #{pk}",
            "prestamo": prestamo,
            "herramientas_json": herramientas,
            "confirmar_url": confirmar_url,
            "lista_url": lista_url,
            "solicitantes": ", ".join(
                s.get_full_name() or s.username for s in prestamo.solicitantes.all()
            ),
            "responsable": prestamo.responsable.get_full_name() or prestamo.responsable.username,
        }
        return TemplateResponse(request, "admin/prestamos/devolucion.html", context)

    def view_confirmar_devolucion(self, request, pk):
        """Recibe POST con los códigos escaneados y confirma la devolución."""
        if request.method != "POST":
            return redirect("admin:prestamos_prestamo_devolucion", pk)

        prestamo = get_object_or_404(Prestamo, pk=pk)

        if prestamo.estado != Prestamo.Estado.ACTIVO:
            messages.warning(request, f"El préstamo #{pk} ya fue cerrado.")
            return redirect("admin:prestamos_prestamo_changelist")

        prestamo.estado = Prestamo.Estado.DEVUELTO
        prestamo.fecha_devolucion_real = timezone.now()
        prestamo.save(update_fields=["estado", "fecha_devolucion_real"])
        prestamo.herramientas.all().update(estado=Herramienta.Estado.DISPONIBLE)

        messages.success(request, f"Préstamo #{pk} registrado como devuelto. Todas las herramientas están disponibles.")
        return redirect("admin:prestamos_prestamo_changelist")

    def boton_devolver(self, obj):
        if obj.estado == Prestamo.Estado.ACTIVO:
            url = reverse("admin:prestamos_prestamo_devolucion", args=[obj.pk])
            return format_html(
                '<a href="{}" style="'
                'background:#c0392b;color:white;padding:5px 12px;'
                'border-radius:4px;font-size:12px;text-decoration:none;'
                'font-weight:bold;">'
                'Devolver</a>',
                url,
            )
        return format_html(
            '<span style="color:#888;font-size:12px;">{}</span>',
            obj.get_estado_display(),
        )

    boton_devolver.short_description = "Acción"

    def lista_herramientas(self, obj):
        return ", ".join(h.nombre for h in obj.herramientas.all()) or "—"
    lista_herramientas.short_description = "Herramientas"

    def lista_solicitantes(self, obj):
        return ", ".join(
            s.get_full_name() or s.username for s in obj.solicitantes.all()
        ) or "—"
    lista_solicitantes.short_description = "Solicitantes"
