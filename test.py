import io

import requests
from bs4 import BeautifulSoup
import re
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from urllib.parse import urljoin
import time
import os
from tqdm import tqdm  # для прогресс-бара заргузки картинок


class Article:
    # TODO добавить индивидуальный идентификатор для каждой статьи.
    # TODO В ссылке каждой статьи он уже есть, так что нужно просто его достать

    def __init__(self, article_url, header, topic, text, tags, views, pics_number):
        self.url = article_url
        self.work_name = re.findall(r"[0-9]+[^/]+$", self.url)[0]
        self.header = header
        self.topic = topic
        self.text = text
        self.tags = tags
        self.views = views
        self.pics_number = pics_number
        self.comments = []

    def get_comments(self):
        """
        Цитаты включены в текст комментария. Ветки комментариев не обрабатываются

        :return:
        """
        # TODO сделать так, чтобы картинки заменялись на что-нибудь вроде "KARTINKA"
        # TODO это нужно, чтобы понимать какие комменты содержат картинки
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')
        comments_block = soup.find("div", {"class": "comments__body"})
        comments_text = [elem.getText() for elem in comments_block.find_all("p")]
        self.comments.extend([comment.replace("\n", " ") for comment in comments_text])

    def __str__(self):
        return "Название: {0}\nПросмотров: {1}\nТэги: {2}\nКартинок: {3}".format(
            self.header, self.views, self.tags, self.pics_number)


def get_article_data(target_url: str):
    response = requests.get(target_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    header = soup.find("h1", {"class": "content-title"})
    if header is not None:
        try:
            header.span.span.decompose()  # удаляем из заголовка строчку "Статьи редакции", если такая имеется
        except AttributeError:
            pass
        header = header.getText().strip()
    else:
        header = ""

    topic = soup.find("div", {"class": "content-header-author__name"}).getText().strip()
    main_text = soup.find("div", {"class": "content content--full"})
    views = "".join(main_text.find("span", {"class": "views__value"}).getText().split())
    pics_number = len(main_text.findAll("figure", {"class": "figure-image"}))
    for tag in main_text.select("textarea"):
        tag.decompose()

    main_text = [" ".join(block.getText().strip().split()) for block in
                 soup.find("div", {"class": "content content--full"}).findAll("div", {"class": "l-island-a"})]

    # preamble = main_text[0]
    # views = "".join(re.findall('[0-9]+', main_text[1]))
    tags = " ".join(re.findall(r"#[\S]+", main_text[-1]))
    # print(main_text)
    return Article(target_url, header, topic, main_text, tags, views, pics_number)


def get_all_links_by_class(target_url: str, tag_a_class: str):
    opts = Options()
    opts.headless = True
    assert opts.headless

    browser = Firefox(options=opts)
    browser.get(target_url)
    browser.execute_script("window.scrollTo(0, 14550)")  # листаем ленту вниз, чтобы прогрузилось больше новостей
    time.sleep(3)
    links = [elem.get_attribute("href") for elem in browser.find_elements(By.CLASS_NAME, tag_a_class)]
    browser.close()
    return links


# адрес обработки
url = 'https://dtf.ru/'
# корневой адрес сайта
base_url = re.match(r'^(http:\/\/|https:\/\/)?[^\/: \n]*', url).group()

download_dir = os.path.join(os.getcwd(), "comments")
try:
    os.mkdir(download_dir)
except FileExistsError:
    pass


print("Формирую список статей...")
content_links = get_all_links_by_class(url, "content-link")
articles = []

try:  # TODO повторяющийся код...
    processed_links_file = open("processed_links.txt", "a")
    processed_links_list = processed_links_file.read()
except io.UnsupportedOperation:
    processed_links_file = open("processed_links.txt", "w")
    processed_links_list = ""
for link in tqdm(content_links):
    if link not in processed_links_list:
        articles.append(get_article_data(link))
        processed_links_file.write(link + "\n")
processed_links_file.close()

print("Начинаю обрабатывать комментарии...")
for article in tqdm(articles):
    article.get_comments()
    with open(os.path.join(download_dir, article.work_name)+ '.txt', "w") as output:
        output.write("Заголовок: {}\nПросмотров: {}\nТеги:{}\n".format(article.header, article.views, article.tags))
        for comment in article.comments:
            output.write(comment + "\n")
