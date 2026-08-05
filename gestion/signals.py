from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import DetalleVenta, Venta, AuditoriaVenta

@receiver(post_save, sender=DetalleVenta)
@receiver(post_delete, sender=DetalleVenta)
def actualizar_total_venta(sender, instance, **kwargs):
    venta = instance.venta
    detalles = venta.detalles.all()

    nuevo_total = sum((d.cantidad * d.precio_unitario for d in detalles), Decimal('0'))

    # Usamos update para evitar re-disparar señales de Venta con save().
    if venta.tipo_pago == Venta.TIPO_PAGO_CUENTA_ABIERTA:
        total_imputado = venta.imputaciones_pago.aggregate(total=Sum('monto_aplicado')).get('total') or Decimal('0')
        nuevo_saldo = nuevo_total - total_imputado
        if nuevo_saldo < 0:
            nuevo_saldo = Decimal('0')
        venta.__class__.objects.filter(id=venta.id).update(total=nuevo_total, saldo=nuevo_saldo)
    else:
        venta.__class__.objects.filter(id=venta.id).update(total=nuevo_total, saldo=0)

# precio automaticado (toma del producto)
@receiver(pre_save, sender=DetalleVenta)
def asignar_precio_unitario(sender, instance, **kwargs):
    if not instance.precio_unitario:
        instance.precio_unitario = instance.producto.precio

#auditoria
@receiver(pre_save, sender=Venta)
def auditar_cambios_venta(sender, instance, **kwargs):
    if getattr(instance, '_skip_audit_signal', False):
        return

    if instance.pk:
        try:
            old_instance = Venta.objects.get(pk=instance.pk)

            if old_instance.total != instance.total:
                usuario_corrector = getattr(instance, '_audit_user', None) or instance.becado.user
                AuditoriaVenta.objects.create(
                    venta=instance,
                    usuario_corrector=usuario_corrector,
                    campo_modificado="total",
                    valor_anterior=str(old_instance.total),
                    valor_nuevo=str(instance.total),
                    motivo="Ajuste automático por cambio en detalles"
                )
        except Venta.DoesNotExist:
            pass