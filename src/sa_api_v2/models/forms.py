from django.contrib.gis.db import models
from .core import DataSet
from .flavors import Flavor


class Form(models.Model):
    label = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    dataset = models.ForeignKey(DataSet, related_name='+', on_delete=models.CASCADE)

    flavor = models.ForeignKey(
        Flavor,
        related_name='forms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __unicode__(self):
        return self.label

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form'
