from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from .models import Producto, PerfilBecado, Asistencia
from .serializers import ProductoSerializer
from django.utils import timezone

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class FichajeEntradaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        dni_recibido = request.data.get('dni')
        
        if not dni_recibido:
            return Response({"error": "El DNI es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # buscamos al becado por su DNI
            becado = PerfilBecado.objects.get(dni=dni_recibido)
            usuario = becado.user
            
            # fichaje automatico
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

            # token JWT para el turno actual
            token = AccessToken.for_user(usuario)
            
            return Response({
                "token": str(token),
                "becado": {
                    "id": becado.id,
                    "nombre": usuario.first_name or usuario.username,
                    "dni": becado.dni
                },
                "msg": mensaje_fichaje
            }, status=status.HTTP_200_OK)
            
        except PerfilBecado.DoesNotExist:
            return Response({"error": "No existe ningún becado/a con ese DNI"}, status=status.HTTP_404_NOT_FOUND)