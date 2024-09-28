from os import system
import logging
import asyncio
import aiohttp
import aiofiles
import aiohttp.client_exceptions
import nltk
from nltk.corpus import stopwords
# from nltk.corpus import wordnet as wn
import json
from yarl import URL
from bs4 import BeautifulSoup


CONTRACTION_MAPPING = {
    "don't": "do not",
    "can't": "cannot",
    "won't": "will not",
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "he'll": "he will",
    "he's": "he is",
    "she's": "she is",
    "it's": "it is",
    "they're": "they are",
    "they'll": "they will",
    "we're": "we are",
    "we'll": "we will",
    "you're": "you are",
}

STOPWORDS = set(stopwords.words('english'))

URLFILENAME = 'diff-urls.txt'

URLS_LENGTH = 28

# nltk.download('punkt_tab')
nltk.download('universal_tagset')
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('stopwords')
# nltk.download('wordnet')


class ProcessArticles:
    def __init__(self,
                 urlfilename:str,
                 url_record_part:int,
                 save_html:bool=True, 
                 skip:int=0, 
                 max_coroutines:int=5, 
                 log:bool=True):
        self.urlfilename = urlfilename
        self.save_html = save_html
        self.skip = skip
        self.url_record_part = url_record_part
        self.failures = list()
        self.processing_tasks = set()
        self.writer_tasks = set()
        self.current_url_index = 0
        self.max_coroutines = max_coroutines
        self.completed = 0
        self.eof = False
        self.end_future = None
        self.http_session = None
        self.urlfile = None
        if log:
            logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')
        logging.info('Initialization of ProcessArticles complete.')


    async def process_urls(self):
        # The result of this asyncio Future is set when all the processing coroutine finished executing
        self.end_future = asyncio.get_event_loop().create_future()

        self.http_session = await create_session()

        self.urlfile = open(self.urlfilename, 'r', encoding='utf-8')

        update_progress(self.completed, URLS_LENGTH)

        # Create 5 initial tasks
        for _ in range(self.skip):
            url = self.urlfile.readline()
            if url == '':
                # This should not happen
                return
        for _ in range(self.max_coroutines):
            url = self.urlfile.readline()
            if url == '':
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
        url = URL(url)
        try:
            if self.http_session.closed:
                return
            logging.info(f'Accessing {url=}')
            response = await self.http_session.get(url)
        except aiohttp.client_exceptions.InvalidUrlClientError as e:
            logging.warning(f'Cannot access {url=}')
            return
        else:
            logging.info(f'Successfully accessed {url=}')

        if response.status != 200:
            logging.warning(f'Response [{response.status}] for {url=}')
            self.failures.append([url, f'Response status: [{response.status}]'])
            return

        html = await response.text(encoding='utf-8')
        soup = BeautifulSoup(html, 'lxml')

        if self.save_html:
            self.write_file(f'articles/{url.parts[-self.url_record_part]}.html', html)

        paragraphs = str()
        for paragraph in soup.find_all(class_='paragraph'):
            text = str(paragraph.text).lower()
            paragraphs += text

        tokens = nltk.tokenize.TreebankWordTokenizer().tokenize(text)

        expanded_tokens = tokens
        for i in range(len(tokens)):
            if tokens[i] in CONTRACTION_MAPPING.keys():
                expanded_tokens[i] = CONTRACTION_MAPPING[tokens[i]]

        tokens = [word for word in expanded_tokens if word not in STOPWORDS]

        nouns = list()
        for (word, pos) in nltk.pos_tag(tokens):
            if pos == 'NN' and word.isalpha() and len(word) > 2:
                insertion = word
                if '.' in insertion:
                    insertion.replace('.', '')
                nouns.append(word)

        self.write_file(
            f'nouns/{url.parts[-self.url_record_part]}.json',
            json.dumps(nouns, indent=2)
        )


    def write_file(self, filename:str, s:str):
        writer_task = asyncio.create_task(self.aio_write(filename, s))
        self.writer_tasks.add(writer_task)
        writer_task.add_done_callback(self.writer_tasks.discard)


    async def aio_write(self, filename:str, s:str):
        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            logging.info(f'Writing to file: {filename}')
            await file.write(s)


    def task_finish(self, finished_task: asyncio.Task):
        self.completed += 1
        update_progress(self.completed, URLS_LENGTH)
        # Remove the task from tasks list
        self.processing_tasks.discard(finished_task)

        url = ''
        if not self.eof:
            # If end of file not reached yet, read a new line
            url = self.urlfile.readline()

        if url == '':
            # If the read line is '' then the reader reached the EOF
            self.eof = True
        else:
            # If EOF not reached then process the url
            task = asyncio.create_task(self.process_url(url[:-1]))
            self.processing_tasks.add(task)
            task.add_done_callback(self.task_finish)
        if self.eof and not self.processing_tasks:
            # If EOF reached and all the urls were processed then set the result of end_future to stop blocking
            # the self.process_urls function.
            self.end_future.set_result(True)


    async def _close(self):
        # for task in self.writer_tasks.union(self.processing_tasks):
        #     task.set_result(True)
        await self.http_session.close()
        await asyncio.sleep(0.250)
        self.urlfile.close()


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
    processor = ProcessArticles('diff-urls.txt', 2)
    asyncio.run(processor.process_urls())
except KeyboardInterrupt:
    print('Keyboard Interrupt')
    asyncio.run(processor._close())
