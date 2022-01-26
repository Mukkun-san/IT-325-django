import threading
from black import json
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from main.quizMaker import generate_mcqs
from scraper.models import Quiz
from scraper.serializers import QuizSerializer
from scraper.models import Article
from scraper.serializers import ArticleSerializer
from rest_framework.decorators import api_view
from bs4 import BeautifulSoup
import requests


@api_view(["POST"])
def scrape_article(request):
    # Scrape an article from given URL and save to DB if not already exists
    url = JSONParser().parse(request)["url"]
    print(url)
    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content, "lxml")
    title = soup.find(
        "h1",
        attrs={"class": "m-detail-header--title"},
    ).get_text()

    if Article.objects.filter(title=title).exists():
        return JsonResponse(
            {"DUPLICATE ERROR": "ARTICLE ALREADY EXISTS"},
            status=status.HTTP_409_CONFLICT,
        )
    articleEl = soup.find(
        "div",
        attrs={"class": "m-detail--body"},
    )
    content = ""
    for el in articleEl.children:
        if el.name == "p":
            content += el.get_text()
    article_serializer = ArticleSerializer(data={"title": title, "content": content})
    if article_serializer.is_valid():
        article_serializer.save()
        return JsonResponse(article_serializer.data, status=status.HTTP_201_CREATED)
    return JsonResponse(article_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def generate_quiz(request):
    title = JSONParser().parse(request)["title"]
    if not (Article.objects.filter(title=title).exists()):
        return JsonResponse(
            {"404 ERROR": "ARTICLE NOT FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    article = Article.objects.get(title=title)
    content = ArticleSerializer(article).data["content"]
    th = threading.Thread(target=generate_mcqs, args=(content, title))
    th.start()
    return JsonResponse(
        {"message": "Quiz generation have started"}, status=status.HTTP_200_OK
    )


import csv


@api_view(["POST"])
def export_quiz(request):
    try:
        print("started")
        title = JSONParser().parse(request)["title"]
        print(title)
        quiz = Quiz.objects.get(title=title)
        questions = json.loads(QuizSerializer(quiz).data["questions"])
        print(questions)
        with open(title + ".csv", "w") as f:
            writer = csv.writer(f)

            writer.writerow(["question", "answer", "options"])
            for x in questions:
                writer.writerow(
                    [x["question"], x["answer"]] + json.loads(x["distractors"])
                )

        return JsonResponse(
            {"message": "Successfully exported quiz"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
