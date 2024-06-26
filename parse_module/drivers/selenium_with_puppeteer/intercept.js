const puppeteer = require('puppeteer');

// Получение аргументов командной строки
const targetUrl = process.argv[2];
const searchPhrases = JSON.parse(process.argv[3]);
const port = process.argv[4];
const debug = process.argv[5] === 'true';

(async () => {
    try {
        if (debug) console.log("Connecting to the browser...");
        // Подключение к уже запущенному браузеру Chrome
        const browser = await puppeteer.connect({
            browserURL: `http://localhost:${port}`  // Порт для удаленной отладки Chrome
        });

        const pages = await browser.pages();
        const page = pages[0];  // Предполагаем, что первая страница - это та, которую открыл Selenium

        if (debug) console.log("Enabling request interception...");
        // Включение перехвата запросов
        await page.setRequestInterception(true);

        const responses = [];

        page.on('request', request => {
            if (debug) console.log(`Request URL: ${request.url()}`);
            request.continue();
        });

        page.on('response', async response => {
            try {
                const url = response.url();
                if (searchPhrases.length === 0 || searchPhrases.some(phrase => url.includes(phrase))) {
                    const status = response.status();
                    const headers = response.headers();
                    const body = await response.text();
                    responses.push({ url, status, headers, body });
                    if (debug) console.log(`Response URL: ${url}`);
                }
            } catch (error) {
                console.error('Error capturing response:', error);
            }
        });

        if (debug) console.log(`Navigating to ${targetUrl}...`);
        await page.goto(targetUrl);

        if (debug) console.log("Waiting for requests...");
        // Увеличение времени для перехвата запросов
        await new Promise(resolve => setTimeout(resolve, 15000)); // Ждем 15 секунд

        await browser.disconnect();
        if (debug) console.log("Disconnected from the browser.");

        // Запись результатов в stdout
        process.stdout.write(JSON.stringify(responses, null, 2));
    } catch (error) {
        console.error('Error:', error);
        process.stderr.write(`Error: ${error}\n`);
    }
})();
