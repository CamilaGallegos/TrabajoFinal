from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.becados_views import PerfilBecadoAdminViewSet
from .views.cuentas_abiertas_views import CuentaAbiertaViewSet
from .views.productos_views import ProductoViewSet
from .views.ventas_views import VentaViewSet, AuditoriaVentaViewSet, PagoCuentaAbiertaViewSet
from .views.asistencia_views import FichajeEntradaView, FichajeSalidaView, ActividadSesionesView, AsistenciaResumenView
from .views.reportes_views import ReporteDashboardResumenView, CuentaAbiertaResumenView, CuentaAbiertaEvolucionMensualView

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)
router.register(r'cuentas-abiertas', CuentaAbiertaViewSet)
router.register(r'cuentas-abiertas-pagos', PagoCuentaAbiertaViewSet, basename='cuentas-abiertas-pagos')
router.register(r'becados-admin', PerfilBecadoAdminViewSet, basename='becados-admin')
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