from django.utils import dateparse
from django.db.models import Avg, Count, Max
from rest_framework import views
from rest_framework.response import Response
from rest_framework import authentication
from rest_framework import exceptions
from sga.models import TrackingArea, Store, Area
from sga.rest.permissions import AdminWritePermissions


class StatsView(views.APIView):
    authentication_classes = (authentication.TokenAuthentication,
                              authentication.SessionAuthentication,
                              authentication.BasicAuthentication)
    permission_classes = (AdminWritePermissions,)


    def get(self, request):
        if not request.user.is_authenticated():
            raise exceptions.NotAuthenticated()

        self.user = request.user
        self.params = request.query_params
        return Response(self.process_stats())

    def process_stats(self):
        json = {}
        stats = TrackingArea.objects.all()
        stats = self.process_dates(stats)

        store = Store.objects.get(id=self.params.get('store'))

        if store.parent:
            print('simple store')
            # Simple store
            json['area_data'] = self.process_areas(stats)
            json['nr_of_devices'] = stats.filter(area__store=store).annotate(Count('device', distinct=True)).count()
            json['best_day'] =  self.get_best_day(stats.filter(area__store=store))
            json['best_age'] = self.get_best_age(stats.filter(area__store=store))
        else:
            # Shopping center
            type = self.params.get('type')
            if type == 'area':
                json['area_data'] = self.process_areas(stats)
                json['nr_of_devices'] = stats.filter(area__store=store).annotate(Count('device', distinct=True)).count()
                json['best_day'] =  self.get_best_day(stats.filter(area__store=store))
                json['best_age'] = self.get_best_age(stats.filter(area__store=store))
            else:
                json['store_data'] = self.process_stores(stats)
                json['nr_of_devices'] = stats.filter(area__store__parent=store).annotate(Count('device', distinct=True)).count()
                json['best_age'] = self.get_best_age(stats.filter(area__store__parent=store))
                json['best_day'] = self.get_best_day(stats.filter(area__store__parent=store))
        return json


    def process_dates(self, stats):
        start_time = self.params.get('start_time')
        end_time = self.params.get('end_time')

        if end_time:
            date_max = dateparse.parse_datetime(end_time)
            stats = stats.filter(
                    end_time__lte=date_max
            )

        if start_time:
            date_min = dateparse.parse_datetime(start_time)
            stats = stats.filter(
                    start_time__gte=date_min
            )

        return stats

    def process_stores(self, stats):
        json_data = []
        parent = self.params.get('store')
        for store in Store.objects.filter(parent=parent):
            area_max = stats.filter(area__store=store).aggregate(Max('area'))['area__max']
            area = Area.objects.get(id=area_max)
            json = {
                'store': {
                    'id': store.id,
                    'name': store.name,
                    'best_area' : {'id': area.id, 'name': area.name},
                    'nr_of_devices': stats.filter(area__store=store).annotate(Count('device', distinct=True)).count(),
                    'best_day': self.get_best_day(stats.filter(area__store=store)),
                    'best_age': self.get_best_age(stats.filter(area__store=store))
                }
            }
            json_data.append(json)
        return json_data

    def process_areas(self, stats):
        json_data = []
        store = self.params.get('store')
        for area in Area.objects.filter(store=store):
            json = {
                'area': {
                    'id': area.id,
                    'name': area.name,
                    'nr_of_devices': stats.filter(area=area).annotate(Count('device', distinct=True)).count(),
                    'best_day': self.get_best_day(stats.filter(area=area)),
                    'best_age': self.get_best_age(stats.filter(area=area))
                }
            }
            json_data.append(json)
        return json_data

    def get_best_day(self, stats):
        json_aux = {}
        list = []
        for stat in stats.all():
            day = str(stat.start_time.day)
            month = str(stat.start_time.month)
            year = str(stat.start_time.year)
            date = year + '-' + month + '-' + day
            try:
                json_aux[date] = json_aux[date] + 1
            except:
                json_aux[date] = 1
                list.append(date)

        best_date_value = 0
        best_date = ''
        for index in list:
            if json_aux[index] > best_date_value:
                best_date_value = json_aux[index]
                best_date = index

        return best_date

    def get_best_age(self, stats):
        json_aux = {}
        for stat in stats.all():
            age = str(stat.device.age)
            try:
                json_aux['age'+age] = json_aux['age'+age] + 1
            except:
                json_aux['age'+age] = 1
        max = 0
        best_age = 0
        for age in range(0,150):
            try:
                if json_aux['age'+str(age)]>max:
                    max = json_aux['age'+str(age)]
                    best_age = age
            except:
                None
        return best_age