from rest_framework import serializers
from .models import Producto, Categoria, CuentaAbierta

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
        