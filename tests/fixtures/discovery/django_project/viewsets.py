"""Sample DRF ViewSet for testing route discovery."""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="archive")
    def archive_item(self, request, pk=None):
        return Response({"archived": True})

    @action(detail=False, methods=["get"])
    def recent(self, request):
        return Response([])


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    pass
