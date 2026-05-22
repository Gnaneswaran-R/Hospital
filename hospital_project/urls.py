from django.contrib import admin
from django.urls import path, include
from details.views import logout_view, StyledLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', StyledLoginView.as_view(), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('details.urls')),
]
