from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Contact, Deal


class ContactSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    deal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Contact
        fields = ["id", "owner", "name", "email", "company", "deal_count", "created_at"]
        read_only_fields = ["created_at"]
        validators = [UniqueTogetherValidator(queryset=Contact.objects.all(), fields=["owner", "email"])]

    def validate_email(self, value):
        return value.strip().lower()


class DealSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.none())
    value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    class Meta:
        model = Deal
        fields = ["id", "contact", "contact_name", "title", "value", "stage", "created_at"]
        read_only_fields = ["created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["contact"].queryset = Contact.objects.filter(owner=request.user)
