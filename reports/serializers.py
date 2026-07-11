from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CrimeType, Evidence, Report, ReportTimeline
from .validators import (
    validate_coordinate,
    validate_description,
    validate_evidence_file,
    validate_evidence_file_count,
)

User = get_user_model()


class CrimeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrimeType
        fields = ('id', 'name', 'slug', 'description', 'is_active')


class ReportCreateSerializer(serializers.ModelSerializer):
    crime_type = serializers.SlugRelatedField(slug_field='name', queryset=CrimeType.objects.all())
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Report
        fields = (
            'id',
            'tracking_code',
            'crime_type',
            'description',
            'incident_datetime',
            'address',
            'latitude',
            'longitude',
            'anonymous',
            'status',
            'priority',
            'reporter',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'tracking_code', 'status', 'reporter', 'created_at', 'updated_at')

    def validate_description(self, value):
        validate_description(value)
        return value

    def validate_latitude(self, value):
        validate_coordinate('latitude', value)
        return value

    def validate_longitude(self, value):
        validate_coordinate('longitude', value)
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        anonymous = attrs.get('anonymous', False)
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            if not anonymous:
                raise serializers.ValidationError({
                    'anonymous': 'Authentication is required to submit a non-anonymous report.'
                })
            return attrs

        if anonymous:
            attrs['reporter'] = user
            attrs['anonymous'] = True
        else:
            attrs['reporter'] = user
            attrs['anonymous'] = False

        return attrs


class ReportSerializer(serializers.ModelSerializer):
    crime_type = serializers.SlugRelatedField(slug_field='name', read_only=True)
    crime_type_id = serializers.IntegerField(source='crime_type.id', read_only=True)

    class Meta:
        model = Report
        fields = (
            'id',
            'tracking_code',
            'crime_type',
            'crime_type_id',
            'description',
            'incident_datetime',
            'address',
            'latitude',
            'longitude',
            'anonymous',
            'status',
            'priority',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'tracking_code', 'created_at', 'updated_at', 'crime_type', 'crime_type_id')

    def validate_description(self, value):
        validate_description(value)
        return value

    def validate_latitude(self, value):
        validate_coordinate('latitude', value)
        return value

    def validate_longitude(self, value):
        validate_coordinate('longitude', value)
        return value


class ReportTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTimeline
        fields = ('id', 'status', 'note', 'updated_by', 'created_at')
        read_only_fields = ('id', 'created_at')


class EvidenceSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    file_type = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = Evidence
        fields = ('id', 'file', 'file_type', 'mime_type', 'file_size', 'uploaded_at')
        read_only_fields = ('id', 'file_type', 'mime_type', 'file_size', 'uploaded_at')

    def validate_file(self, value):
        validate_evidence_file(value)
        validate_evidence_file_count(self.context['report'])
        return value

    def create(self, validated_data):
        report = self.context['report']
        upload = validated_data.pop('file')
        validated_data['report'] = report
        validated_data['file'] = upload
        validated_data['file_type'] = Evidence.get_file_type(upload.name)
        validated_data['mime_type'] = upload.content_type or 'application/octet-stream'
        validated_data['file_size'] = upload.size
        return super().create(validated_data)
