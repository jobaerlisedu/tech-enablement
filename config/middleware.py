from urllib.parse import urlparse
from django.conf import settings
from django.http.request import validate_host

class DynamicCsrfTrustedOriginsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN')
        if origin:
            try:
                parsed_origin = urlparse(origin)
                host = parsed_origin.netloc
                
                # Strip port if present in netloc for validate_host check
                if ':' in host:
                    host_name, _ = host.split(':', 1)
                else:
                    host_name = host
                
                if host_name:
                    # Validate hostname against settings.ALLOWED_HOSTS
                    if validate_host(host_name, settings.ALLOWED_HOSTS):
                        # Safely append to CSRF_TRUSTED_ORIGINS if not already present
                        if origin not in settings.CSRF_TRUSTED_ORIGINS:
                            current_origins = list(settings.CSRF_TRUSTED_ORIGINS)
                            current_origins.append(origin)
                            settings.CSRF_TRUSTED_ORIGINS = current_origins
            except Exception:
                pass
        return self.get_response(request)
