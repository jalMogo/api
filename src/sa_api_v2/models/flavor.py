from django.contrib.gis.db import models


class Flavor(models.Model):
    name = models.CharField(max_length=128, unique=True)

    # TODO: add datasets
    # datasets = models.ManyToManyField(DataSet, related_name='tags', on_delete=models.CASCADE)

    def __unicode__(self):
        return "{name}".format(name=self.name)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_flavor'
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=128)
    icon = models.CharField(max_length=128)
    flavor = models.ForeignKey(Flavor, related_name='categories',
                               on_delete=models.CASCADE)
    # TODO, once Form model is created:
    # form = models.ForeignKey(Form, related_name='categories',
    # on_delete=models.CASCADE)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_category'
        # ordering = ['name']
