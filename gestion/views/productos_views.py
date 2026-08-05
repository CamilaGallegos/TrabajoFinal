from rest_framework import viewsets, status
from rest_framework.response import Response

from ..models import Producto
from ..serializers import ProductoSerializer


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
