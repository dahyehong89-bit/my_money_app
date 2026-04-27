from django.urls import path
from . import views

urlpatterns = [
    # 로그인
    path("login/", views.simple_login, name="simple_login"),
    path("logout/", views.simple_logout, name="simple_logout"),

    # 메인 페이지
    path("", views.index, name="index"),
    path("living/", views.living, name="living"),

    # 기능
    path("delete/<int:pk>/", views.delete_transaction, name="delete_transaction"),
    path("check/<int:pk>/", views.toggle_checklist, name="toggle_checklist"),

    # API
    path("api/memo/", views.memo_list),
    path("api/memo/<int:id>/", views.memo_detail),
]