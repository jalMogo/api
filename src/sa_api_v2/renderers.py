import ujson as json
from rest_framework.renderers import JSONRenderer
from rest_framework_csv.renderers import CSVRenderer
from django.contrib.gis.geos import GEOSGeometry


class PaginatedCSVRenderer (CSVRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        if not isinstance(data, list):
            data = data.get('results') or data.get('features')
        return super(PaginatedCSVRenderer, self).render(data, media_type, renderer_context)


class GeoJSONRenderer(JSONRenderer):
    """
    Renderer which serializes to GeoJSON
    """

    media_type = 'application/json'
    format = 'json'
    geometry_field = 'geometry'
    id_field = 'id'

    def render(self, data, media_type=None, renderer_context=None):
        """
        Renders *data* into a GeoJSON feature.
        """
        # Let error codes slip through to the super class method.
        response = (renderer_context or {}).get('response')
        if response and response.status_code >= 400:
            return super(GeoJSONRenderer, self).render(data, media_type, renderer_context)

        # Assume everything else is a successful geometry.
        if isinstance(data, list):
            new_data = {
              'type': 'FeatureCollection',
              'features': [(self.get_feature(elem) or elem) for elem in data]
            }
        elif isinstance(data, dict) and data.get('type') == 'FeatureCollection':
            new_data = data.copy()
            new_data['features'] = [(self.get_feature(elem) or elem) for elem in data['features']]
        elif data is None:
            new_data = None
        else:
            new_data = self.get_feature(data) or data

        return super(GeoJSONRenderer, self).render(new_data, media_type, renderer_context)

    def get_feature(self, data):
        if 'geometry' not in data:
            return None

        feature_props = data.copy()
        geometry = feature_props.pop(self.geometry_field)
        feature_id = feature_props.get(self.id_field)  # Should this be popped?

        if isinstance(geometry, str):
            geometry = json.loads(GEOSGeometry(geometry).json)
        elif isinstance(geometry, GEOSGeometry):
            geometry = json.loads(geometry.json)

        feature = {
          'type': 'Feature',
          'geometry': geometry,
          'properties': feature_props,
        }

        if feature_id is not None:
            feature['id'] = feature_id

        return feature





class NullJSONRenderer(JSONRenderer):
    """
    Renderer JSON with a simple None value as null
    """
    def render(self, data, media_type=None, renderer_context=None):
        if data is None:
            return bytes('null'.encode('utf-8'))
        return super(NullJSONRenderer, self).render(data, media_type, renderer_context)


