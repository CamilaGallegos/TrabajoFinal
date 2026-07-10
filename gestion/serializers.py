from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from .models import Producto, Categoria, CuentaAbierta, Venta, DetalleVenta, AuditoriaVenta


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'stock', 'es_servicio', 'categoria', 'categoria_nombre', 'activo']

    def create(self, validated_data):
        # Si no se proporciona categoría, usar o crear la categoría por defecto "General"
        if 'categoria' not in validated_data or validated_data['categoria'] is None:
            categoria_default, _ = Categoria.objects.get_or_create(nombre='General')
            validated_data['categoria'] = categoria_default
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Permitir actualizar campos, incluido 'activo'
        return super().update(instance, validated_data)


class CuentaAbiertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaAbierta
        fields = ['id', 'nombre_departamento', 'responsable']


class VentaItemCreateSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)


class VentaCreateSerializer(serializers.Serializer):
    items = VentaItemCreateSerializer(many=True)
    tipo_pago = serializers.ChoiceField(choices=Venta.TIPO_PAGO_CHOICES)
    cuenta_abierta_id = serializers.PrimaryKeyRelatedField(
        queryset=CuentaAbierta.objects.all(),
        required=False,
        allow_null=True,
        source='cuenta_abierta',
    )
    monto_efectivo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    monto_transferencia = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))

    def validate(self, attrs):
        tipo_pago = attrs['tipo_pago']
        cuenta_abierta = attrs.get('cuenta_abierta')
        monto_efectivo = attrs['monto_efectivo']
        monto_transferencia = attrs['monto_transferencia']

        if tipo_pago == Venta.TIPO_PAGO_CUENTA_ABIERTA and not cuenta_abierta:
            raise serializers.ValidationError({'cuenta_abierta_id': 'Debe seleccionar una cuenta abierta.'})

        if tipo_pago != Venta.TIPO_PAGO_CUENTA_ABIERTA and cuenta_abierta:
            raise serializers.ValidationError({'cuenta_abierta_id': 'La cuenta abierta solo aplica a ventas con cuenta abierta.'})

        if tipo_pago == Venta.TIPO_PAGO_EFECTIVO and monto_transferencia != Decimal('0'):
            raise serializers.ValidationError({'monto_transferencia': 'Debe ser 0 para ventas en efectivo.'})

        if tipo_pago == Venta.TIPO_PAGO_TRANSFERENCIA and monto_efectivo != Decimal('0'):
            raise serializers.ValidationError({'monto_efectivo': 'Debe ser 0 para ventas por transferencia.'})

        if tipo_pago == Venta.TIPO_PAGO_CUENTA_ABIERTA and (monto_efectivo != Decimal('0') or monto_transferencia != Decimal('0')):
            raise serializers.ValidationError('Las ventas por cuenta abierta no deben registrar montos en efectivo o transferencia.')

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        try:
            becado = request.user.perfil
        except Exception as exc:
            raise serializers.ValidationError('El usuario autenticado no tiene un perfil de becado asociado.') from exc

        items_data = validated_data.pop('items')
        productos_ids = [item['producto_id'] for item in items_data]
        productos = {
            producto.id: producto
            for producto in Producto.objects.select_for_update().filter(id__in=productos_ids)
        }

        if len(productos) != len(set(productos_ids)):
            raise serializers.ValidationError('Uno o más productos seleccionados no existen.')

        total = Decimal('0')
        detalles = []

        for item_data in items_data:
            producto = productos[item_data['producto_id']]
            cantidad = item_data['cantidad']

            if not producto.es_servicio:
                stock_actual = producto.stock or 0
                if stock_actual < cantidad:
                    raise serializers.ValidationError(
                        {'items': f'Stock insuficiente para {producto.nombre}. Disponible: {stock_actual}.'}
                    )

            subtotal = producto.precio * cantidad
            total += subtotal
            detalles.append((producto, cantidad, producto.precio))

        monto_efectivo = validated_data['monto_efectivo']
        monto_transferencia = validated_data['monto_transferencia']
        tipo_pago = validated_data['tipo_pago']

        if tipo_pago == Venta.TIPO_PAGO_EFECTIVO and monto_efectivo != total:
            raise serializers.ValidationError({'monto_efectivo': 'Debe coincidir con el total de la venta.'})

        if tipo_pago == Venta.TIPO_PAGO_TRANSFERENCIA and monto_transferencia != total:
            raise serializers.ValidationError({'monto_transferencia': 'Debe coincidir con el total de la venta.'})

        if tipo_pago == Venta.TIPO_PAGO_COMBINADO and (monto_efectivo + monto_transferencia) != total:
            raise serializers.ValidationError('La suma de efectivo y transferencia debe coincidir con el total de la venta.')

        venta = Venta.objects.create(
            becado=becado,
            total=total,
            tipo_pago=tipo_pago,
            monto_efectivo=monto_efectivo,
            monto_transferencia=monto_transferencia,
            cuenta_abierta=validated_data.get('cuenta_abierta'),
        )

        for producto, cantidad, precio_unitario in detalles:
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
            )
            if not producto.es_servicio:
                producto.stock = (producto.stock or 0) - cantidad
                producto.save(update_fields=['stock'])

        return venta


