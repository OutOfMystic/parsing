from typing import NamedTuple, Optional, Union
import datetime
import calendar
import json

from dateutil import relativedelta

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class CskaSportstar(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://cska.sportstar.me/graphql'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        json_data = await self._requests_to_events()

        events = self._get_events_from_json_data(json_data)

        return self._parse_events_from_soup(events)

    def _parse_events_from_soup(self, events: list[dict]) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: dict) -> Optional[Union[OutputEvent, None]]:
        title = event['title'].replace('ПФК ', '').replace('ФК ', '')

        date = event['startDate']
        date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ') + datetime.timedelta(hours=3)
        normal_date = f'{date.day} {month_list[int(date.month)]} {date.year} {date.hour}:{date.minute}'

        event_id = event['id']
        href = f'https://cska.sportstar.me/tickets/{event_id}'

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_json_data(self, json_data: json) -> list[dict]:
        events = json_data['data']['allEvents']['edges']
        return events

    async def _requests_to_events(self) -> json:
        headers = {
            'Accept-Language': 'ru,en;q=0.9',
            'Connection': 'keep-alive',
            'Origin': 'https://cska.sportstar.me',
            'Referer': 'https://cska.sportstar.me/tickets',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': self.user_agent,
            'accept': '*/*',
            'content-type': 'application/json',
            'sec-ch-ua': '"Chromium";v="118", "YaBrowser";v="23.11", "Not=A?Brand";v="99", "Yowser";v="2.5"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'x-locale': 'ru',
        }
        start_date = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + relativedelta.relativedelta(months=1)
        _, max_day_in_month = calendar.monthrange(end_date.year, end_date.month)
        end_date = end_date.replace(day=max_day_in_month)
        start_date = datetime.datetime.timestamp(start_date)
        end_date = datetime.datetime.timestamp(end_date)
        start_date = str(int(start_date)) + '001'
        end_date = str(int(end_date)) + '001'
        payload = '{\"query\":\"query allEvents($query: DefaultQueryInput) {\\n  allEvents(query: $query) {\\n    ...eventConnection\\n    __typename\\n  }\\n}\\n\\nfragment eventConnection on EventConnection {\\n  total\\n  limit\\n  cursor\\n  sortable\\n  edges {\\n    ...eventFull\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment eventFull on Event {\\n  ...eventFlat\\n  price {\\n    ...eventPrice\\n    __typename\\n  }\\n  eventType {\\n    ...eventType\\n    __typename\\n  }\\n  tournamentMatch {\\n    ...tournamentMatch\\n    __typename\\n  }\\n  loyaltyDiscount {\\n    ...loyaltyDiscount\\n    __typename\\n  }\\n  promo {\\n    ...loyaltyPromo\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment eventFlat on Event {\\n  id\\n  image\\n  state\\n  title\\n  eventTypeId\\n  eventPlaceId\\n  description\\n  saleStartDate\\n  saleFinishDate\\n  startDate\\n  finishDate\\n  availableSlots\\n  saleLimit\\n  parkings\\n  isFanIdRequired\\n  __typename\\n}\\n\\nfragment eventPrice on EventPrice {\\n  value\\n  discountValue\\n  __typename\\n}\\n\\nfragment eventType on EventType {\\n  id\\n  name\\n  description\\n  image\\n  templates\\n  __typename\\n}\\n\\nfragment tournamentMatch on TournamentMatch {\\n  ...tournamentMatchFlat\\n  team1 {\\n    ...tournamentTeamSmall\\n    __typename\\n  }\\n  team2 {\\n    ...tournamentTeamSmall\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment tournamentMatchFlat on TournamentMatch {\\n  id\\n  team1Id\\n  team2Id\\n  result\\n  team1IdGoals\\n  team2IdGoals\\n  state\\n  stadiumName\\n  stadiumAddress\\n  startDate\\n  startTime\\n  finishDate\\n  startedAt\\n  finishedAt\\n  __typename\\n}\\n\\nfragment tournamentTeamSmall on TournamentTeam {\\n  id\\n  name\\n  logo\\n  website\\n  __typename\\n}\\n\\nfragment loyaltyDiscount on LoyaltyDiscount {\\n  order {\\n    id\\n    __typename\\n  }\\n  discountPercent\\n  __typename\\n}\\n\\nfragment loyaltyPromo on LoyaltyPromo {\\n  id\\n  clientId\\n  name\\n  description\\n  imageUri\\n  state\\n  amount\\n  currencyId\\n  code\\n  codeType\\n  codesCount\\n  startDate\\n  finishDate\\n  promoCodeStartDate\\n  promoCodeFinishDate\\n  discountMaxAmount\\n  discountPercent\\n  createdAt\\n  updatedAt\\n  __typename\\n}\\n\",\"variables\":{\"query\":{\"filters\":[{\"field\":\"eventTypeId\",\"value\":\"[2,1]\"},{\"value\":\"' + f'[{start_date}, {end_date}]' + '\",\"field\":\"startDate\",\"isRange\":true}],\"sort\":[{\"direction\":\"ASC\",\"field\":\"startDate\"}]}}}'
        
        r = await self.session.post(self.url, data=payload, headers=headers)
        return r.json()

    async def body(self):
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
