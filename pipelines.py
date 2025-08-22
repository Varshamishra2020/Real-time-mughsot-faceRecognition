import os
import re
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request


class RecordImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        for link in item.get("photos", []):
            yield Request(
                link,
                meta={
                    "state": item.get("state", "NA"),
                    "county": item.get("county", "NA"),
                    "city": item.get("city", "NA"),
                    "person": item.get("person", "NA")
                }
            )

    def file_path(self, request, response=None, info=None, *, item=None):
        def clean(value):
            if not value:
                return "NA"
            return re.sub(r'[\\/*?:"<>|]', "_", value.strip())

        st = clean(request.meta.get("state"))
        ct = clean(request.meta.get("county"))
        cy = clean(request.meta.get("city"))
        nm = clean(request.meta.get("person")) + ".jpg"

        return os.path.join(st, ct, cy, nm)

    def item_completed(self, results, item, info):
        for success, data in results:
            if success:
                info.spider.logger.info(f"Stored: {data['path']}")
            else:
                info.spider.logger.warning(f"Image failed: {item.get('person')}")
        return item
