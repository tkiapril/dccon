""":mod:`dccon.dccon` --- library main source file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

#!/usr/bin/env python3
from enum import Enum
from io import BytesIO
from json import loads
from pathlib import Path
from urllib.parse import quote_plus

from lxml.html import document_fromstring
from PIL import Image
from requests import Session


class list_order(Enum):
    hot = 'hot'
    new = 'new'


class search_condition(Enum):
    title = 'title'
    nick_name = 'nick_name'
    tags = 'tags'


class dccon:
    '''Be aware of cache memory size.'''

    def __init__(self, session=None):
        if not session:
            session = Session()
        session.get('http://dccon.dcinside.com/')
        self.session = session
        self.reverse_list_cache = {}
        self.details_cache = {}

    def get_list(self, page, order=list_order.new):
        '''Returns a list of packages.'''
        return self.search_list(None, None, page, order)

    def search_list(self, condition, keyword, page, order=list_order.new):
        '''Returns a page of search result with search_condition.'''
        url = 'http://dccon.dcinside.com/{}/{}'.format(order.value, page)
        if keyword:
            url += '/{}/{}'.format(condition.value, quote_plus(keyword))
        result = {
            i.get('package_idx'):
            i.xpath('.//*[@class="sticker1_name"]')[0].text
            for i in document_fromstring(
                self.session.get(url).text
            ).xpath('//*[@class="div_package "]')
        }
        self.reverse_list_cache.update({v: k for k, v in result.items()})
        return result

    def get_details(self, package_idx):
        '''Get the details of a package.'''
        try:
            c = self.details_cache[package_idx]
            if c:
                return c
        except KeyError:
            pass
        detail = loads(
            self.session.post(
                'http://dccon.dcinside.com/index/package_detail',
                data={
                    'ci_t': self.session.cookies.get('ci_c'),
                    'package_idx': package_idx,
                },
                headers={'X-Requested-With': 'XMLHttpRequest'},
            ).text
        )
        self.details_cache[package_idx] = detail
        return detail

    def get_package_images(self, package_idx):
        '''Download images in a package.'''
        return {
            '{}-{}-{}.{}'.format(i['idx'], i['sort'], i['title'], i['ext']):
            self.get_image(i['path'])
            for i in self.get_details(package_idx)['detail']
        }

    def get_image(self, path):
        '''Fetch a single image from a path.'''
        return Image.open(BytesIO(self.session.get(
            'http://dcimg5.dcinside.com/dccon.php?no={}'.format(path),
            headers={'Referer': 'http://dccon.dcinside.com/'}
        ).content))

    def fix_ratio_slack(self, image_dict):
        '''
        Fix the ratio and background of the images
        for view on mobile slack.
        '''
        new_dict = {}
        for name, image in image_dict.items():
            w, h = image.size
            wide = round(h / 13 * 22) // 2 * 2
            f = Image.new('RGBA', (w + 2, h), 'lightgrey')
            f.paste(
                Image.alpha_composite(
                    Image.new('RGBA', image.size, 'white'),
                    image
                ),
                (1, 0)
            )
            f2 = Image.new('RGBA', (wide, h), 'white')
            f2.paste(f, ((wide - w) // 2, 0))
            new_dict[name] = f2
        return new_dict

    def save_package_images(self, image_dict, path=Path('.')):
        '''Save a package of images.'''
        if type(path) is str:
            path = Path(path)
        for name, image in image_dict.items():
            image.save(path / name)
