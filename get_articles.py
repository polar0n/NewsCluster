import aiohttp
from bs4 import BeautifulSoup
import asyncio
import json
from yarl import URL


URLS = [
    'https://edition.cnn.com/article/sitemap-2023-1.html',
    'https://edition.cnn.com/article/sitemap-2023-2.html',
    'https://edition.cnn.com/article/sitemap-2023-3.html',
    'https://edition.cnn.com/article/sitemap-2023-4.html',
    'https://edition.cnn.com/article/sitemap-2023-5.html',
    'https://edition.cnn.com/article/sitemap-2023-6.html',
    'https://edition.cnn.com/article/sitemap-2023-7.html',
    'https://edition.cnn.com/article/sitemap-2023-8.html',
    'https://edition.cnn.com/article/sitemap-2023-9.html',
    'https://edition.cnn.com/article/sitemap-2023-10.html',
    'https://edition.cnn.com/article/sitemap-2023-11.html',
    'https://edition.cnn.com/article/sitemap-2023-12.html'
]

URLS = map(lambda url: URL(url), URLS)

async def main():

    articles = list()

    async with aiohttp.ClientSession() as session:
        for url in URLS:
            async with session.get(url) as response:
                html = await response.text()
                print(url)

                soup = BeautifulSoup(html, 'lxml')
                for element in soup.select('.sitemap-entry ul li'):
                    href = element.a.get('href')
                    active_url = URL(href)
                    if active_url.parts[-3] == 'live-news':
                        continue
                    article = list()
                    article.append(element.find(class_='date').text)
                    article.append(element.a.text)
                    article.append(href)
                    article.append(active_url.parts[-2])
                    article.append(active_url.parts[-3])
                    articles.append(article)

    articles = sorted(articles, key=lambda article: article[3])
    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2)

asyncio.run(main())
