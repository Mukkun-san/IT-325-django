from rest_framework import serializers
from scraper.models import Article, Quiz


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "title",
            "content",
            "date",
        )


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = (
            "title",
            "questions",
            "date",
        )
