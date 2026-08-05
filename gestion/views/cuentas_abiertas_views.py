from rest_framework import viewsets

from ..models import CuentaAbierta
from ..serializers import CuentaAbiertaSerializer


class CuentaAbiertaViewSet(viewsets.ModelViewSet):
    queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
    serializer_class = CuentaAbiertaSerializer

    def get_queryset(self):
        queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
        if getattr(self, 'action', None) != 'list':
            return queryset
        if str(self.request.query_params.get('incluye_inactivas', '')).lower() in {'1', 'true', 'si', 'yes'}:
            return queryset
        return queryset.filter(activo=True)
