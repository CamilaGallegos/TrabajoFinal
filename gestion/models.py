from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(null=True, blank=True)
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
    becado = models.ForeignKey(PerfilBecado, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    cuenta_abierta = models.ForeignKey(
        CuentaAbierta, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ventas'
    )

    def __str__(self):
        tipo = f"Cuenta: {self.cuenta_abierta}" if self.cuenta_abierta else "Efectivo"
        return f"Venta {self.id} - {tipo} (${self.total})"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"