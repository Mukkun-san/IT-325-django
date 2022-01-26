from summarizer import Summarizer
import pke
import string
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
from flashtext import KeywordProcessor
import requests
from nltk.corpus import wordnet as wn


def get_nouns_multipartite(text):
    out = []

    extractor = pke.unsupervised.MultipartiteRank()
    extractor.load_document(input=text)
    pos = {"PROPN", "ADJ", "NOUN"}
    stoplist = list(string.punctuation)
    stoplist += ["-lrb-", "-rrb-", "-lcb-", "-rcb-", "-lsb-", "-rsb-"]
    stoplist += stopwords.words("english")
    extractor.candidate_selection(pos=pos, stoplist=stoplist)
    extractor.candidate_weighting(alpha=1.0, threshold=0.8, method="average")
    keyphrases = extractor.get_n_best(n=20)

    for key in keyphrases:
        out.append(key[0])

    return out


def tokenize_sentences(text):
    sentences = [sent_tokenize(text)]
    sentences = [y for x in sentences for y in x]
    sentences = [sentence.strip() for sentence in sentences if len(sentence) > 20]
    return sentences


def get_sentences_for_keyword(keywords, sentences):
    keyword_processor = KeywordProcessor()
    keyword_sentences = {}
    for word in keywords:
        keyword_sentences[word] = []
        keyword_processor.add_keyword(word)
    for sentence in sentences:
        keywords_found = keyword_processor.extract_keywords(sentence)
        for key in keywords_found:
            keyword_sentences[key].append(sentence)

    for key in keyword_sentences.keys():
        values = keyword_sentences[key]
        values = sorted(values, key=len, reverse=True)
        keyword_sentences[key] = values
    return keyword_sentences


def get_distractors_wordnet(syn, word):
    distractors = []
    word = word.lower()
    orig_word = word
    if len(word.split()) > 0:
        word = word.replace(" ", "_")
    hypernym = syn.hypernyms()
    if len(hypernym) == 0:
        return distractors
    for item in hypernym[0].hyponyms():
        name = item.lemmas()[0].name()
        if name == orig_word:
            continue
        name = name.replace("_", " ")
        name = " ".join(w.capitalize() for w in name.split())
        if name is not None and name not in distractors:
            distractors.append(name)
    return distractors


def get_wordsense(sentence, word):
    from pywsd.similarity import max_similarity
    from pywsd.lesk import cosine_lesk

    word = word.lower()

    if len(word.split()) > 0:
        word = word.replace(" ", "_")

    synsets = wn.synsets(word, "n")
    if synsets:
        wup = max_similarity(sentence, word, "wup", pos="n")
        lesk_output = cosine_lesk(sentence, word, pos="n")
        lowest_index = min(synsets.index(wup), synsets.index(lesk_output))
        return synsets[lowest_index]
    else:
        return None


def get_distractors_conceptnet(word):
    word = word.lower()
    original_word = word
    if len(word.split()) > 0:
        word = word.replace(" ", "_")
    distractor_list = []
    url = (
        "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/PartOf&start=/c/en/%s&limit=5"
        % (word, word)
    )
    obj = requests.get(url).json()

    for edge in obj["edges"]:
        link = edge["end"]["term"]

        url2 = (
            "http://api.conceptnet.io/query?node=%s&rel=/r/PartOf&end=%s&limit=10"
            % (link, link)
        )
        obj2 = requests.get(url2).json()
        for edge in obj2["edges"]:
            word2 = edge["start"]["label"]
            if (
                word2 not in distractor_list
                and original_word.lower() not in word2.lower()
            ):
                distractor_list.append(word2)

    return distractor_list


def generate_mcqs(article_original, title):
    print("⚡ Started MCQ generation ⚡")
    model = Summarizer()
    result = model(article_original, min_length=60, ratio=0.4)
    article_summary = "".join(result)
    keywords = get_nouns_multipartite(article_original)
    filtered_keys = []
    for keyword in keywords:
        if keyword.lower() in article_summary.lower():
            filtered_keys.append(keyword)
    sentences = tokenize_sentences(article_summary)
    keyword_sentence_mapping = get_sentences_for_keyword(filtered_keys, sentences)

    key_distractor_list = {}
    for keyword in keyword_sentence_mapping:
        wordsense = get_wordsense(keyword_sentence_mapping[keyword][0], keyword)
        if wordsense:
            distractors = get_distractors_wordnet(wordsense, keyword)
            if len(distractors) == 0:
                distractors = get_distractors_conceptnet(keyword)
            if len(distractors) != 0:
                key_distractor_list[keyword] = distractors
        else:
            distractors = get_distractors_conceptnet(keyword)
            if len(distractors) != 0:
                key_distractor_list[keyword] = distractors

    from scraper.serializers import QuizSerializer

    questions = []
    for keyword in key_distractor_list:
        question = keyword_sentence_mapping[keyword][0]
        distractors = key_distractor_list[keyword]
        questions.append(
            {"question": question, "answer": keyword, "distractors": distractors}
        )
    QuizSerializer().create(
        validated_data={
            "title": title,
            "questions": questions,
        }
    )
    print("⚡ Finished MCQ generation ⚡")
