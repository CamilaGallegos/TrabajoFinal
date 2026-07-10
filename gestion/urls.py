from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductoViewSet, FichajeEntradaView, CuentaAbiertaViewSet, VentaViewSet, AuditoriaVentaViewSet

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)
router.register(r'cuentas-abiertas', CuentaAbiertaViewSet)
router.register(r'ventas', VentaViewSet, basename='ventas')
router.register(r'auditorias', AuditoriaVentaViewSet, basename='auditorias')

urlpatterns = [
    path('', include(router.urls)),
    path('fichaje/entrada/', FichajeEntradaView.as_view(), name='fichaje-entrada'),
]