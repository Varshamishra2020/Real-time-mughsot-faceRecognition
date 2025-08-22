import scrapy
import re
import os
from scrapy.crawler import CrawlerProcess
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request


class RecordItem(scrapy.Item):
    state = scrapy.Field()
    county = scrapy.Field()
    city = scrapy.Field()
    person = scrapy.Field()
    photos = scrapy.Field()


class RecordSpider(scrapy.Spider):
    name = "records"

    custom_settings = {
        "CONCURRENT_REQUESTS": 5,
        "DOWNLOAD_DELAY": 0.6,
        "FEED_EXPORT_ENCODING": "utf-8",
        "ITEM_PIPELINES": {
            "__main__.RecordImageHandler": 1
        },
        "IMAGES_STORE": "records_data"
    }

    def start_requests(self):
        yield scrapy.Request("http://mugshots.com/US-States/", self.parse_states)

    def parse_states(self, response):
        for link in response.xpath("//div[@style='overflow: hidden']//ul/li/a/@href").getall():
            yield response.follow(link, self.parse_counties)

    def parse_counties(self, response):
        for link in response.xpath("//div[@style='overflow: hidden']//ul/li/a/@href").getall():
            yield response.follow(link, self.parse_cities)

    def parse_cities(self, response):
        breadcrumb = response.xpath("//div[@class='category-breadcrumbs']//h1")
        state_val = breadcrumb.xpath("./a[2]/text()").get(default="NA").strip()
        county_val = breadcrumb.xpath("./a[3]/text()").get(default="NA").strip()
        city_val = breadcrumb.xpath("./span/text()").get(default="NA").strip()

        img_links = [
            x.replace("110x110", "400x800")
            for x in response.xpath("//div[@class='image']/img/@src | //div[@class='image']/img/@data-src").getall()
        ]
        labels = [x.strip() for x in response.xpath("//div[@class='label']/text()").getall()]

        for i, link in enumerate(img_links):
            person_name = labels[i] if i < len(labels) else "NA"
            yield RecordItem(
                state=state_val,
                county=county_val,
                city=city_val,
                person=person_name,
                photos=[link]
            )

        nxt = response.xpath("//a[contains(text(),'Next')]/@href").get()
        if nxt:
            yield response.follow(nxt, self.parse_cities)


class RecordImageHandler(ImagesPipeline):
    def get_media_requests(self, item, info):
        for url in item.get("photos", []):
            yield Request(
                url,
                meta={
                    "state": item.get("state", "NA"),
                    "county": item.get("county", "NA"),
                    "city": item.get("city", "NA"),
                    "person": item.get("person", "NA")
                }
            )

    def file_path(self, request, response=None, info=None, *, item=None):
        def safe_txt(val):
            return re.sub(r'[\\/*?:"<>|]', "_", val.strip())

        st = safe_txt(request.meta.get("state"))
        ct = safe_txt(request.meta.get("county"))
        cy = safe_txt(request.meta.get("city"))
        nm = safe_txt(request.meta.get("person")) + ".jpg"

        return os.path.join(st, ct, cy, nm)

    def item_completed(self, results, item, info):
        for ok, data in results:
            if ok:
                info.spider.logger.info(f"Stored: {data['path']}")
        return item


if __name__ == "__main__":
    crawler = CrawlerProcess()
    crawler.crawl(RecordSpider)
    crawler.start()
