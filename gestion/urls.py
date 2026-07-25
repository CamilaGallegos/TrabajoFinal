from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductoViewSet, FichajeEntradaView, FichajeSalidaView, CuentaAbiertaViewSet, VentaViewSet, AuditoriaVentaViewSet, ActividadSesionesView, AsistenciaResumenView, ReporteDashboardResumenView, CuentaAbiertaResumenView, PagoCuentaAbiertaViewSet, CuentaAbiertaEvolucionMensualView

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)
router.register(r'cuentas-abiertas', CuentaAbiertaViewSet)
router.register(r'cuentas-abiertas-pagos', PagoCuentaAbiertaViewSet, basename='cuentas-abiertas-pagos')
router.register(r'ventas', VentaViewSet, basename='ventas')
router.register(r'auditorias', AuditoriaVentaViewSet, basename='auditorias')

urlpatterns = [
    path('', include(router.urls)),
    path('fichaje/entrada/', FichajeEntradaView.as_view(), name='fichaje-entrada'),
    path('fichaje/salida/', FichajeSalidaView.as_view(), name='fichaje-salida'),
    path('fichaje/actividad/', ActividadSesionesView.as_view(), name='fichaje-actividad'),
    path('asistencias/resumen/', AsistenciaResumenView.as_view(), name='asistencias-resumen'),
    path('reportes/dashboard-resumen/', ReporteDashboardResumenView.as_view(), name='reportes-dashboard-resumen'),
    path('reportes/cuentas-abiertas-evolucion/', CuentaAbiertaEvolucionMensualView.as_view(), name='reportes-cuentas-abiertas-evolucion'),
    path('cuentas-abiertas-resumen/', CuentaAbiertaResumenView.as_view(), name='cuentas-abiertas-resumen'),
]