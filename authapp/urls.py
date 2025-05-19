from django.urls import path
from .views import RegisterView, UploadFileView, login_form, register_form, home_view

urlpatterns = [
    path("register/", register_form, name="register_form"),
    path("api/register/", RegisterView.as_view(), name="api_register"),
    path("login/", login_form, name="login_form"),
    path("home/", home_view, name="home"),
    path("api/upload/", UploadFileView.as_view()),
]