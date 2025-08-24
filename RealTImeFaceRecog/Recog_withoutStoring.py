import os
import re
import cv2
import pickle
import time
import threading
import numpy as np
import face_recognition
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy import Request
import requests
from io import BytesIO
from PIL import Image

ENCODINGS_FILE = "encodings2.pkl"

def save_encodings(encs, person_name):
    """Append new encodings to encodings2.pkl"""
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            known_encodings, known_names = pickle.load(f)
    else:
        known_encodings, known_names = [], []

    for enc in encs:
        known_encodings.append(enc)
        known_names.append(person_name)

    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump((known_encodings, known_names), f)

    print(f"[INFO] Added {len(encs)} encoding(s) for {person_name}")


def load_encodings():
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    return [], []


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
            "__main__.RecordEncodingHandler": 1
        }
    }

    def start_requests(self):
        # You can change this to a specific state/county/city if needed
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


class RecordEncodingHandler:
    def process_item(self, item, spider):
        for url in item.get("photos", []):
            try:
                # Download image into memory
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                img = np.array(Image.open(BytesIO(resp.content)).convert("RGB"))

                # Encode faces
                encs = face_recognition.face_encodings(img)
                if not encs:
                    print(f"[WARNING] No face found in {url}")
                    continue

                # Save encodings with person's name
                person_name = item.get("person", "Unknown")
                save_encodings(encs, person_name)

            except Exception as e:
                print(f"[ERROR] Failed to process {url}: {e}")

        return item


def recognize_from_camera():
    cap = cv2.VideoCapture(0)
    last_reload = 0
    known_encodings, known_names = load_encodings()

    print("[INFO] Starting camera... Press 'q' to quit")

    while True:
        # Reload encodings every 30s
        if time.time() - last_reload > 30:
            known_encodings, known_names = load_encodings()
            print(f"[INFO] Reloaded encodings ({len(known_names)})")
            last_reload = time.time()

        ret, frame = cap.read()
        if not ret:
            break

        rgb_small = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        for face_encoding, face_loc in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
            name = "Unknown"

            if True in matches:
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                best_match_index = np.argmin(distances)
                if matches[best_match_index]:
                    name = known_names[best_match_index]

            top, right, bottom, left = [v * 4 for v in face_loc]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Live Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def run_scraper():
    process = CrawlerProcess()
    process.crawl(RecordSpider)
    process.start()


if __name__ == "__main__":
    # Start scraper in background
    threading.Thread(target=run_scraper, daemon=True).start()

    # Start real-time recognition
    recognize_from_camera()
