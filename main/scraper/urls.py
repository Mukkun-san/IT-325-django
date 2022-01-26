from django.conf.urls import url
from scraper import views

urlpatterns = [
    url("api/scrape/article", views.scrape_article),
    url("api/generate-mcqs/from-title", views.generate_quiz),
    url("api/export-quiz/csv", views.export_quiz),
]
