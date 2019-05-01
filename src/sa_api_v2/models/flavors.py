from django.contrib.gis.db import models


class Flavor(models.Model):
    name = models.CharField(max_length=128, unique=True)

    # TODO: add datasets
    # These are the datasets that the flavor reads from.
    # datasets = models.ManyToManyField(DataSet, related_name='tags', on_delete=models.CASCADE)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_flavor'
        ordering = ['name']
