from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, FichajeEntradaView, CuentaAbiertaViewSet

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)
router.register(r'cuentas-abiertas', CuentaAbiertaViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('fichaje/entrada/', FichajeEntradaView.as_view(), name='fichaje-entrada'),
]