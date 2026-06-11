from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from .models import Producto, Categoria, CuentaAbierta, Venta, DetalleVenta


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'stock', 'es_servicio', 'categoria', 'categoria_nombre']


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
