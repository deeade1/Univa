def mobile_app_settings(request):
    return {
        'MOBILE_APP_NAME': 'Univa',
        'MOBILE_APP_VERSION': '1.0.0',
        'MOBILE_API_ENDPOINT': '/graphql/',
        'MOBILE_WS_ENDPOINT': f'ws{"" if request.is_secure() else "s"}://{request.get_host()}/ws/',
    }