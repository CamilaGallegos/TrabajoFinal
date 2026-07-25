from django.db import models
from django.utils import timezone

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    es_servicio = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} (${self.precio})"

# usuario becado
from django.contrib.auth.models import User

class PerfilBecado(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    dni = models.CharField(max_length=15, unique=True)
    legajo = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - DNI: {self.dni}"

class Asistencia(models.Model):
    becado = models.ForeignKey(PerfilBecado, on_delete=models.CASCADE)
    entrada = models.DateTimeField(auto_now_add=True)
    salida = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.becado.user.first_name} - {self.entrada.strftime('%d/%m %H:%M')}"
    
# ventas y cuentas abiertas
class CuentaAbierta(models.Model):
    nombre_departamento = models.CharField(max_length=100, unique=True)
    responsable = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre_departamento

class Venta(models.Model):
    TIPO_PAGO_EFECTIVO = 'efectivo'
    TIPO_PAGO_TRANSFERENCIA = 'transferencia'
    TIPO_PAGO_COMBINADO = 'combinado'
    TIPO_PAGO_CUENTA_ABIERTA = 'cuenta_abierta'

    TIPO_PAGO_CHOICES = [
        (TIPO_PAGO_EFECTIVO, 'Efectivo'),
        (TIPO_PAGO_TRANSFERENCIA, 'Transferencia'),
        (TIPO_PAGO_COMBINADO, 'Combinado'),
        (TIPO_PAGO_CUENTA_ABIERTA, 'Cuenta Abierta'),
    ]

    becado = models.ForeignKey(PerfilBecado, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES, default=TIPO_PAGO_EFECTIVO)
    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cuenta_abierta = models.ForeignKey(
        CuentaAbierta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas'
    )

    def __str__(self):
        tipo = self.get_tipo_pago_display()
        if self.cuenta_abierta:
            tipo = f"Cuenta: {self.cuenta_abierta}"
        return f"Venta {self.id} - {tipo} (${self.total})"


class PagoCuentaAbierta(models.Model):
    METODO_EFECTIVO = 'efectivo'
    METODO_TRANSFERENCIA = 'transferencia'
    METODO_OTRO = 'otro'

    METODO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TRANSFERENCIA, 'Transferencia'),
        (METODO_OTRO, 'Otro'),
    ]

    cuenta_abierta = models.ForeignKey(CuentaAbierta, on_delete=models.PROTECT, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, default=METODO_TRANSFERENCIA)
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pagos_cuentas_abiertas')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_pago', '-id']

    def __str__(self):
        return f"Pago cuenta {self.cuenta_abierta_id} - ${self.monto}"


class ImputacionPagoVenta(models.Model):
    pago = models.ForeignKey(PagoCuentaAbierta, on_delete=models.CASCADE, related_name='imputaciones')
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='imputaciones_pago')
    monto_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_posterior = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['venta__fecha', 'venta_id']

    def __str__(self):
        return f"Pago {self.pago_id} -> Venta {self.venta_id}: ${self.monto_aplicado}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
# auditoria
class AuditoriaVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='auditorias')
    usuario_corrector = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha_correccion = models.DateTimeField(auto_now_add=True)
    
    campo_modificado = models.CharField(max_length=100) 
    valor_anterior = models.CharField(max_length=255)
    valor_nuevo = models.CharField(max_length=255)
    motivo = models.TextField(blank=True)

    def __str__(self):
        return f"Corrección Venta {self.venta.id} - {self.fecha_correccion.strftime('%d/%m/%y')}"