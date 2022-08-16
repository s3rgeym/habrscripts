#!/usr/bin/env python

import argparse
import random
import time
from http.cookies import SimpleCookie
from typing import Any, Literal, TypedDict

import requests


# {
#     "id": 1000105710,
#     "href": "/vacancies/1000105710",
#     "title": "Backend developer (Python)",
#     "isMarked": true,
#     "remoteWork": true,
#     ...
#     "employment": "full_time",
#     "salary": {
#         "from": null,
#         "to": null,
#         "currency": null,
#         "formatted": ""
#     },
#     ...
#     "archived": false,
#     ...
# }
class Vacancy(TypedDict):
    id: int
    href: str
    title: str
    remoteWork: bool
    ...


# {
#     "totalResults": 591,
#     "perPage": 25,
#     "currentPage": 2,
#     "totalPages": 24
# }
class PaginationInfo(TypedDict):
    totalResults: int
    perPage: int
    currentPage: int
    totalPages: int


class Vacancies(TypedDict):
    list: list[Vacancy]
    meta: PaginationInfo


CSRFHeaders = TypedDict('CSRFHeaders', {'Referer': str, 'X-CSRF-Token': str})


def get_csrf_headers(r: requests.Response) -> CSRFHeaders:
    csrf_token = r.text.split('<meta name="csrf-token" content="')[1]
    csrf_token, *_ = csrf_token.split('" />')
    return {
        'Referer': r.url,
        'X-CSRF-Token': csrf_token,
    }


def get_vacancies(
    session: requests.Session, page: int, query: str = None
) -> Vacancies:
    r = session.get(
        'https://career.habr.com/vacancies',
        params=dict(q=query, page=page, type='suitable'),
    )
    headers = get_csrf_headers(r)
    # https://career.habr.com/api/frontend/vacancies?q=python&sort=relevance&type=suitable&currency=RUR&page=3
    # Object.fromEntries(new URLSearchParams('q=python&sort=relevance&type=suitable&currency=RUR&page=3').entries())
    # {q: 'python', sort: 'relevance', type: 'suitable', currency: 'RUR', page: '3'}
    params = {
        "q": query,
        "sort": "relevance",
        "type": "suitable",
        "currency": "RUR",
        "page": page,
    }
    r = session.get(
        'https://career.habr.com/api/frontend/vacancies',
        params=params,
        headers=headers,
    )
    return r.json()


class ApiError(TypedDict):
    error: Any
    ...


class ForceMultipartDict(dict):
    def __bool__(self):
        return True


class Result(TypedDict):
    response: dict[str, Any]


def send_job_application(
    session: requests.Session, path: str, message: str
) -> ApiError | Result:
    r = session.get(f'https://career.habr.com{path}')
    # if not ('name="body"' in r.text):
    #     return False
    headers = get_csrf_headers(r)
    print(headers)
    endpoint = f'https://career.habr.com/api/frontend{path}/responses'
    r = session.post(
        endpoint,
        data={'body': message},
        files=ForceMultipartDict(),
        headers=headers,
    )
    return r.json()


def do_spam(
    session: requests.Session,
    query: str,
    contact: str,
    page: int = 1,
) -> None:
    r = get_vacancies(session, page, query)
    for v in r['list']:
        vacancy: str = v['title'].split('(')[0].strip()
        greeting: str = random.choice(
            ['Здравствуйте', 'Доброго времени суток', 'Приветствую']
        )
        message = f"{greeting}, я бы хотел чтобы Вы рассмотрели мою кандидатуру в качестве {vacancy}. Если Вас заинтересовало мое резюме, пожалуйста свяжитесь со мной с помощью {contact}, т.к. уведомления с сайта часто теряются среди множества писем в ящике. Спасибо."
        result = send_job_application(session, v['href'], message):
        print(result)
        if error := result.get('error', {}):
            if error.get('type') == 'captcha':
                input(
                    f"Перейди по ссылке и кликни по капче: https://career.habr.com{v['href']}"
                )
                time.sleep(11)
        elif 'response' in result:
            time.sleep(11)
    if page < r['meta']['totalPages']:
        do_spam(session, query, contact, page + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description='Spam Job Application')
    parser.add_argument(
        '-c',
        '--cookie',
        help='client cookies. see devtools network tab',
        required=True,
    )
    parser.add_argument(
        '--contact',
        help='your any contact like telegram',
        required=True,
    )
    parser.add_argument('-q', '--query', help='search vacancy query')
    parser.add_argument(
        '-u',
        '--user-agent',
        help='http user agent',
        default='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36',
    )
    args = parser.parse_args()
    session = requests.session()
    session.headers.setdefault('User-Agent', args.user_agent)
    cookie = SimpleCookie()
    cookie.load(args.cookie)
    cookies = {k: v.value for k, v in cookie.items()}
    requests.utils.add_dict_to_cookiejar(session.cookies, cookies)
    # {'message': 'Можно оставлять не более 30 откликов в месяц'}
    do_spam(session, args.query, args.contact)


if __name__ == '__main__':
    main()
