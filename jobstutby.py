#!/usr/bin/python3
import logging
import configparser
import os
import requests
import datetime
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
                time = int(time_str) + 1
        return time

    def auth(self):
        """
        Аутеризация на сайте
        """

        logger.info('Auth in jobs.tut.by')

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
        logger.info('Get resume list')
        url = 'http://jobs.tut.by/applicant/resumes'
        r = self.s.get(url)
        save_debug(r, '2_resumes_list')

    def check_time(self, resume_id):
        """
        Проверка возможности обновления резюме. Время в секундах
        """
        logger.info('Check resume time id:%s' % resume_id)
        time = 0
        url = 'http://jobs.tut.by/resume/%s' % resume_id
        r = self.s.get(url)
        save_debug(r, '4_time_update_%s' % resume_id)
        if r.status_code == 200:
            time = self.get_time_to_update(r.text)
            logger.info('Time to update %i id - %s' % (time, resume_id))
        return time

    def update_resume(self, resume_id):
        """
        Обновление определенного резюме
        """
        logger.debug('Check update resume id: %s' % resume_id)
        time = self.check_time(resume_id)
        if time == 0:
            logger.debug('Start update %s' % resume_id)
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
                       "Referer": "http://jobs.tut.by/resume/%s" % resume_id,
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
                logger.info('Resume updated %s' % resume_id)
                time = 14400  # 4 часа - дефолтное время обновления
            else:
                time = 300  # 5 минут ждем, если что-то не так
        return time


def save_debug(res, num_file):
    open("%spage_%s.html" % ('./debug/', num_file), 'w', -1, 'utf-8', 'ignore').write(res.text)


def start_logging(dir_path):
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

    global logger
    logger = logging.getLogger()
    file_path = "{0}{1}.log".format(dir_path, 'jobs.tut.by')
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(log_formatter)

    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--time', dest='time', help='Start time update. (-t 9:00)')
    args = parser.parse_args()
    logger.debug('Args:%s' %args)

    return args


def get_start_time(args):
    sec_to_start = 0
    try:
        str_time = args.time
        logger.info('Update will start at %s' % str_time)
    except Exception as exc:
        logger.debug('Start time not found. %s' % exc)
    else:
        if str_time:
            str_time += ':0'
            ls = [int(i) for i in str_time.split(':')][:2]
            tn = datetime.datetime.now()
            sec_to_start = (ls[0] - tn.hour) * 3600 + (ls[1] - tn.minute)*60 - tn.second
            if sec_to_start < 0:
                sec_to_start += 86400
    return sec_to_start


def main():
    dir_path = os.path.dirname(__file__) + os.path.sep

    start_logging(dir_path)

    logger.debug('Program path %s' % dir_path)
    args = parse_args()
    logger.debug('Param: %s' % args)
    start_time = get_start_time(args)
    if start_time:
        logger.info('Wait to update %s ' % str(datetime.timedelta(seconds=start_time)))
        sleep(start_time)
    config_path = dir_path + "config.ini"
    logger.info('Config path: %s' % config_path)
    config = configparser.ConfigParser()

    if os.path.exists(config_path):
        config.read(config_path)
    else:
        logger.critical('Config not exists:%s' % config_path)
        return

    name = config.get('USER', 'name', fallback='')
    passwd = config.get('USER', 'passwd', fallback='')

    ids = config.items('IDs')

    jobs_site = Site(name, passwd)
    while True:
        if not jobs_site.auth():
            logger.warn('Error auth! Try after 30 sec')
            sleep(30)  # Через 30 секунд пробуем еще раз
            continue

        min_time = 14400
        for resume_id in ids:
            new_time = jobs_site.update_resume(resume_id[1])
            min_time = min(min_time, new_time)
        logger.info('Sleep %s ' % str(datetime.timedelta(seconds=min_time)))
        sleep(min_time)


if __name__ == '__main__':
    main()
