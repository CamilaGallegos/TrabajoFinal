from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay, TruncMonth
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings as django_settings

from .models import (
    Producto,
    PerfilBecado,
    Asistencia,
    CuentaAbierta,
    Venta,
    DetalleVenta,
    AuditoriaVenta,
    PagoCuentaAbierta,
)
from .serializers import (
    ProductoSerializer,
    CuentaAbiertaSerializer,
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaSerializer,
    AuditoriaVentaSerializer,
    PagoCuentaAbiertaSerializer,
    PagoCuentaAbiertaCreateSerializer,
    PerfilBecadoAdminSerializer,
    PerfilBecadoCreateSerializer,
)


class PerfilBecadoAdminViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = PerfilBecado.objects.select_related('user').all().order_by('user__first_name', 'user__last_name', 'dni')

    def get_serializer_class(self):
        if self.action == 'create':
            return PerfilBecadoCreateSerializer
        return PerfilBecadoAdminSerializer

    def _validar_admin(self, request):
        if not (request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
            raise PermissionDenied('Solo administradores pueden gestionar becados.')

    def list(self, request, *args, **kwargs):
        self._validar_admin(request)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._validar_admin(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()
        response_serializer = PerfilBecadoAdminSerializer(perfil)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        self._validar_admin(request)
        perfil = self.get_object()
        if 'activo' not in request.data:
            return Response({'detail': 'Debe enviar el campo activo.'}, status=status.HTTP_400_BAD_REQUEST)

        valor_activo = request.data.get('activo')
        if isinstance(valor_activo, bool):
            activo = valor_activo
        else:
            activo = str(valor_activo).strip().lower() in {'1', 'true', 'si', 'yes'}

        if perfil.user_id == request.user.id and not activo:
            return Response(
                {'detail': 'No podes inhabilitar tu propio usuario mientras esta en uso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil.user.is_active = activo
        perfil.user.save(update_fields=['is_active'])
        response_serializer = PerfilBecadoAdminSerializer(perfil)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


def _get_access_token_lifetime():
    jwt_config = getattr(django_settings, 'SIMPLE_JWT', {}) or {}
    configured = jwt_config.get('ACCESS_TOKEN_LIFETIME')
    if isinstance(configured, timedelta) and configured.total_seconds() > 0:
        return configured
    return timedelta(hours=7)


def _expiracion_desde_asistencia(asistencia):
    return asistencia.entrada + _get_access_token_lifetime()

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


class CuentaAbiertaViewSet(viewsets.ModelViewSet):
    queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
    serializer_class = CuentaAbiertaSerializer

    def get_queryset(self):
        queryset = CuentaAbierta.objects.all().order_by('nombre_departamento')
        if str(self.request.query_params.get('incluye_inactivas', '')).lower() in {'1', 'true', 'si', 'yes'}:
            return queryset
        return queryset.filter(activo=True)


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

            if not usuario.is_active:
                return Response({"error": "Usuario inhabilitado"}, status=status.HTTP_403_FORBIDDEN)

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
                sesiones_abiertas_anteriores = Asistencia.objects.filter(
                    becado=becado,
                    salida__isnull=True,
                    entrada__lt=inicio_hoy,
                )
                for sesion_abierta in sesiones_abiertas_anteriores:
                    salida_forzada = min(timezone.now(), _expiracion_desde_asistencia(sesion_abierta))
                    try:
                        sesion_abierta.salida = salida_forzada
                        sesion_abierta.salida_motivo = Asistencia.MOTIVO_SIN_CIERRE
                        sesion_abierta.save(update_fields=['salida', 'salida_motivo'])
                    except (ProgrammingError, OperationalError):
                        sesion_abierta.salida = salida_forzada
                        sesion_abierta.save(update_fields=['salida'])

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
            payload = pyjwt.decode(token_str, options={"verify_signature": False})
            user_id = payload.get('user_id')
            token_exp = payload.get('exp')
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

        motivo_salida = str(request.data.get('motivo') or Asistencia.MOTIVO_MANUAL).strip().lower()
        motivos_validos = {key for key, _ in Asistencia.MOTIVO_SALIDA_CHOICES}
        if motivo_salida not in motivos_validos:
            motivo_salida = Asistencia.MOTIVO_MANUAL

        ahora = timezone.now()
        salida_calculada = ahora
        if motivo_salida == Asistencia.MOTIVO_EXPIRADA:
            expiracion_por_entrada = _expiracion_desde_asistencia(asistencia_abierta)
            expiracion_por_token = None
            if token_exp:
                try:
                    expiracion_por_token = datetime.fromtimestamp(int(token_exp), tz=ZoneInfo('UTC'))
                except (TypeError, ValueError, OSError):
                    expiracion_por_token = None

            if expiracion_por_token is not None:
                salida_calculada = min(ahora, expiracion_por_entrada, expiracion_por_token)
            else:
                salida_calculada = min(ahora, expiracion_por_entrada)

            if salida_calculada < asistencia_abierta.entrada:
                salida_calculada = asistencia_abierta.entrada

        asistencia_abierta.salida = salida_calculada
        try:
            asistencia_abierta.salida_motivo = motivo_salida
            asistencia_abierta.save(update_fields=['salida', 'salida_motivo'])
        except (ProgrammingError, OperationalError):
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

        # no debe superar ACCESS_TOKEN_LIFETIME.
        if asistencia.salida_motivo == Asistencia.MOTIVO_EXPIRADA:
            salida = min(salida, _expiracion_desde_asistencia(asistencia))

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
        try:
            for asistencia in asistencias:
                usuario = asistencia.becado.user
                nombre_completo = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
                grupo = grupos.setdefault(asistencia.becado_id, {
                    'becado_id': asistencia.becado_id,
                    'nombre_usuario': nombre_completo,
                    'activo': bool(usuario.is_active),
                    'asistencias': [],
                    '_minutos_total': 0,
                })

                duracion_minutos = self._asistencia_duracion_minutos(asistencia, fin)
                grupo['_minutos_total'] += duracion_minutos
                salida_efectiva = asistencia.salida
                if salida_efectiva and asistencia.salida_motivo == Asistencia.MOTIVO_EXPIRADA:
                    salida_efectiva = min(salida_efectiva, _expiracion_desde_asistencia(asistencia))

                grupo['asistencias'].append({
                    'id': asistencia.id,
                    'entrada': asistencia.entrada.isoformat(),
                    'salida': salida_efectiva.isoformat() if salida_efectiva else None,
                    'salida_motivo': asistencia.salida_motivo,
                    'estado': 'activo' if asistencia.salida is None else 'cerrada',
                    'horas': self._format_horas(duracion_minutos),
                })
        except (ProgrammingError, OperationalError):
            asistencias_legacy = (
                Asistencia.objects
                .filter(entrada__gte=inicio, entrada__lt=fin)
                .values(
                    'id',
                    'becado_id',
                    'entrada',
                    'salida',
                    'becado__user__first_name',
                    'becado__user__last_name',
                    'becado__user__username',
                    'becado__user__is_active',
                )
                .order_by('becado__user__first_name', 'becado__user__last_name', 'entrada')
            )

            for asistencia in asistencias_legacy:
                nombre_completo = (
                    f"{asistencia['becado__user__first_name']} {asistencia['becado__user__last_name']}"
                ).strip() or asistencia['becado__user__username']
                grupo = grupos.setdefault(asistencia['becado_id'], {
                    'becado_id': asistencia['becado_id'],
                    'nombre_usuario': nombre_completo,
                    'activo': bool(asistencia['becado__user__is_active']),
                    'asistencias': [],
                    '_minutos_total': 0,
                })

                salida = asistencia['salida'] or min(fin, timezone.now())
                if salida < asistencia['entrada']:
                    duracion_minutos = 0
                else:
                    delta = salida - asistencia['entrada']
                    duracion_minutos = max(0, int(delta.total_seconds() // 60))

                grupo['_minutos_total'] += duracion_minutos
                grupo['asistencias'].append({
                    'id': asistencia['id'],
                    'entrada': asistencia['entrada'].isoformat(),
                    'salida': asistencia['salida'].isoformat() if asistencia['salida'] else None,
                    'salida_motivo': Asistencia.MOTIVO_MANUAL,
                    'estado': 'activo' if asistencia['salida'] is None else 'cerrada',
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


class ReporteDashboardResumenView(APIView):
    REPORT_TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires')
    WEEKDAY_ORDER = [1, 2, 3, 4, 5, 6, 7]
    WEEKDAY_LABELS = {
        1: 'Lunes',
        2: 'Martes',
        3: 'Miércoles',
        4: 'Jueves',
        5: 'Viernes',
        6: 'Sábado',
        7: 'Domingo',
    }
    TIPO_PAGO_LABELS = {
        Venta.TIPO_PAGO_EFECTIVO: 'Efectivo',
        Venta.TIPO_PAGO_TRANSFERENCIA: 'Transferencia',
        Venta.TIPO_PAGO_COMBINADO: 'Combinado',
        Venta.TIPO_PAGO_CUENTA_ABIERTA: 'Cuenta Abierta',
    }

    def _bool_query_param(self, value, default=False):
        if value is None:
            return default
        return str(value).strip().lower() in {'1', 'true', 't', 'si', 'yes', 'y'}

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _default_date_range(self):
        now = timezone.localtime(timezone.now(), self.REPORT_TIMEZONE)
        start = now.date().replace(day=1)
        return start, now.date()

    def _date_range_from_query(self, request):
        fecha_desde = self._parse_date(request.query_params.get('fecha_desde'))
        fecha_hasta = self._parse_date(request.query_params.get('fecha_hasta'))

        if not fecha_desde and not fecha_hasta:
            fecha_desde, fecha_hasta = self._default_date_range()
        elif fecha_desde and not fecha_hasta:
            fecha_hasta = fecha_desde
        elif fecha_hasta and not fecha_desde:
            fecha_desde = fecha_hasta

        if fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

        inicio = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), self.REPORT_TIMEZONE)
        fin_exclusivo = timezone.make_aware(datetime.combine(fecha_hasta + timedelta(days=1), datetime.min.time()), self.REPORT_TIMEZONE)
        return fecha_desde, fecha_hasta, inicio, fin_exclusivo

    def _movimiento_por_dia(self, ventas_qs, incluir_finde):
        ventas_por_dia = {
            item['weekday']: item['ventas']
            for item in ventas_qs.annotate(weekday=ExtractIsoWeekDay('fecha', tzinfo=self.REPORT_TIMEZONE)).values('weekday').annotate(ventas=Count('id'))
        }

        dias_base = [1, 2, 3, 4, 5] if not incluir_finde else self.WEEKDAY_ORDER
        return [
            {
                'dia': self.WEEKDAY_LABELS[dia_num],
                'ventas': int(ventas_por_dia.get(dia_num, 0)),
            }
            for dia_num in dias_base
        ]

    def _horas_pico(self, ventas_qs):
        ventas_por_hora = {
            item['hora']: item['ventas']
            for item in ventas_qs.annotate(hora=ExtractHour('fecha', tzinfo=self.REPORT_TIMEZONE)).values('hora').annotate(ventas=Count('id'))
        }

        inicio_hora, fin_hora = 9, 20
        return [
            {
                'hora': f'{hora:02d}:00',
                'ventas': int(ventas_por_hora.get(hora, 0)),
            }
            for hora in range(inicio_hora, fin_hora + 1)
        ]

    def _flujo_dia_hora(self, ventas_qs, incluir_finde):
        agregado = (
            ventas_qs
            .annotate(
                weekday=ExtractIsoWeekDay('fecha', tzinfo=self.REPORT_TIMEZONE),
                hora=ExtractHour('fecha', tzinfo=self.REPORT_TIMEZONE),
            )
            .values('weekday', 'hora')
            .annotate(ventas=Count('id'))
            .order_by('weekday', 'hora')
        )

        dias_permitidos = set([1, 2, 3, 4, 5] if not incluir_finde else self.WEEKDAY_ORDER)
        inicio_hora, fin_hora = 9, 20

        resultado = []
        for item in agregado:
            dia_num = item['weekday']
            hora_num = item['hora']
            if dia_num not in dias_permitidos:
                continue
            if hora_num is None or hora_num < inicio_hora or hora_num > fin_hora:
                continue

            resultado.append({
                'dia': self.WEEKDAY_LABELS[dia_num],
                'hora': f'{hora_num:02d}:00',
                'ventas': int(item['ventas']),
            })

        return resultado

    def _preferencia_pago(self, ventas_qs):
        totales = list(ventas_qs.values('tipo_pago').annotate(transacciones=Count('id')).order_by())
        total_transacciones = sum(item['transacciones'] for item in totales)

        if total_transacciones == 0:
            return []

        resultado = []
        for item in totales:
            transacciones = int(item['transacciones'])
            porcentaje = round((transacciones / total_transacciones) * 100, 2)
            tipo = item['tipo_pago']
            resultado.append({
                'metodo': tipo,
                'label': self.TIPO_PAGO_LABELS.get(tipo, tipo.replace('_', ' ').title()),
                'transacciones': transacciones,
                'porcentaje': porcentaje,
            })
        return resultado

    def _totales_efectivo_transferencia(self, ventas_qs):
        totales = (
            ventas_qs
            .values('tipo_pago')
            .annotate(monto_total=Sum('total'))
            .filter(tipo_pago__in=[Venta.TIPO_PAGO_EFECTIVO, Venta.TIPO_PAGO_TRANSFERENCIA])
        )

        resultado = []
        for item in totales:
            tipo = item['tipo_pago']
            monto = float(item['monto_total'] or 0)
            resultado.append({
                'metodo': tipo,
                'label': self.TIPO_PAGO_LABELS.get(tipo, tipo.replace('_', ' ').title()),
                'monto': round(monto, 2),
            })
        
        return resultado

    def _top_productos(self, inicio, fin_exclusivo):
        top = (
            DetalleVenta.objects
            .filter(venta__fecha__gte=inicio, venta__fecha__lt=fin_exclusivo)
            .values('producto__nombre')
            .annotate(unidades=Sum('cantidad'))
            .order_by('-unidades', 'producto__nombre')[:10]
        )

        return [
            {
                'producto': item['producto__nombre'],
                'unidades': int(item['unidades'] or 0),
            }
            for item in top
        ]

    def get(self, request):
        incluir_finde = self._bool_query_param(request.query_params.get('incluir_finde'), default=False)
        fecha_desde, fecha_hasta, inicio, fin_exclusivo = self._date_range_from_query(request)

        ventas_qs = Venta.objects.filter(fecha__gte=inicio, fecha__lt=fin_exclusivo)

        response = {
            'filtros': {
                'fecha_desde': fecha_desde.isoformat(),
                'fecha_hasta': fecha_hasta.isoformat(),
                'incluir_finde': incluir_finde,
            },
            'movimiento_dia_semana': self._movimiento_por_dia(ventas_qs, incluir_finde),
            'horas_pico': self._horas_pico(ventas_qs),
            'flujo_dia_hora': self._flujo_dia_hora(ventas_qs, incluir_finde),
            'preferencia_pago': self._preferencia_pago(ventas_qs),
            'totales_efectivo_transferencia': self._totales_efectivo_transferencia(ventas_qs),
            'top_productos': self._top_productos(inicio, fin_exclusivo),
        }
        return Response(response)


class CuentaAbiertaEvolucionMensualView(APIView):
    REPORT_TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires')

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _default_date_range(self):
        now = timezone.localtime(timezone.now(), self.REPORT_TIMEZONE).date()
        end = now
        start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(4):
            start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
        return start, end

    def _month_sequence(self, start_date, end_date):
        months = []
        cursor = start_date.replace(day=1)
        limit = end_date.replace(day=1)

        while cursor <= limit:
            months.append(cursor)
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1, day=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1, day=1)

        return months

    def get(self, request):
        fecha_desde = self._parse_date(request.query_params.get('fecha_desde'))
        fecha_hasta = self._parse_date(request.query_params.get('fecha_hasta'))

        if not fecha_desde and not fecha_hasta:
            fecha_desde, fecha_hasta = self._default_date_range()
        elif fecha_desde and not fecha_hasta:
            fecha_hasta = fecha_desde
        elif fecha_hasta and not fecha_desde:
            fecha_desde = fecha_hasta

        if fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

        inicio = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), self.REPORT_TIMEZONE)
        fin_exclusivo = timezone.make_aware(
            datetime.combine(fecha_hasta + timedelta(days=1), datetime.min.time()),
            self.REPORT_TIMEZONE,
        )

        deuda_por_mes_qs = (
            Venta.objects
            .filter(
                tipo_pago=Venta.TIPO_PAGO_CUENTA_ABIERTA,
                fecha__gte=inicio,
                fecha__lt=fin_exclusivo,
            )
            .annotate(mes=TruncMonth('fecha', tzinfo=self.REPORT_TIMEZONE))
            .values('mes')
            .annotate(total=Sum('total'))
            .order_by('mes')
        )

        pagos_por_mes_qs = (
            PagoCuentaAbierta.objects
            .filter(fecha_pago__gte=inicio, fecha_pago__lt=fin_exclusivo)
            .annotate(mes=TruncMonth('fecha_pago', tzinfo=self.REPORT_TIMEZONE))
            .values('mes')
            .annotate(total=Sum('monto'))
            .order_by('mes')
        )

        deuda_por_mes = {
            item['mes'].date().isoformat(): round(float(item['total'] or 0), 2)
            for item in deuda_por_mes_qs
            if item['mes']
        }
        pagos_por_mes = {
            item['mes'].date().isoformat(): round(float(item['total'] or 0), 2)
            for item in pagos_por_mes_qs
            if item['mes']
        }

        meses = self._month_sequence(fecha_desde, fecha_hasta)
        evolucion = []
        for mes in meses:
            key = mes.replace(day=1).isoformat()
            deuda = deuda_por_mes.get(key, 0)
            pagos = pagos_por_mes.get(key, 0)
            evolucion.append({
                'periodo': mes.strftime('%Y-%m'),
                'deuda_generada': deuda,
                'pagos_cobrados': pagos,
                'variacion_neta': round(deuda - pagos, 2),
            })

        return Response({
            'filtros': {
                'fecha_desde': fecha_desde.isoformat(),
                'fecha_hasta': fecha_hasta.isoformat(),
            },
            'evolucion': evolucion,
        })


class CuentaAbiertaResumenView(APIView):
    REPORT_TIMEZONE = ZoneInfo('America/Argentina/Buenos_Aires')

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _format_money(self, value):
        return round(float(value or 0), 2)

    def get(self, request):
        fecha_desde_raw = request.query_params.get('fecha_desde')
        fecha_hasta_raw = request.query_params.get('fecha_hasta')
        fecha_desde = self._parse_date(fecha_desde_raw)
        fecha_hasta = self._parse_date(fecha_hasta_raw)

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

        ventas_qs = (
            Venta.objects
            .select_related('becado__user', 'cuenta_abierta')
            .prefetch_related('detalles__producto')
            .filter(cuenta_abierta__isnull=False)
            .order_by('cuenta_abierta_id', '-fecha')
        )

        pagos_qs = (
            PagoCuentaAbierta.objects
            .select_related('cuenta_abierta', 'usuario_registro')
            .prefetch_related('imputaciones__venta')
            .order_by('-fecha_pago', '-id')
        )

        if fecha_desde:
            inicio = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), self.REPORT_TIMEZONE)
            ventas_qs = ventas_qs.filter(fecha__gte=inicio)
            pagos_qs = pagos_qs.filter(fecha_pago__gte=inicio)

        if fecha_hasta:
            fin_exclusivo = timezone.make_aware(
                datetime.combine(fecha_hasta + timedelta(days=1), datetime.min.time()),
                self.REPORT_TIMEZONE,
            )
            ventas_qs = ventas_qs.filter(fecha__lt=fin_exclusivo)
            pagos_qs = pagos_qs.filter(fecha_pago__lt=fin_exclusivo)

        cuentas = list(CuentaAbierta.objects.all().order_by('nombre_departamento'))
        ventas_por_cuenta = {cuenta.id: [] for cuenta in cuentas}
        pagos_por_cuenta = {cuenta.id: [] for cuenta in cuentas}
        modo_compatibilidad = False

        try:
            ventas = list(ventas_qs)
            pagos = list(pagos_qs)

            for venta in ventas:
                becado_user = venta.becado.user
                becado_nombre = (f'{becado_user.first_name} {becado_user.last_name}'.strip() or becado_user.username)
                ventas_por_cuenta.setdefault(venta.cuenta_abierta_id, []).append({
                    'id': venta.id,
                    'fecha': timezone.localtime(venta.fecha, self.REPORT_TIMEZONE).isoformat(),
                    'total': self._format_money(venta.total),
                    'saldo': self._format_money(venta.saldo),
                    'tipo_pago': venta.tipo_pago,
                    'becado_nombre': becado_nombre,
                    'detalles': [
                        {
                            'producto_nombre': detalle.producto.nombre,
                            'cantidad': detalle.cantidad,
                            'precio_unitario': self._format_money(detalle.precio_unitario),
                        }
                        for detalle in venta.detalles.all()
                    ],
                })

            for pago in pagos:
                pagos_por_cuenta.setdefault(pago.cuenta_abierta_id, []).append({
                    'id': pago.id,
                    'fecha_pago': timezone.localtime(pago.fecha_pago, self.REPORT_TIMEZONE).isoformat(),
                    'monto': self._format_money(pago.monto),
                    'metodo_pago': pago.metodo_pago,
                    'referencia': pago.referencia,
                    'observaciones': pago.observaciones,
                    'usuario_registro': pago.usuario_registro.get_full_name() or pago.usuario_registro.username,
                    'imputaciones': [
                        {
                            'venta_id': imputacion.venta_id,
                            'monto_aplicado': self._format_money(imputacion.monto_aplicado),
                            'saldo_anterior': self._format_money(imputacion.saldo_anterior),
                            'saldo_posterior': self._format_money(imputacion.saldo_posterior),
                        }
                        for imputacion in pago.imputaciones.all()
                    ],
                })
        except (ProgrammingError, OperationalError):
            # Compatibilidad temporal para entornos con migraciones pendientes.
            modo_compatibilidad = True
            ventas_legacy_qs = (
                Venta.objects
                .select_related('becado__user', 'cuenta_abierta')
                .prefetch_related('detalles__producto')
                .only('id', 'fecha', 'total', 'tipo_pago', 'becado_id', 'cuenta_abierta_id')
                .filter(cuenta_abierta__isnull=False)
                .order_by('cuenta_abierta_id', '-fecha')
            )

            if fecha_desde:
                inicio = timezone.make_aware(datetime.combine(fecha_desde, datetime.min.time()), self.REPORT_TIMEZONE)
                ventas_legacy_qs = ventas_legacy_qs.filter(fecha__gte=inicio)

            if fecha_hasta:
                fin_exclusivo = timezone.make_aware(
                    datetime.combine(fecha_hasta + timedelta(days=1), datetime.min.time()),
                    self.REPORT_TIMEZONE,
                )
                ventas_legacy_qs = ventas_legacy_qs.filter(fecha__lt=fin_exclusivo)

            for venta in ventas_legacy_qs:
                becado_user = venta.becado.user
                becado_nombre = (f'{becado_user.first_name} {becado_user.last_name}'.strip() or becado_user.username)
                total = self._format_money(venta.total)
                ventas_por_cuenta.setdefault(venta.cuenta_abierta_id, []).append({
                    'id': venta.id,
                    'fecha': timezone.localtime(venta.fecha, self.REPORT_TIMEZONE).isoformat(),
                    'total': total,
                    'saldo': total,
                    'tipo_pago': venta.tipo_pago,
                    'becado_nombre': becado_nombre,
                    'detalles': [
                        {
                            'producto_nombre': detalle.producto.nombre,
                            'cantidad': detalle.cantidad,
                            'precio_unitario': self._format_money(detalle.precio_unitario),
                        }
                        for detalle in venta.detalles.all()
                    ],
                })

        resultado_cuentas = []
        for cuenta in cuentas:
            ventas = ventas_por_cuenta.get(cuenta.id, [])
            pagos = pagos_por_cuenta.get(cuenta.id, [])
            total_cuenta = sum(venta['total'] for venta in ventas)
            total_pendiente = sum(venta['saldo'] for venta in ventas)
            total_pagado = sum(pago['monto'] for pago in pagos)
            resultado_cuentas.append({
                'cuenta_id': cuenta.id,
                'nombre_departamento': cuenta.nombre_departamento,
                'responsable': cuenta.responsable,
                'activo': cuenta.activo,
                'cantidad_ventas': len(ventas),
                'total_ventas': round(total_cuenta, 2),
                'total_pendiente': round(total_pendiente, 2),
                'total_pagado': round(total_pagado, 2),
                'ventas': ventas,
                'pagos': pagos,
            })

        return Response({
            'filtros': {
                'fecha_desde': fecha_desde.isoformat() if fecha_desde else None,
                'fecha_hasta': fecha_hasta.isoformat() if fecha_hasta else None,
            },
            'modo_compatibilidad': modo_compatibilidad,
            'cuentas': resultado_cuentas,
        })

class AuditoriaVentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').all().order_by('-fecha_correccion')
    serializer_class = AuditoriaVentaSerializer

    def get_queryset(self):
        venta_id = self.request.query_params.get('venta_id')
        queryset = AuditoriaVenta.objects.select_related('usuario_corrector', 'venta').order_by('-fecha_correccion')
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        return queryset
