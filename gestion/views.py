from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q
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
                inicio_hoy = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                Asistencia.objects.filter(
                    becado=becado,
                    salida__isnull=True,
                    entrada__lt=inicio_hoy,
                ).update(salida=timezone.now())

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


class FichajeSalidaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token_str = request.data.get('token', '')
        if not token_str and auth_header.startswith('Bearer '):
            token_str = auth_header.split(' ', 1)[1]

        if not token_str:
            return Response({"msg": "Token no proporcionado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import jwt as pyjwt
            from django.conf import settings as django_settings
            payload = pyjwt.decode(token_str, options={"verify_signature": False})
            user_id = payload.get('user_id')
        except Exception:
            return Response({"msg": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not user_id:
            return Response({"msg": "Token sin user_id."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            usuario = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"msg": "Usuario no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            becado = usuario.perfil
        except PerfilBecado.DoesNotExist:
            return Response({"msg": "Usuario sin perfil de becado, no se registró salida."}, status=status.HTTP_200_OK)

        asistencia_abierta = Asistencia.objects.filter(
            becado=becado,
            salida__isnull=True,
        ).order_by('-entrada').first()

        if not asistencia_abierta:
            return Response({"msg": "No hay asistencia activa para cerrar."}, status=status.HTTP_200_OK)

        asistencia_abierta.salida = timezone.now()
        asistencia_abierta.save(update_fields=['salida'])

        return Response({"msg": "Salida registrada correctamente."}, status=status.HTTP_200_OK)


class ActividadSesionesView(APIView):
    def get(self, request):
        limite = timezone.now() - timedelta(hours=48)

        asistencias = Asistencia.objects.select_related('becado__user').filter(
            Q(entrada__gte=limite) | Q(salida__gte=limite)
        ).order_by('becado_id', '-entrada')

        ultimas_por_becado = {}
        for asistencia in asistencias:
            if asistencia.becado_id not in ultimas_por_becado:
                ultimas_por_becado[asistencia.becado_id] = asistencia

        resultado = []
        for asistencia in ultimas_por_becado.values():
            usuario = asistencia.becado.user
            nombre_completo = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            # "activo" solo si la asistencia no tiene salida Y la entrada es reciente
            esta_activo = asistencia.salida is None and asistencia.entrada >= limite
            ultima_actividad = asistencia.entrada if esta_activo else asistencia.salida

            resultado.append({
                'becado_id': asistencia.becado_id,
                'nombre_usuario': nombre_completo,
                'estado': 'activo' if esta_activo else 'cerrada',
                'ultima_actividad': ultima_actividad.isoformat() if ultima_actividad else None,
                'entrada': asistencia.entrada.isoformat() if asistencia.entrada else None,
                'salida': asistencia.salida.isoformat() if asistencia.salida else None,
            })

        resultado.sort(
            key=lambda item: (
                item['estado'] != 'activo',
                item['ultima_actividad'] or '',
            ),
            reverse=False,
        )

        return Response(resultado)


class AsistenciaResumenView(APIView):
    def _parse_month(self, value):
        if not value:
            now = timezone.localtime(timezone.now())
            return now.year, now.month

        try:
            year_str, month_str = value.split('-')
            year = int(year_str)
            month = int(month_str)
            if 1 <= month <= 12:
                return year, month
        except (ValueError, AttributeError):
            pass

        now = timezone.localtime(timezone.now())
        return now.year, now.month

    def _month_bounds(self, year, month):
        start = timezone.make_aware(datetime(year, month, 1, 0, 0, 0), timezone.get_current_timezone())
        if month == 12:
            next_start = timezone.make_aware(datetime(year + 1, 1, 1, 0, 0, 0), timezone.get_current_timezone())
        else:
            next_start = timezone.make_aware(datetime(year, month + 1, 1, 0, 0, 0), timezone.get_current_timezone())
        return start, next_start

    def _format_horas(self, total_minutes):
        horas = total_minutes / 60
        return round(horas, 2)

    def _asistencia_duracion_minutos(self, asistencia, fin_periodo):
        ahora = timezone.now()
        salida = asistencia.salida or min(fin_periodo, ahora)
        if salida < asistencia.entrada:
            return 0
        delta = salida - asistencia.entrada
        return max(0, int(delta.total_seconds() // 60))

    def _build_month_payload(self, year, month, label=None):
        inicio, fin = self._month_bounds(year, month)
        asistencias = Asistencia.objects.select_related('becado__user').filter(
            entrada__gte=inicio,
            entrada__lt=fin,
        ).order_by('becado__user__first_name', 'becado__user__last_name', 'entrada')

        grupos = {}
        for asistencia in asistencias:
            usuario = asistencia.becado.user
            nombre_completo = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            grupo = grupos.setdefault(asistencia.becado_id, {
                'becado_id': asistencia.becado_id,
                'nombre_usuario': nombre_completo,
                'asistencias': [],
                '_minutos_total': 0,
            })

            duracion_minutos = self._asistencia_duracion_minutos(asistencia, fin)
            grupo['_minutos_total'] += duracion_minutos
            grupo['asistencias'].append({
                'id': asistencia.id,
                'entrada': asistencia.entrada.isoformat(),
                'salida': asistencia.salida.isoformat() if asistencia.salida else None,
                'estado': 'activo' if asistencia.salida is None else 'cerrada',
                'horas': self._format_horas(duracion_minutos),
            })

        usuarios = []
        total_minutos = 0
        for grupo in grupos.values():
            minutos_total_grupo = grupo.pop('_minutos_total')
            total_minutos += minutos_total_grupo
            grupo['total_horas'] = self._format_horas(minutos_total_grupo)
            usuarios.append(grupo)

        usuarios.sort(key=lambda item: item['nombre_usuario'].lower())

        return {
            'periodo': f'{year:04d}-{month:02d}',
            'label': label or f'{month:02d}/{year:04d}',
            'cantidad_asistencias': asistencias.count(),
            'total_horas': self._format_horas(total_minutos),
            'usuarios': usuarios,
        }

    def get(self, request):
        mes = request.query_params.get('mes')
        year, month = self._parse_month(mes)
        current_now = timezone.localtime(timezone.now())
        current_year, current_month = current_now.year, current_now.month

        previous_year = current_year
        previous_month = current_month - 1
        if previous_month == 0:
            previous_month = 12
            previous_year -= 1

        response = {
            'actual': self._build_month_payload(current_year, current_month, 'Mes actual'),
            'anterior': self._build_month_payload(previous_year, previous_month, 'Mes anterior'),
            'seleccionado': self._build_month_payload(year, month, f'{month:02d}/{year:04d}'),
        }

        return Response(response)

class AuditoriaVentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').all().order_by('-fecha_correccion')
    serializer_class = AuditoriaVentaSerializer

    def get_queryset(self):
        venta_id = self.request.query_params.get('venta_id')
        queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').order_by('-fecha_correccion')
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        return queryset
