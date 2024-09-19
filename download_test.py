from os import system
import asyncio
import aiohttp
import nltk
import json
from bs4 import BeautifulSoup
from helpers import ModifyOnAccessInteger


URLFILENAME = 'urls.txt'

URLS_LENGTH = 16

failures = list()

nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')

tasks = set()
current_url_index = ModifyOnAccessInteger(1)
# The result of this asyncio Future is set when all the processing coroutine finished executing
end_future = None
session = None
urls_file = open(URLFILENAME, 'r')


def update_progress(current: int, total: int, units:int=100):
    system('cls')
    progress = int(current / total * units)
    print(f'Articles processed: [', end='')
    for _ in range(progress):
        print('=', end='')
    for _ in range(units-progress):
        print(' ', end='')
    print(f'] {current}/{total}')


async def process_url(url: str, session: aiohttp.ClientSession):
    # print(f'Processing article {URLS.index(url)+1}/{URLS_LENGTH}')
    response = await session.get(url)
    if response.status != 200:
        failures.append(url)
        return

    soup = BeautifulSoup(
        await response.text(encoding='utf-8'), 'lxml')

    paragraphs = str()
    for paragraph in soup.find_all(class_='paragraph'):
        paragraphs += str(paragraph.text)

    tokens = nltk.tokenize.word_tokenize(paragraphs)
    nouns = list()
    for (word, pos) in nltk.pos_tag(tokens):
        if pos == 'NN' and word.isalpha() and len(word) > 1:
            nouns.append(word)

    with open(f'nouns/{response.url.parts[-2]}.json', 'w', encoding='utf-8') as f:
        json.dump(nouns, f, indent=2)


def task_finish(finished_task: asyncio.Task):
    '''Process a finished task.'''
    update_progress(int(finished_task.get_name()), URLS_LENGTH)
    # Remove the task from tasks list
    tasks.discard(finished_task)
    
    url = urls_file.readline()
    if url == '\n':
        end_future.set_result(True)

    task = asyncio.create_task(
        coro=process_url(url[:-1], session),
        name=str(current_url_index())
    )
    tasks.add(task)
    task.add_done_callback(task_finish)


async def create_session():
    return aiohttp.ClientSession()


async def main(coroutines=5):
    # The result of this asyncio Future is set when all the processing coroutine finished executing
    global end_future
    end_future = asyncio.get_event_loop().create_future()

    global session
    session = await create_session()

    # Create 5 initial tasks
    for _ in range(coroutines):
        url = urls_file.readline()
        if url == '\n':
            # This should not happen
            break
        task = asyncio.create_task(
            coro=process_url(url[:-1], session),
            name=str(current_url_index())
        )
        tasks.add(task)

    task.add_done_callback(task_finish)

    # Await the processing of all urls
    await end_future
    await session.close()


try:
    asyncio.run(main(5))
except KeyboardInterrupt:
    for task in tasks:
        task.cancel()
finally:
    urls_file.close()
