from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from gestion.models import AuditoriaVenta, Categoria, DetalleVenta, PerfilBecado, Producto, Venta
from gestion.serializers import VentaUpdateSerializer


class VentaUpdateSerializerAuditTests(SimpleTestCase):
    def test_group_changes_in_single_audit_entry_when_multiple_fields_change(self):
        serializer = VentaUpdateSerializer()
        snapshot_anterior = {
            'tipo_pago': 'efectivo',
            'monto_efectivo': '100.00',
            'total': '100.00',
            'cuenta_abierta': '',
        }
        snapshot_nuevo = {
            'tipo_pago': 'transferencia',
            'monto_efectivo': '50.00',
            'total': '50.00',
            'cuenta_abierta': '',
        }

        audit_data = serializer._build_audit_entry(snapshot_anterior, snapshot_nuevo)

        self.assertEqual(audit_data['campo_modificado'], 'Varios campos')
        self.assertIn('tipo_pago=efectivo', audit_data['valor_anterior'])
        self.assertIn('monto_efectivo=100.00', audit_data['valor_anterior'])
        self.assertIn('total=100.00', audit_data['valor_anterior'])
        self.assertIn('tipo_pago=transferencia', audit_data['valor_nuevo'])
        self.assertIn('monto_efectivo=50.00', audit_data['valor_nuevo'])
        self.assertIn('total=50.00', audit_data['valor_nuevo'])


class VentaUpdateSerializerIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='becado', password='test123')
        self.perfil = PerfilBecado.objects.create(user=self.user, dni='12345678', legajo='A1')
        self.categoria = Categoria.objects.create(nombre='General tests')
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            nombre='Fotocopia A4',
            precio=Decimal('20.00'),
            stock=100,
            es_servicio=False,
        )
        self.venta = Venta.objects.create(
            becado=self.perfil,
            tipo_pago=Venta.TIPO_PAGO_EFECTIVO,
            monto_efectivo=Decimal('100.00'),
            monto_transferencia=Decimal('0.00'),
            total=Decimal('100.00'),
        )
        DetalleVenta.objects.create(
            venta=self.venta,
            producto=self.producto,
            cantidad=5,
            precio_unitario=Decimal('20.00'),
        )

    def test_update_creates_single_audit_entry_for_sale_change(self):
        serializer = VentaUpdateSerializer(context={'request': SimpleNamespace(user=self.user)})

        serializer.update(
            self.venta,
            {
                'items': [{'producto_id': self.producto.id, 'cantidad': 4}],
                'tipo_pago': Venta.TIPO_PAGO_EFECTIVO,
                'monto_efectivo': Decimal('80.00'),
                'monto_transferencia': Decimal('0.00'),
                'motivo_auditoria': 'eran 100 fotocopias menos',
            },
        )

        self.assertEqual(AuditoriaVenta.objects.count(), 1)
        auditoria = AuditoriaVenta.objects.get()
        self.assertEqual(auditoria.usuario_corrector, self.user)
        self.assertEqual(auditoria.motivo, 'eran 100 fotocopias menos')
        self.assertEqual(auditoria.campo_modificado, 'Varios campos')
        self.assertIn(f'detalles={self.producto.id}:5:20.00', auditoria.valor_anterior)
        self.assertIn(f'detalles={self.producto.id}:4:20.00', auditoria.valor_nuevo)
