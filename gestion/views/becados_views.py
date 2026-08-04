from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from ..models import PerfilBecado
from ..serializers import PerfilBecadoAdminSerializer, PerfilBecadoCreateSerializer


class PerfilBecadoAdminViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = PerfilBecado.objects.select_related('user').all().order_by('user__first_name', 'user__last_name', 'dni')

    def get_serializer_class(self):
        if self.action == 'create':
            return PerfilBecadoCreateSerializer
        return PerfilBecadoAdminSerializer

    def _validar_admin(self, request):
        if not (request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
            raise PermissionDenied('Solo administradores pueden gestionar becados.')

    def list(self, request, *args, **kwargs):
        self._validar_admin(request)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._validar_admin(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()
        response_serializer = PerfilBecadoAdminSerializer(perfil)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        self._validar_admin(request)
        perfil = self.get_object()
        if 'activo' not in request.data:
            return Response({'detail': 'Debe enviar el campo activo.'}, status=status.HTTP_400_BAD_REQUEST)

        valor_activo = request.data.get('activo')
        if isinstance(valor_activo, bool):
            activo = valor_activo
        else:
            activo = str(valor_activo).strip().lower() in {'1', 'true', 'si', 'yes'}

        if perfil.user_id == request.user.id and not activo:
            return Response(
                {'detail': 'No podes inhabilitar tu propio usuario mientras esta en uso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil.user.is_active = activo
        perfil.user.save(update_fields=['is_active'])
        response_serializer = PerfilBecadoAdminSerializer(perfil)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
