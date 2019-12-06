from django.contrib.gis.db import models


class Flavor(models.Model):
    display_name = models.CharField(max_length=128)

    slug = models.SlugField(max_length=128, default="", unique=True)

    # TODO: add datasets to the flavor. The client needs to know which
    # dataset endpoints to download and display on the map, and their
    # permissions.

    # datasets = models.ManyToManyField(DataSet, related_name='tags', on_delete=models.CASCADE)

    # AND, consider adding a "LayerGroup" model, which references
    # an ordered list of models that represent either a styled
    # DataSet, or other vector/raster/geojson source.

    def __str__(self):
        return self.display_name

    class Meta:
        app_label = "sa_api_v2"
        db_table = "ms_api_flavor"
        ordering = ["display_name"]
