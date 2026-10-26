from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from crm.views import ContactViewSet, DealViewSet

router = DefaultRouter()
router.register("contacts", ContactViewSet, basename="contact")
router.register("deals", DealViewSet, basename="deal")
urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
