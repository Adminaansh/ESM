import time
from .aggregators import registry


class ResponseTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if not request.path.startswith("/api/monitoring/"):
            match = getattr(request, "resolver_match", None)
            key = match.route if match else "unmatched"   # route pattern, not raw URL
            try:
                registry.add(key, elapsed_ms)
            except RuntimeError:
                pass
        return response