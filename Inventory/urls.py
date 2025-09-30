"""
URL configuration for Inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("logout/", logout_view, name="logout"),
    path("", dashboard, name="dashboard"),
    path("notifications/", notifications_page, name="notifications"),
    path(
        "notifications/read/<int:notification_id>/",
        mark_notification_as_read,
        name="mark_notification_read",
    ),
    path("inventory/", inventory_page, name="inventory"),
    path("sales/", sales, name="sales"),
    path("sales/add/", add_sale, name="add_sale"),
    path("suppliers/", suppliers_list, name="suppliers_list"),
    path("profile/", profile_view, name="profile"),
    path("api/notifications/", get_notifications, name="get_notifications"),
    path("api/add/", add_product, name="add_product"),
    path("api/update/<int:product_id>/", update_product, name="update_product"),
    path("api/delete/<int:product_id>/", delete_product, name="delete_product"),
    path(
        "inventory/api/get-product/<int:product_id>/", get_product, name="get_product"
    ),
    path("suppliers/add/", add_supplier, name="add_supplier"),
    path(
        "suppliers/update/<int:supplier_id>/", update_supplier, name="update_supplier"
    ),
    path(
        "suppliers/delete/<int:supplier_id>/", delete_supplier, name="delete_supplier"
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
