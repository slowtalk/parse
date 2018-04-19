import gc
import json
import yaml
import requests

from libsanctions import Source, Entity
from libsanctions.model import session

NAME = 'master'
YAML_URL = 'https://raw.githubusercontent.com/opensanctions/opensanctions.org/master/_data/sources.yml'  # noqa
SOURCE_URL = 'http://data.opensanctions.org/v1/sources/%s/latest/%s.ijson'
IGNORE = ['master', 'everypolitician']


def load_source(source_name):
    if source_name in IGNORE:
        return
    url = SOURCE_URL % (source_name, source_name)
    res = requests.get(url, stream=True)
    if res.status_code != 200:
        return
    for line in res.iter_lines():
        data = json.loads(line)
        Entity.from_json(data)
    session.commit()
    session.remove()
    gc.collect()


def combine():
    res = requests.get(YAML_URL)
    source = Source(NAME)
    for data in yaml.load(res.content):
        source_name = data.get('slug')
        source.log.info("Combine [%(slug)s]: %(title)s", data)
        load_source(source_name)
    source.finish()


if __name__ == '__main__':
    combine()
