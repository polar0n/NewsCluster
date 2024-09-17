import asyncio
import aiohttp


async def main():

    async with aiohttp.ClientSession() as session:
        async with session.get('https://edition.cnn.com/2023/01/31/tennis/atp-alexander-zverev-domestic-abuse-spt-intl/index.html') as response:

            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.text()
            print("Body:", html[:15], "...")
            with open('article.html', 'w', encoding="utf-8") as f:
                f.write(html)

asyncio.run(main())
