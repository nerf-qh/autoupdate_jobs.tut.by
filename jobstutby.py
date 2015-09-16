#!/usr/bin/python3
import logging
import configparser
import os
import requests
from time import sleep

__author__ = 'shkalar'


class Site:
    """
    Работа с сайтом jobs.tut.by
    """
    def __init__(self, name, passwd):
        self.name = name
        self.passwd = passwd
        self.token = None
        self.r = None
        self.s = None
        self.resumes = []

    @staticmethod
    def get_token(text):
        token = None
        str_find = 'name="_xsrf" value="'
        poz = text.find(str_find)
        if poz:
            token = text[poz + len(str_find): text.find('"', poz + len(str_find))]

        return token

    @staticmethod
    def get_time_to_update(text):
        """
        Определение времени до обновления
        """
        time = 0
        str_find = '"toUpdate"'
        poz = text.find(str_find)
        if poz:
            poz = text.find('"', poz + len(str_find))
            time_str = text[poz + 1: text.find('"', poz + 1)]
            if time_str:
                time = int(time / 60) + 1
        return time

    def auth(self):
        """
        Аутеризация на сайте
        """
        logging.info('Auth in jobs.tut.by')

        url = 'https://jobs.tut.by/account/login'
        self.s = requests.session()
        self.s.verify = False
        self.s.allow_redirects = True

        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)\
                              Chrome/45.0.2454.85 Safari/537.36',
                   'Origin': 'http://jobs.tut.by',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4,be;q=0.2,uk;q=0.2',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                   'Content-Type': 'application/x-www-form-urlencoded',
                   'Host': 'jobs.tut.by',
                   'Referer': 'https://jobs.tut.by/account/login'
                   }
        self.s.headers.update(headers)
        self.s.options(url)
        r = self.s.get(url, headers=headers)
        save_debug(r, '0_login')
        self.token = self.get_token(r.text)
        data = {'username': self.name,
                'password': self.passwd,
                '_xsrf': self.token,
                'backUrl': 'https://jobs.tut.by/',
                'failUrl': 'https://jobs.tut.by/',
                'remember': 'yes'
                }
        r = self.s.post(url, headers=headers, data=data)
        save_debug(r, '1_auth')
        return r.status_code == 200

    def get_resume_urls(self):
        """
        Получение списка резюме пользователя
        """
        logging.info('Get resume list')
        url = 'http://jobs.tut.by/applicant/resumes'
        r = self.s.get(url)
        save_debug(r, '2_resumes_list')

    def check_time(self, resume_id):
        """
        Проверка возможности обновления резюме
        """
        logging.info('Check resume time id:%s' % resume_id)
        time = 0
        url = 'http://jobs.tut.by/resume/%s' % resume_id
        r = self.s.get(url)
        save_debug(r, '4_time_update_%s' % resume_id)
        if r.status_code == 200:
            time = self.get_time_to_update(r.text)
        return time

    def update_resume(self, resume_id):
        """
        Обновление определенного резюме
        """
        logging.info('Update resume id: %s' % resume_id)
        time = self.check_time(resume_id)
        if time == 0:
            url = 'http://jobs.tut.by/applicant/resumes/touch'
            data = {'resume': resume_id,
                    'undirectable': 'true'
                    }
            headers = {"Origin": "http://jobs.tut.by",
                       "Accept-Encoding": "gzip, deflate",
                       "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4,be;q=0.2,uk;q=0.2",
                       "X-Requested-With": "XMLHttpRequest",
                       "Connection": "keep-alive",
                       "Host": "jobs.tut.by",
                       "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)\
                        Chrome/45.0.2454.85 Safari/537.36",
                       "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                       "Accept": "text/plain, */*; q=0.01",
                       "Referer": "http://jobs.tut.by/resume/a5b5bc34ff029dc3250039ed1f4d3063333749",
                       "X-Xsrftoken": self.token
                       }
            req = requests.Request('POST',  url,
                                   data=data,
                                   headers=headers
                                   )
            prepped = self.s.prepare_request(req)
            resp = self.s.send(prepped)
            save_debug(resp, '3_update_id_%s' % resume_id)
            if resp.status_code == 200:
                time = 240
            else:
                time = 30
        return time


def save_debug(res, num_file):
    open("%spage_%s.html" % ('./debug/', num_file), 'w', -1, 'utf-8', 'ignore').write(res.text)


def main():
    dir_path = os.path.dirname(__file__) + os.path.sep

    logging.basicConfig(filename=dir_path + 'jobs.tut.by.log',
                        filemode='a',
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    config_path = dir_path + 'config.ini'

    logging.info('Config path: %s' % config_path)
    config = configparser.ConfigParser()

    if os.path.exists(config_path):
        config.read(config_path)
    else:
        print('Config not exists:%s' % config_path)
        logging.critical('Config not exists:%s' % config_path)
        return

    name = config.get('USER', 'name', fallback='')
    passwd = config.get('USER', 'passwd', fallback='')

    ids = config.items('IDs')

    jobs_site = Site(name, passwd)
    while True:
        if not jobs_site.auth():
            logging.critical('Error auth!')
            sleep(30)  # Через 30 секунд пробуем еще раз
            continue

        min_time = 60
        for resume_id in ids:
            new_time = jobs_site.update_resume(resume_id[1])
            min_time = min(min_time, new_time)
        sleep(min_time * 60)


if __name__ == '__main__':
    main()
