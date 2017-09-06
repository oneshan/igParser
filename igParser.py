from datetime import datetime
from queue import Queue
from threading import Thread
import argparse
import csv
import os
import requests


class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            directory, url = self.queue.get()
            try:
                downloadFile(directory, url)
            except Exception as e:
                raise e
            self.queue.task_done()


def downloadFile(folder, url):
    try:
        filename = url.split('?')[0].split('/')[-1]
        data = requests.get(url, stream=True)
        with open(os.path.join(folder, filename), 'wb') as file:
            for chunk in data.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
    except Exception as e:
        raise e


def parse(account, max_id=None):
    param = '?max_id=%s' % max_id if max_id else ''
    url = 'http://instagram.com/{0}/media{1}'.format(account, param)
    media = requests.get(url).json()
    for item in media["items"]:
        url = item.get("videos", item["images"])["standard_resolution"]["url"]
        meta = dict(
            link=item["link"],
            filename=url.split('?')[0].split('/')[-1],
            created_time=None,
            text=None,
        )

        if item["caption"]:
            meta["created_time"] = item["caption"]["created_time"]
            meta["created_time"] = (datetime.fromtimestamp(float(meta["created_time"]))
                                            .strftime("%Y/%m/%d %H:%M:%S"))
            meta["text"] = item["caption"]["text"]
        yield url, meta

    if media["more_available"]:
        for url, meta in parse(account, media["items"][-1]["id"]):
            yield url, meta


def main():
    parser = argparse.ArgumentParser(description='Instagram Downloader')
    parser.add_argument('account', help='Instagram account')
    parser.add_argument('--dir', type=str, default='result', help='Directory to save file')
    args = parser.parse_args()

    queue = Queue()
    for idx in range(3):
        worker = DownloadWorker(queue)
        worker.setDaemon(True)
        worker.start()

    directory = args.dir
    if not os.path.exists(directory):
        os.makedirs(directory)

    toCSV = []
    for url, meta in parse(args.account):
        queue.put((directory, url))
        toCSV.append(meta)
        break

    if toCSV:
        print("#media of the account {}: {}".format(args.account, len(toCSV)))
        print("Start to download... ")
    else:
        print("No posts yet or it's a private account.")
        return

    keys = toCSV[0].keys()
    with open('%s.csv' % args.account, 'w') as file:
        dict_writer = csv.DictWriter(file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(toCSV)

    queue.join()


if __name__ == "__main__":
    main()
