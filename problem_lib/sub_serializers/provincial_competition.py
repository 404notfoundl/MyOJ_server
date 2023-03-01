from rest_framework import serializers
from .. import models


class ProvincialCompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.provincial_competition.ProvincialCompetitionList
        fields = '__all__'
