from django.db.models import Count
from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from .models import Contact, Deal
from .serializers import ContactSerializer, DealSerializer


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "email", "company"]

    def get_queryset(self):
        return Contact.objects.filter(owner=self.request.user).annotate(deal_count=Count("deals")).order_by("-created_at", "-pk")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response({"detail": "Remove or reassign this contact's deals first."}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DealViewSet(viewsets.ModelViewSet):
    serializer_class = DealSerializer

    def get_queryset(self):
        queryset = Deal.objects.filter(contact__owner=self.request.user).select_related("contact")
        stage = self.request.query_params.get("stage")
        return queryset.filter(stage=stage) if stage else queryset