class VentaUpdateSerializer(serializers.Serializer):
    items = VentaItemCreateSerializer(many=True)
    tipo_pago = serializers.ChoiceField(choices=Venta.TIPO_PAGO_CHOICES)
    cuenta_abierta_id = serializers.PrimaryKeyRelatedField(
        queryset=CuentaAbierta.objects.all(),
        required=False,
        allow_null=True,
        source='cuenta_abierta',
    )
    monto_efectivo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    monto_transferencia = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    motivo_auditoria = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        tipo_pago = attrs['tipo_pago']
        cuenta_abierta = attrs.get('cuenta_abierta')
        monto_efectivo = attrs['monto_efectivo']
        monto_transferencia = attrs['monto_transferencia']

        if tipo_pago == Venta.TIPO_PAGO_CUENTA_ABIERTA and not cuenta_abierta:
            raise serializers.ValidationError({'cuenta_abierta_id': 'Debe seleccionar una cuenta abierta.'})

        if tipo_pago != Venta.TIPO_PAGO_CUENTA_ABIERTA and cuenta_abierta:
            raise serializers.ValidationError({'cuenta_abierta_id': 'La cuenta abierta solo aplica a ventas con cuenta abierta.'})

        if tipo_pago == Venta.TIPO_PAGO_EFECTIVO and monto_transferencia != Decimal('0'):
            raise serializers.ValidationError({'monto_transferencia': 'Debe ser 0 para ventas en efectivo.'})

        if tipo_pago == Venta.TIPO_PAGO_TRANSFERENCIA and monto_efectivo != Decimal('0'):
            raise serializers.ValidationError({'monto_efectivo': 'Debe ser 0 para ventas por transferencia.'})

        if tipo_pago == Venta.TIPO_PAGO_CUENTA_ABIERTA and (monto_efectivo != Decimal('0') or monto_transferencia != Decimal('0')):
            raise serializers.ValidationError('Las ventas por cuenta abierta no deben registrar montos en efectivo o transferencia.')

        return attrs

    def _build_audit_entry(self, snapshot_anterior, snapshot_nuevo):
        cambios = []

        for campo, valor_anterior in snapshot_anterior.items():
            valor_nuevo = snapshot_nuevo[campo]
            if valor_anterior != valor_nuevo:
                cambios.append((campo, valor_anterior, valor_nuevo))

        if not cambios:
            return None

        if len(cambios) == 1:
            campo_modificado, valor_anterior, valor_nuevo = cambios[0]
            return {
                'campo_modificado': campo_modificado,
                'valor_anterior': str(valor_anterior),
                'valor_nuevo': str(valor_nuevo),
            }

        return {
            'campo_modificado': 'Varios campos',
            'valor_anterior': ' | '.join(
                f'{campo}={valor_anterior}'
                for campo, valor_anterior, _ in cambios
            ),
            'valor_nuevo': ' | '.join(
                f'{campo}={valor_nuevo}'
                for campo, _, valor_nuevo in cambios
            ),
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context['request']
        motivo = validated_data.pop('motivo_auditoria', '')
        items_data = validated_data.pop('items')

        productos_ids = [item['producto_id'] for item in items_data]

        productos_a_actualizar = Producto.objects.select_for_update().filter(
            id__in=list(set(productos_ids + [d.producto_id for d in instance.detalles.all()]))
        )
        productos_map = {producto.id: producto for producto in productos_a_actualizar}

        if len(set(productos_ids)) != len([pid for pid in set(productos_ids) if pid in productos_map]):
            raise serializers.ValidationError('Uno o más productos seleccionados no existen')

        # revertir cambios de stock de los detalles anteriores
        detalles_anteriores = list(instance.detalles.select_related('producto').all())
        for detalle in detalles_anteriores:
            producto = productos_map.get(detalle.producto_id)
            if producto and not producto.es_servicio:
                producto.stock = (producto.stock or 0) + detalle.cantidad
                producto.save(update_fields=['stock'])

        total_nuevo = Decimal('0')
        detalles_nuevos = []

        for item_data in items_data:
            producto = productos_map[item_data['producto_id']]
            cantidad = item_data['cantidad']

            if not producto.es_servicio:
                stock_actual = producto.stock or 0
                if stock_actual < cantidad:
                    raise serializers.ValidationError(
                        {'items': f'Stock insuficiente para {producto.nombre}. Disponible: {stock_actual}.'}
                    )

            subtotal = producto.precio * cantidad
            total_nuevo += subtotal
            detalles_nuevos.append((producto, cantidad, producto.precio))

        tipo_pago = validated_data['tipo_pago']
        monto_efectivo = validated_data['monto_efectivo']
        monto_transferencia = validated_data['monto_transferencia']

        if tipo_pago == Venta.TIPO_PAGO_EFECTIVO and monto_efectivo != total_nuevo:
            raise serializers.ValidationError({'monto_efectivo': 'Debe coincidir con el total de la venta.'})

        if tipo_pago == Venta.TIPO_PAGO_TRANSFERENCIA and monto_transferencia != total_nuevo:
            raise serializers.ValidationError({'monto_transferencia': 'Debe coincidir con el total de la venta.'})

        if tipo_pago == Venta.TIPO_PAGO_COMBINADO and (monto_efectivo + monto_transferencia) != total_nuevo:
            raise serializers.ValidationError('La suma de efectivo y transferencia debe coincidir con el total de la venta.')

        snapshot_anterior = {
            'tipo_pago': instance.tipo_pago,
            'monto_efectivo': str(instance.monto_efectivo),
            'monto_transferencia': str(instance.monto_transferencia),
            'total': str(instance.total),
            'cuenta_abierta': str(instance.cuenta_abierta_id or ''),
            'detalles': '|'.join(
                sorted(
                    [
                        f"{d.producto_id}:{d.cantidad}:{d.precio_unitario}"
                        for d in detalles_anteriores
                    ]
                )
            ),
        }

        instance.tipo_pago = tipo_pago
        instance.monto_efectivo = monto_efectivo
        instance.monto_transferencia = monto_transferencia
        instance.total = total_nuevo
        instance.cuenta_abierta = validated_data.get('cuenta_abierta')
        instance._skip_audit_signal = True
        instance.save(update_fields=['tipo_pago', 'monto_efectivo', 'monto_transferencia', 'total', 'cuenta_abierta'])

        instance.detalles.all().delete()
        for producto, cantidad, precio_unitario in detalles_nuevos:
            DetalleVenta.objects.create(
                venta=instance,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
            )
            if not producto.es_servicio:
                producto.stock = (producto.stock or 0) - cantidad
                producto.save(update_fields=['stock'])

        snapshot_nuevo = {
            'tipo_pago': instance.tipo_pago,
            'monto_efectivo': str(instance.monto_efectivo),
            'monto_transferencia': str(instance.monto_transferencia),
            'total': str(instance.total),
            'cuenta_abierta': str(instance.cuenta_abierta_id or ''),
            'detalles': '|'.join(
                sorted(
                    [
                        f"{d.producto_id}:{d.cantidad}:{d.precio_unitario}"
                        for d in instance.detalles.all()
                    ]
                )
            ),
        }

        audit_entry = self._build_audit_entry(snapshot_anterior, snapshot_nuevo)
        if audit_entry:
            AuditoriaVenta.objects.create(
                venta=instance,
                usuario_corrector=request.user,
                campo_modificado=audit_entry['campo_modificado'],
                valor_anterior=audit_entry['valor_anterior'],
                valor_nuevo=audit_entry['valor_nuevo'],
                motivo=motivo,
            )
        return instance


class VentaSerializer(serializers.ModelSerializer):
    becado_nombre = serializers.ReadOnlyField(source='becado.user.first_name')
    detalles = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = [
            'id',
            'fecha',
            'total',
            'tipo_pago',
            'monto_efectivo',
            'monto_transferencia',
            'cuenta_abierta',
            'becado',
            'becado_nombre',
            'detalles',
        ]

    def get_detalles(self, obj):
        return [
            {
                'producto_id': detalle.producto_id,
                'producto_nombre': detalle.producto.nombre,
                'cantidad': detalle.cantidad,
                'precio_unitario': detalle.precio_unitario,
            }
            for detalle in obj.detalles.select_related('producto').all()
        ]

class AuditoriaVentaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario_corrector.get_full_name', read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(source='venta', read_only=True)
    becado_nombre = serializers.CharField(source='venta.becado.user.first_name', read_only=True)

    class Meta:
        model = AuditoriaVenta
        fields = ['id', 'venta_id', 'usuario_corrector', 'usuario_nombre', 'becado_nombre', 'fecha_correccion', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'motivo']
        read_only_fields = ['id', 'usuario_corrector', 'fecha_correccion']
