from app.main import app


def test_critical_route_surface_is_registered():
    paths = {route.path for route in app.routes}
    expected = {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/sessions",
        "/api/v1/vehicles/search",
        "/api/v1/quotes",
        "/api/v1/bookings",
        "/api/v1/kyc/cases",
        "/api/v1/payments/webhooks/sandbox",
        "/api/v1/support/tickets",
    }
    assert expected.issubset(paths)
