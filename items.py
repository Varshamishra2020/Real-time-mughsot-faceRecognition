import scrapy


class RecordItem(scrapy.Item):
    state = scrapy.Field()
    county = scrapy.Field()
    city = scrapy.Field()
    person = scrapy.Field()
    photos = scrapy.Field()
    stored = scrapy.Field()
