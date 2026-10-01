# serializers.py
class ServiceRequestSerializer(serializers.ModelSerializer):
    structured_data = serializers.SerializerMethodField()

    def get_structured_data(self, obj):
        return {
            "@context": "https://schema.org",
            "@type": "Service",
            "serviceType": obj.get_service_type_display(),
            "provider": {
                "@type": "Organization",
                "name": "Your Company"
            },
            "areaServed": obj.get_service_area()
        }