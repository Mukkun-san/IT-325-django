from djongo import models
from django import forms
from django.contrib.postgres.fields import ArrayField


class Article(models.Model):
    title = models.TextField(blank=False, default="")
    content = models.TextField(blank=False, default="")
    date = models.DateTimeField(auto_now_add=True)


class Question(models.Model):
    question = models.TextField(blank=False, default="")
    answer = models.TextField(blank=False, default="")
    distractors = ArrayField(models.CharField(max_length=100, blank=True))

    class Meta:
        abstract = True


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("question", "answer", "distractors")


class Quiz(models.Model):
    title = models.TextField(blank=False, default="")
    questions = models.ArrayField(
        model_container=Question, model_form_class=QuestionForm
    )
    date = models.DateTimeField(auto_now_add=True)
