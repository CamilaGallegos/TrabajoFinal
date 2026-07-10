from django.utils import timezone
from datetime import timedelta
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .models import Producto, PerfilBecado, Asistencia, CuentaAbierta, Venta, AuditoriaVenta
from .serializers import (
    ProductoSerializer,
    CuentaAbiertaSerializer,
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaSerializer,
    AuditoriaVentaSerializer,
)

class ProductoViewSet(viewsets.ModelViewSet):
    # List only active products by default
    queryset = Producto.objects.filter(activo=True)
    serializer_class = ProductoSerializer

    def get_queryset(self):
        # For list operations return only activos; other actions already use the same queryset
        return Producto.objects.filter(activo=True)

    def destroy(self, request, *args, **kwargs):
        # Soft-delete: marcar 'activo' a False en lugar de borrar físicamente
        instance = self.get_object()
        instance.activo = False
        instance.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        password_recibido = request.data.get('password', '')

        if not dni_recibido:
            return Response({"error": "El DNI es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            becado = PerfilBecado.objects.select_related('user').get(dni=dni_recibido)
            usuario = becado.user
            es_admin = bool(usuario.is_staff or usuario.is_superuser)

            if es_admin:
                if not password_recibido:
                    return Response({
                        "requires_password": True,
                        "is_admin": True,
                        "becado": {
                            "id": becado.id,
                            "nombre": usuario.first_name or usuario.username,
                            "dni": becado.dni,
                        },
                        "msg": "Usuario admin requiere contraseña"
                    }, status=status.HTTP_403_FORBIDDEN)

                if not usuario.check_password(password_recibido):
                    return Response({
                        "error": "Contraseña incorrecta",
                        "requires_password": True,
                        "is_admin": True,
                    }, status=status.HTTP_401_UNAUTHORIZED)

            if not es_admin:
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
            else:
                mensaje_fichaje = "Acceso admin autorizado"

            token = AccessToken.for_user(usuario)

            return Response({
                "token": str(token),
                "becado": {
                    "id": becado.id,
                    "nombre": usuario.first_name or usuario.username,
                    "dni": becado.dni,
                },
                "msg": mensaje_fichaje,
                "is_admin": es_admin,
                "requires_password": False,
            }, status=status.HTTP_200_OK)

        except PerfilBecado.DoesNotExist:
            return Response({"error": "No existe ningún becado/a con ese DNI"}, status=status.HTTP_404_NOT_FOUND)
        except PerfilBecado.DoesNotExist:
            return Response({"error": "No existe ningún becado/a con ese DNI"}, status=status.HTTP_404_NOT_FOUND)

class AuditoriaVentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').all().order_by('-fecha_correccion')
    serializer_class = AuditoriaVentaSerializer

    def get_queryset(self):
        venta_id = self.request.query_params.get('venta_id')
        queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').order_by('-fecha_correccion')
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        return queryset
