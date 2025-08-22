import random
from scrapy import signals


class RecordSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        crawler.signals.connect(inst.spider_opened, signal=signals.spider_opened)
        return inst

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for item in result:
            yield item

    def process_spider_exception(self, response, exception, spider):
        spider.logger.error(f"[SpiderMW] {spider.name} error: {exception}")
        return None

    def process_start_requests(self, start_requests, spider):
        for req in start_requests:
            yield req

    def spider_opened(self, spider):
        spider.logger.info(f"[SpiderMW] Started: {spider.name}")


class RecordDownloaderMiddleware:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:109.0) "
        "Gecko/20100101 Firefox/109.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 12; Pixel 5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
    ]

    PROXIES = [
        # "http://user:pass@proxyserver:port",
        # "http://proxyserver:port"
    ]

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        crawler.signals.connect(inst.spider_opened, signal=signals.spider_opened)
        return inst

    def process_request(self, request, spider):
        ua = random.choice(self.USER_AGENTS)
        request.headers["User-Agent"] = ua

        if self.PROXIES:
            proxy = random.choice(self.PROXIES)
            request.meta["proxy"] = proxy
            spider.logger.debug(f"[DownloaderMW] Proxy: {proxy}")

        spider.logger.debug(f"[DownloaderMW] URL: {request.url} | UA: {ua}")
        return None

    def process_response(self, request, response, spider):
        if response.status != 200:
            spider.logger.warning(f"[DownloaderMW] Status {response.status} @ {request.url}")
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f"[DownloaderMW] Exception {request.url}: {exception}")
        return None

    def spider_opened(self, spider):
        spider.logger.info(f"[DownloaderMW] Started: {spider.name}")
