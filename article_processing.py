from os import system
import asyncio
import aiohttp
import aiofiles
import nltk
import json
from bs4 import BeautifulSoup


URLFILENAME = 'urls.txt'

URLS_LENGTH = 1000

nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')


class ProcessArticles:
    def __init__(self, urlfilename:str, save_html:bool=True, skip:int=0, coroutines:int=5):
        self.urlfilename = urlfilename
        self.save_html = save_html
        self.skip = skip
        self.failures = list()
        self.processing_tasks = set()
        self.writer_tasks = set()
        self.current_url_index = 0
        self.coroutines = 5
        self.completed = 0
        self.eof = False
        self.end_future = None
        self.http_session = None
        self.urlfile = None


    async def process_urls(self):
        # The result of this asyncio Future is set when all the processing coroutine finished executing
        self.end_future = asyncio.get_event_loop().create_future()

        self.http_session = await create_session()

        self.urlfile = open(self.urlfilename, 'r', encoding='utf-8')

        # Create 5 initial tasks
        for _ in range(self.skip):
            url = self.urlfile.readline()
            if url == '\n':
                # This should not happen
                return
        for _ in range(self.coroutines):
            url = self.urlfile.readline()
            if url == '\n':
                # This should not happen
                break
            task = asyncio.create_task(self.process_url(url[:-1]))
            self.processing_tasks.add(task)
            task.add_done_callback(self.task_finish)

        # Await the processing of all urls
        await self.end_future
        await self.http_session.close()
        self.urlfile.close()


    async def process_url(self, url:str):
        response = await self.http_session.get(url)
        if response.status != 200:
            self.failures.append(url)
            return

        html = await response.text(encoding='utf-8')
        soup = BeautifulSoup(html, 'lxml')

        if self.save_html:
            self.write_file(f'articles/{response.url.parts[-2]}.html', html)

        paragraphs = str()
        for paragraph in soup.find_all(class_='paragraph'):
            paragraphs += str(paragraph.text)

        tokens = nltk.tokenize.word_tokenize(paragraphs)
        nouns = list()
        for (word, pos) in nltk.pos_tag(tokens):
            if pos == 'NN' and word.isalpha() and len(word) > 1:
                nouns.append(word)

        self.write_file(
            f'nouns/{response.url.parts[-2]}.json',
            json.dumps(nouns, indent=2)
        )


    def write_file(self, filename:str, s:str):
        writer_task = asyncio.create_task(self.aio_write(filename, s))
        self.writer_tasks.add(writer_task)
        writer_task.add_done_callback(self.writer_tasks.discard)


    async def aio_write(self, filename:str, s:str):
        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(s)


    def task_finish(self, finished_task: asyncio.Task):
        '''Process a finished task.'''
        self.completed += 1
        update_progress(self.completed, URLS_LENGTH)
        # Remove the task from tasks list
        self.processing_tasks.discard(finished_task)

        url = '\n'
        if not self.eof:
            url = self.urlfile.readline()

        if url == '\n':
            self.eof = True
        else:
            task = asyncio.create_task(self.process_url(url[:-1]))
            self.processing_tasks.add(task)
            task.add_done_callback(self.task_finish)
        if self.eof and not self.processing_tasks:
            self.end_future.set_result(True)
            return


    async def _close(self):
        self.urlfile.close()
        await self.http_session.close()
        for task in self.writer_tasks.union(self.processing_tasks):
            task.cancel()


def update_progress(current: int, total: int, units:int=100):
    system('cls')
    progress = int(current / total * units)
    print(f'Articles processed: [', end='')
    for _ in range(progress):
        print('=', end='')
    for _ in range(units-progress):
        print(' ', end='')
    print(f'] {current}/{total}')


async def create_session():
    return aiohttp.ClientSession()


try:
    processor = ProcessArticles('urls.txt')
    asyncio.run(processor.process_urls())
except KeyboardInterrupt:
    asyncio.get_event_loop().run_until_complete(processor._close())
