from django.contrib import admin
from .models import Categoria, Producto, PerfilBecado, Asistencia, CuentaAbierta, Venta, DetalleVenta, AuditoriaVenta

# turbalarInline para q detalles se vea dentro de la misma view
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1 

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleVentaInline]
    list_display = ['id', 'fecha', 'becado', 'cuenta_abierta', 'total']

admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(PerfilBecado)
admin.site.register(Asistencia)
admin.site.register(CuentaAbierta)
admin.site.register(AuditoriaVenta)