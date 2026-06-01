from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, FichajeEntradaView

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('fichaje/entrada/', FichajeEntradaView.as_view(), name='fichaje-entrada'),
]