from bs4 import BeautifulSoup

soup = None

with open('article.html', encoding='utf-8') as fp:
    soup = BeautifulSoup(fp, 'lxml')

elements_with_class = soup.find_all(class_='paragraph')

with open('paragraphs.txt', 'w') as f:
    for element in elements_with_class:
        print(element.text)
        f.write(element.text)

