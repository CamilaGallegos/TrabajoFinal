from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import DetalleVenta, Venta, AuditoriaVenta

@receiver(pre_save, sender=DetalleVenta)
def guardar_cantidad_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = DetalleVenta.objects.get(pk=instance.pk)
            instance._cantidad_anterior = old_instance.cantidad
        except DetalleVenta.DoesNotExist:
            instance._cantidad_anterior = 0
    else:
        instance._cantidad_anterior = 0

@receiver(post_save, sender=DetalleVenta)
@receiver(post_delete, sender=DetalleVenta)
def actualizar_total_venta(sender, instance, **kwargs):
    venta = instance.venta
    detalles = venta.detalles.all()
    
    nuevo_total = sum(d.cantidad * d.precio_unitario for d in detalles)
    
    # update pq con save podria armarse un bucle
    venta.__class__.objects.filter(id=venta.id).update(total=nuevo_total)
# manejo de stock
@receiver(post_save, sender=DetalleVenta)
def ajustar_stock_dinamico(sender, instance, created, **kwargs):
    producto = instance.producto
    
    if producto.es_servicio or producto.stock is None:
        return

    if created:
        diferencia = instance.cantidad
    else:
        cantidad_anterior = getattr(instance, '_cantidad_anterior', 0)
        diferencia = instance.cantidad - cantidad_anterior

    producto.stock -= diferencia
    producto.save(update_fields=['stock'])

@receiver(post_delete, sender=DetalleVenta)
def devolver_stock(sender, instance, **kwargs):
    producto = instance.producto

    if producto.es_servicio or producto.stock is None:
        return

    producto.stock += instance.cantidad
    producto.save(update_fields=['stock'])
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
                AuditoriaVenta.objects.create(
                    venta=instance,
                    usuario_corrector=instance.becado.user,
                    campo_modificado="total",
                    valor_anterior=str(old_instance.total),
                    valor_nuevo=str(instance.total),
                    motivo="Ajuste automático por cambio en detalles"
                )
        except Venta.DoesNotExist:
            pass