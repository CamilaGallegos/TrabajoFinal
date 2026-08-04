from rest_framework import viewsets, status
from rest_framework.response import Response

from ..models import Producto, CuentaAbierta
from ..serializers import ProductoSerializer, CuentaAbiertaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.filter(activo=True)
    serializer_class = ProductoSerializer

    def get_queryset(self):
        return Producto.objects.filter(activo=True)

    def destroy(self, request, *args, **kwargs):
        # Soft-delete: marcar 'activo' a False en lugar de borrar fisicamente
        instance = self.get_object()
        instance.activo = False
        instance.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CuentaAbiertaViewSet(viewsets.ModelViewSet):
    queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
    serializer_class = CuentaAbiertaSerializer

    def get_queryset(self):
        queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
        if str(self.request.query_params.get('incluye_inactivas', '')).lower() in {'1', 'true', 'si', 'yes'}:
            return queryset
        return queryset.filter(activo=True)
