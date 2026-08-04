from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay, TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Venta, DetalleVenta, PagoCuentaAbierta, CuentaAbierta


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
                becado_nombre = (f"{becado_user.first_name} {becado_user.last_name}".strip() or becado_user.username)
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
                becado_nombre = (f"{becado_user.first_name} {becado_user.last_name}".strip() or becado_user.username)
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
