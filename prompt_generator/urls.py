from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Original simple generator (kept for compatibility)
    path('generate/', views.generate_prompt, name='generate_prompt'),

    # Endpoints used by the frontend tabs
    path('generate/edit/', views.generate_edit, name='generate_edit'),
    path('generate/thumbnail/', views.generate_thumbnail, name='generate_thumbnail'),
    path('generate/style/', views.generate_style, name='generate_style'),
]
