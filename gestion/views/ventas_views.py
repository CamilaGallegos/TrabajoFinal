from datetime import timedelta

from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from ..models import Venta, PagoCuentaAbierta, AuditoriaVenta
from ..serializers import (
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaSerializer,
    PagoCuentaAbiertaSerializer,
    PagoCuentaAbiertaCreateSerializer,
    AuditoriaVentaSerializer,
)


class PagoCuentaAbiertaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = (
        PagoCuentaAbierta.objects
        .select_related('cuenta_abierta', 'usuario_registro')
        .prefetch_related('imputaciones__venta')
        .all()
        .order_by('-fecha_pago', '-id')
    )

    def get_serializer_class(self):
        if self.action == 'create':
            return PagoCuentaAbiertaCreateSerializer
        return PagoCuentaAbiertaSerializer

    def get_queryset(self):
        queryset = self.queryset
        cuenta_abierta_id = self.request.query_params.get('cuenta_abierta_id')
        if cuenta_abierta_id:
            queryset = queryset.filter(cuenta_abierta_id=cuenta_abierta_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        pago = serializer.save()
        response_serializer = PagoCuentaAbiertaSerializer(pago)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


# recibe la venta y la guarda, tambien lista el historial
class VentaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Venta.objects.select_related('becado', 'cuenta_abierta').prefetch_related('detalles__producto').all().order_by('-fecha')

    def get_serializer_class(self):
        if self.action == 'create':
            return VentaCreateSerializer
        if self.action in ('update', 'partial_update'):
            return VentaUpdateSerializer
        return VentaSerializer

    def _validar_ventana_edicion(self, venta):
        limite_edicion = venta.fecha + timedelta(hours=24)
        if timezone.now() > limite_edicion:
            raise PermissionDenied('La venta solo puede editarse dentro de las 24 horas desde su creación.')

    def create(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        venta = serializer.save()
        response_serializer = VentaSerializer(venta)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        venta = self.get_object()
        self._validar_ventana_edicion(venta)

        serializer = self.get_serializer(venta, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        venta_actualizada = serializer.save()
        response_serializer = VentaSerializer(venta_actualizada)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class AuditoriaVentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').all().order_by('-fecha_correccion')
    serializer_class = AuditoriaVentaSerializer

    def get_queryset(self):
        venta_id = self.request.query_params.get('venta_id')
        queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').order_by('-fecha_correccion')
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        return queryset
