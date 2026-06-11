from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioListView(generics.ListAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]
