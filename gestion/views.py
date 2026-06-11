from django.utils import timezone
from datetime import timedelta
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .models import Producto, PerfilBecado, Asistencia, CuentaAbierta, Venta
from .serializers import (
    ProductoSerializer,
    CuentaAbiertaSerializer,
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaSerializer,
)

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


class CuentaAbiertaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
    serializer_class = CuentaAbiertaSerializer

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


class FichajeEntradaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        dni_recibido = request.data.get('dni')
        
        if not dni_recibido:
            return Response({"error": "El DNI es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # buscamos al becado por su DNI
            becado = PerfilBecado.objects.get(dni=dni_recibido)
            usuario = becado.user
            
            # fichaje automatico
            hoy = timezone.now().date()
            asistencia_existente = Asistencia.objects.filter(
                becado=becado, 
                entrada__date=hoy, 
                salida__isnull=True
            ).exists()
            
            if not asistencia_existente:
                Asistencia.objects.create(becado=becado)
                mensaje_fichaje = "Asistencia registrada con éxito!"
            else:
                mensaje_fichaje = "Ya tenes una asistencia activa de hoy"

            # token JWT para el turno actual
            token = AccessToken.for_user(usuario)
            
            return Response({
                "token": str(token),
                "becado": {
                    "id": becado.id,
                    "nombre": usuario.first_name or usuario.username,
                    "dni": becado.dni
                },
                "msg": mensaje_fichaje
            }, status=status.HTTP_200_OK)
            
        except PerfilBecado.DoesNotExist:
            return Response({"error": "No existe ningún becado/a con ese DNI"}, status=status.HTTP_404_NOT_FOUND)