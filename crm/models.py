from django.conf import settings
from django.db import models


class Contact(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    email = models.EmailField()
    company = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["owner", "email"], name="unique_contact_email_per_owner")]
        indexes = [models.Index(fields=["owner", "-created_at"], name="contact_owner_created")]

    def __str__(self):
        return self.name


class Deal(models.Model):
    class Stage(models.TextChoices):
        NEW = "new", "New"
        QUALIFIED = "qualified", "Qualified"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="deals")
    title = models.CharField(max_length=180)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(value__gte=0), name="deal_value_nonnegative")]
        indexes = [models.Index(fields=["contact", "stage"], name="deal_contact_stage")]
