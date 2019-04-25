from django.contrib.gis.db import models
from .forms import Form


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


class Category(models.Model):
    name = models.CharField(max_length=128)
    icon = models.CharField(max_length=128)
    flavor = models.ForeignKey(Flavor, related_name='categories',
                               on_delete=models.CASCADE)
    # These forms are attached to datasets, which the flavor writes to.
    form = models.ForeignKey(Form, related_name='+',
                             on_delete=models.CASCADE)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_category'
