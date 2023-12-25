import itertools
import datetime as dt

import numpy as np
import pyperclip
from loguru import logger
from more_itertools import chunked

from parse_module.connection import db_manager
from parse_module.console.base import print_cols
from parse_module.utils import utils
from parse_module.utils.date import Date, month_num_by_str, encode_month

MANUAL_TABLE = False
ACQUIRINGS = {
    'Миша': 0.0315,
    'Никита': 0.0259,
    'Саша': 0.03
}
OWNER_ALIASES = {
    'Миша': 'Олегу',
    'Никита': 'Никите',
    'Саша': 'Саше С.'
}
SHARE_OWNER_NAMES = ['Влад', 'Никита', 'Саша', 'Миша', 'Олег']
PROJECTS = {
    'Большой театр': [18.7, 6.8, 6.8, 52.7, 15],
    'Ледовый дворец СКА': [22, 8, 8, 62, 0],
    'Малый театр': [22, 8, 58, 12, 0],
    'Мегаспорт': [22, 8, 58, 12, 0],
    'Театр Вахтангова': [22, 58, 8, 12, 0],
    'Театр Горького': [22, 8, 58, 12, 0],
    'Театр Ленком (Ленинского комсомола)': [22, 58, 8, 12, 0],
    'Театр Оперетты': [22, 8, 58, 12, 0],
    'Театр Сатиры': [22, 58, 8, 12, 0],
    'Театр Станиславского': [22, 58, 8, 12, 0],
    'Театр Фоменко': [22, 8, 58, 12, 0],
    'Театр Чехова': [22, 58, 8, 12, 0],
    'ЦСКА Арена': [22, 58, 8, 12, 0],
    'Цирк Никулина на Цветном бульваре': [22, 8, 8, 62, 0],
    'Цирк на Вернадского': [22, 8, 8, 62, 0],
    'ВТБ Арена': [22, 8, 8, 62, 0],
    'Татнефть Арена': [22, 8, 8, 62, 0],
    'Арена 2000': [22, 58, 8, 12, 0],
    'G-Drive Арена': [22, 58, 8, 12, 0],
    'Барвиха Luxury Village': [22, 58, 8, 12, 0]
}
MANUAL_ORDERS = {
    10658: ['Малый театр', '11 Дек 2022 18:00'],
    10597: ['Театр Ленком (Ленинского комсомола)', '28 Ноя 2022 19:00'],
    10619: ['Театр Ленком (Ленинского комсомола)', '20 Дек 2022 19:00'],
    10617: ['Театр Ленком (Ленинского комсомола)', '04 Янв 2023 19:00'],
    10609: ['Театр Ленком (Ленинского комсомола)', '06 Янв 2023 19:00'],
    10618: ['Театр Ленком (Ленинского комсомола)', '04 Янв 2023 19:00'],
    10607: ['Театр Ленком (Ленинского комсомола)', '22 Ноя 2022 19:00'],
    10635: ['Театр Ленком (Ленинского комсомола)', '06 Дек 2022 19:00'],
    10648: ['Театр Ленком (Ленинского комсомола)', '19 Ноя 2022 19:00'],
    10651: ['Театр Ленком (Ленинского комсомола)', '04 Янв 2023 19:00'],
    10746: ['Большой театр', '03 Дек 2022 19:00'],
    10759: ['Большой театр', '04 Дек 2022 19:00'],
    10592: ['Театр Ленком (Ленинского комсомола)', '23 Ноя 2022 19:00'],
    10774: ['Большой театр', '11 Янв 2023 19:00'],
    10779: ['Большой театр', '13 Янв 2023 19:00'],
    10926: ['Театр Вахтангова', '02 Янв 2023 19:00'],
    10610: ['Театр Ленком (Ленинского комсомола)', '15 Янв 2023 19:00'],
    10602: ['Театр Ленком (Ленинского комсомола)', '24 Дек 2022 19:00'],
    10632: ['Театр Ленком (Ленинского комсомола)', '17 Дек 2022 19:00']
}
MANADS_TABLE = ("Наций	Вахтангова	ВТБ Арена	Малый	Оперетты	"
                "Чехова	Мегаспорт	ЦСКА арена	Горького	Ленком ("
                "Ленинск	ФК Спартак Откр	Сатиры	Большой	Фоменко	"
                "Станиславского	Ледовый дворец	Цирк на Вернадс	Цирк"
                " Никулина н\n	229780		4986	4416	190396	"
                "13460		122079	186709		123775	231900	1225"
                "7	73614		461159	410417\n			60200	"
                "												4677"
                "9	")
SALARY_TABLE = "Янв 2023	142440\nФев 2023	443199"


class Order:
    def __init__(self, order_date, order_id, status, pay_data,
                 event_date, venue, zriteli):
        self.order_date = order_date
        self.order_id = order_id
        self.status = status
        self.pay_data = pay_data
        self.event_date = event_date
        self.venue = venue
        self.zritelit = zriteli
        
        tax = get_gross_tax(venue, order_date, status=status)
        tax_val = get_tax(venue, order_date)
        tax_val = int(tax_val * 10000) / 100
        self.tax_val = str(tax_val).replace('.', ',')
        self.gross, self.waste, self.profit = get_profit(pay_data, tax=tax)
        zriteli_tax = (self.gross - self.waste) * 0.05 if zriteli else 0
        self.zriteli_tax = int(zriteli_tax)

    def get_descr(self):
        return [self.order_date, self.order_id, self.status, self.gross,
                self.waste, self.profit, self.tax_val,
                self.zriteli_tax, self.event_date, self.venue]


def get_orders(from_='01 Янв 2021', to_='01 Янв 2040',
               order_to='01 янв 2040',
               future_events=False, copy=True):
    from_date = Date(from_ + ' 00:01')
    to_date = Date(to_ + ' 23:59')
    order_to_date = Date(order_to + ' 23:59')
    now = Date(dt.datetime.now())
    if not future_events:
        to_date = min(now, to_date)

    # GETTING ORDER DATA
    db_manager.execute('SELECT status, id from public.tables_order '
                       "WHERE (status IN ('Завершено', 'Возврат')) AND (ordered = false)")
    incorrect = [f'    {status} {id_}' for status, id_ in db_manager.fetchall()]
    if incorrect and copy:
        incorrect_str = '\n'.join(incorrect)
        print(f'No callback:\n{incorrect_str}')
    db_manager.execute('SELECT id, status, created_at, profit, ticket_ids, viewers from public.tables_order '
                       "WHERE (status IN ('Завершено', 'Возврат')) AND (ordered = true)")
    raw = db_manager.fetchall()

    # GETTING TICKETS DATA
    arrs = [row[4] for row in raw if row[4]]
    ticket_id_gen = itertools.chain.from_iterable(arrs)
    rows = [f'SELECT id, event_id_id, scheme_id_id FROM public.tables_'
            f'tickets WHERE id = {ticket_id}'
            for ticket_id in ticket_id_gen]
    ev_scheme_on_ticket = {}
    for chunk in chunked(rows, 5000):
        db_manager.execute(' UNION '.join(chunk))
        part = {ticket: [event, scheme] for ticket, event, scheme in db_manager.fetchall()}
        ev_scheme_on_ticket.update(part)

    # GETTING EVENTS DATA
    event_ids = {row[0] for row in ev_scheme_on_ticket.values()}
    rows = [f'SELECT id, date FROM public.tables_event WHERE id = {event_id}'
            for event_id in event_ids]
    db_manager.execute(' UNION '.join(rows))
    ev_date_on_event = {id_: Date(date + dt.timedelta(hours=3)) for id_, date in db_manager.fetchall()}

    # GETTING SCHEME DATA
    scheme_ids = {row[1] for row in ev_scheme_on_ticket.values()}
    rows = [f'SELECT id, venue FROM public.tables_constructor WHERE id = {scheme_id}'
            for scheme_id in scheme_ids]
    db_manager.execute(' UNION '.join(rows))
    venue_on_scheme = {id_: venue for id_, venue in db_manager.fetchall()}

    # COMBINING
    formatted = []
    orders_all = []
    orders_ = []
    for order_id, status, order_date, pay_data, tickets, zriteli in raw:
        order_date = Date(order_date + dt.timedelta(hours=3))
        if order_date > order_to_date:
            continue
        ticket_id = tickets[0]
        if ticket_id in ev_scheme_on_ticket:
            event_id, scheme_id = ev_scheme_on_ticket[ticket_id]
            event_date = ev_date_on_event[event_id]
            venue = venue_on_scheme[scheme_id]
        elif order_id in MANUAL_ORDERS:
            venue, event_date = MANUAL_ORDERS[order_id]
            event_date = Date(event_date)
        else:
            db_manager.execute(f'SELECT order_info FROM public.tables_order WHERE id = {order_id}')
            info = db_manager.fetchall()[0][0]
            info = info.replace('\n', ' ')
            print(utils.red(f'Missed event_id for order {order_id}: {info}'))
            continue

        order = Order(order_date, order_id, status, pay_data, event_date, venue, zriteli)
        new_row = order.get_descr()
        if event_date > from_date:
            orders_all.append(order)
        if (event_date > from_date) and (event_date < to_date):
            orders_.append(order)
            formatted.append(new_row)

    # FORMATTING
    formatted.sort(key=lambda row: row[1])
    plain_print = get_plain(formatted)
    pyperclip.copy(plain_print)
    if not MANUAL_TABLE and copy:
        input(f'COPIED. {len(formatted)} orders formatted')

    # GROSSES
    closed_margins, closed_grosses = get_closed_margins(ev_scheme_on_ticket, venue_on_scheme, raw,
                                                        order_from=from_, order_to=to_)
    return orders_, orders_all, closed_margins, closed_grosses


def get_closed_margins(ev_scheme_on_ticket, venue_on_scheme, raw,
                       order_from='01 Янв 2021', order_to='01 Янв 2040'):
    from_date = Date(order_from + ' 00:01')
    to_date = Date(order_to + ' 23:59')

    # COMBINING
    formatted = []
    for order_id, status, order_date, pay_data, tickets, _ in raw:
        order_date = Date(order_date + dt.timedelta(hours=3))
        ticket_id = tickets[0]
        if ticket_id in ev_scheme_on_ticket:
            event_id, scheme_id = ev_scheme_on_ticket[ticket_id]
            venue = venue_on_scheme[scheme_id]
        elif order_id in MANUAL_ORDERS:
            venue, event_date = MANUAL_ORDERS[order_id]
        else:
            db_manager.execute(f'SELECT order_info FROM public.tables_order WHERE id = {order_id}')
            info = db_manager.fetchall()[0][0]
            info = info.replace('\n', ' ')
            print(utils.red(f'Missed event_id for order {order_id}: {info}'))
            continue
        tax = get_gross_tax(venue, order_date, status=status)
        gross, waste, profit = get_profit(pay_data, tax=tax)
        new_row = [order_date, order_id, profit, gross, venue]
        if (order_date < to_date) and (order_date > from_date):
            formatted.append(new_row)

    # FORMATTING
    margins = {'overall': {}}
    grosses = {'overall': {}}
    for month_number, orders_on_month in utils.groupby(formatted, lambda order: encode_month(order[0])):
        margins[month_number] = {}
        grosses[month_number] = {}
        for venue, orders in utils.groupby(orders_on_month, lambda key: key[-1]):
            profit = sum(order[2] for order in orders)
            gross = sum(order[3] for order in orders)
            margins[month_number][venue] = profit
            grosses[month_number][venue] = gross
            if venue not in margins['overall']:
                margins['overall'][venue] = 0
            if venue not in grosses['overall']:
                grosses['overall'][venue] = 0
            margins['overall'][venue] += profit
            grosses['overall'][venue] += gross
    return margins, grosses


def get_operators(orders, to_='01 Янв 2040', before=False):
    awards = {
        '-': 3, None: 3,
        '3': 3, '3%': 3,
        '5': 5, '5%': 5,
        '7': 7, '7%': 7,
        '10': 10, '10%': 10
    }
    to_date = Date(to_ + ' 23:59')
    db_manager.execute('SELECT id, status, profit, operator, award FROM public.tables_order '
                       "WHERE (status IN ('Завершено', 'Возврат')) AND (ordered = true)")
    data_on_order = {id_: [status, pay_data, operator, award]
                     for id_, status, pay_data, operator, award in db_manager.fetchall()
                     if operator}
    operators = {data[2] for data in data_on_order.values()}
    operators = list(operators)
    operators.sort()

    # SPEND OVERVIEW
    spendings_overview = {'overall': {}}
    spendings_on_operator = {operator: 0 for operator in operators}
    before_orders = [order for order in orders if order.order_date < to_date]
    orders_on_months = utils.groupby(before_orders, lambda row: encode_month(row[0]))
    orders_on_months = list(orders_on_months)
    orders_on_months.sort(key=lambda items: items[0])
    for month_number, orders_on_month in orders_on_months:
        spendings_overview[month_number] = {}
        orders_on_venues = utils.groupby(orders_on_month, lambda row: row[-1])
        orders_on_venues = list(orders_on_venues)
        for venue, orders_on_venue in orders_on_venues:
            if venue not in spendings_overview['overall']:
                spendings_overview['overall'][venue] = 0
            spendings_overview[month_number][venue] = 0
            for order in orders_on_venue:
                order_id = order[1]
                if order_id not in data_on_order:
                    continue
                _, pay_data, operator, award_str = data_on_order[order_id]
                award = awards[award_str]
                margin = get_earnings(pay_data, award)
                spendings_on_operator[operator] += margin
                spendings_overview[month_number][venue] += margin
                spendings_overview['overall'][venue] += margin

    # ORDERS PRINTING
    printings_on_operator = {operator: [] for operator in operators}
    for order in orders:
        if order.order_id not in data_on_order:
            continue
        status, pay_data, operator, award_str = data_on_order[order.order_id]
        award = awards[award_str]
        margin = get_earnings(order.pay_data, award)
        description = f'{order.order_id} ({order.gross})'
        if status == 'Возврат':
            description = f'Возврат {description}'
        spending = [order.order_date, description, order.venue, margin]
        this_printing = printings_on_operator[operator]
        this_printing.append(spending)
    listed_printings = list(printings_on_operator.items())
    listed_printings.sort(key=lambda row: row[0])
    listed_orders = [printing[1] for printing in listed_printings]

    # LISTING BY MONTH
    possible_months = {encode_month(order[0]) for order in itertools.chain.from_iterable(listed_orders)}
    month_lists = {month: [[] for _ in operators] for month in possible_months}
    for i, printing in enumerate(listed_orders):
        for month_number, orders_on_month in utils.groupby(printing, key=lambda order: encode_month(order[0])):
            month_list = month_lists[month_number]
            for orders_on_operator in month_list:
                orders_on_operator.sort(key=lambda row: row[0])
            month_list[i].extend(orders_on_month)
    for orders_on_month in month_lists.values():
        expand_arrs(orders_on_month)

    # FORMATTING PRINTING
    first_row_gen = [['', '', operator, ''] for operator in operators]
    second_row_gen = [['Дата', 'Заказ', 'Площадка', 'Плата'] for _ in operators]
    first_row = list(itertools.chain.from_iterable(first_row_gen))
    second_row = list(itertools.chain.from_iterable(second_row_gen))
    formatted = []
    list_of_month_lists = list(month_lists.items())
    list_of_month_lists.sort(key=lambda row: row[0])
    for month_number, orders_on_month in list_of_month_lists:
        # DATE, OPERATORS, LEGEND FIRST ROWS
        str_date = decode_month(month_number)
        date_row = [str_date, '', '', ''] * len(operators)
        first_rows = [first_row, second_row, date_row]
        formatted.extend(first_rows)

        # ORDER ROWS
        month_formatted = []
        for printings in zip(*orders_on_month):
            row = list(itertools.chain.from_iterable(printings))
            month_formatted.append(row)
        formatted.extend(month_formatted)

        # LAST SUMS ROW
        operator_summs_arrs = [['', f'За {str_date}', f'Итого {operator}', 0] for operator in operators]
        operator_summs = list(itertools.chain.from_iterable(operator_summs_arrs))
        for row in month_formatted:
            for i, elem in enumerate(row):
                if (i + 1) % 4 != 0:
                    continue
                elem = int(elem) if elem else 0
                operator_summs[i] += int(elem)
        for i, operator_sum in enumerate(operator_summs):
            if operator_sum == 0:
                operator_summs[i] = 'ИТОГО'
        formatted.append(operator_summs)

    plain_print = get_plain(formatted)
    pyperclip.copy(plain_print)
    if not MANUAL_TABLE and not before:
        input('Copied operators data')
    return spendings_overview


def get_events(orders, margins, grosses, ads_on_venue,
               operators_on_venue, before=False):
    chistogan_on_month = {}
    oleg_5_on_month = {}
    to_print_left, to_print_right = [], []

    # CHECK EVENTS
    venues = {order.venue for order in orders}
    na_venues = [venue for venue in venues if venue not in PROJECTS]
    for venue, percents in PROJECTS.items():
        if sum(percents) != 100:
            raise RuntimeError(f'Incorrect percents for venue {venue}')
    if na_venues:
        joined = "\n".join(na_venues)
        mes = f'No percentage for projects:\n{joined}'
        raise RuntimeError(mes)

    # EVENTS OVERVIEW CALCULATIONS
    orders_on_venue = utils.groupby(orders, lambda row: row.venue)
    orders_on_venue = list(orders_on_venue)
    month_data = get_events_month(orders_on_venue, margins['overall'],
                                  margins['overall'], grosses['overall'],
                                  ads_on_venue, operators_on_venue['overall'],
                                  before)
    left_part, right_part, chistogan, oleg_5 = month_data
    chistogan_on_month['overall'] = chistogan
    oleg_5_on_month['overall'] = oleg_5
    to_col = 10 if before else 12
    addition = ['-'] * 5 + [col_sum(left_part, col) for col in range(6, to_col)]
    to_print_left += [["ОБЩАЯ СВОДКА"] + addition]
    addition = [col_sum(right_part, col) for col in range(1, 3)]
    to_print_right += [["ОБЩАЯ СВОДКА"] + addition]
    to_print_left += left_part
    to_print_right += right_part

    # EVENTS PER MONTH CALCULATIONS
    orders_on_months = utils.groupby(orders, lambda row: encode_month(row.order_date))
    orders_on_months = list(orders_on_months)
    orders_on_months.sort(key=lambda items: items[0])
    for month_number, orders_on_month in orders_on_months:
        orders_on_venue = utils.groupby(orders_on_month, lambda row: row[-1])
        orders_on_venue = list(orders_on_venue)
        margins_on_month = margins[month_number] if month_number in margins else {}
        grosses_on_month = grosses[month_number] if month_number in grosses else {}
        operators_on_month = operators_on_venue[month_number] if month_number in operators_on_venue else {}
        month_data = get_events_month(orders_on_venue, margins_on_month,
                                      margins['overall'], grosses_on_month,
                                      ads_on_venue, operators_on_month,
                                      before)
        left_part, right_part, chistogan, oleg_5 = month_data
        chistogan_on_month[month_number] = chistogan
        oleg_5_on_month[month_number] = oleg_5
        header = "ЗА " + decode_month(month_number).upper()
        addition = ['-'] * 5 + [col_sum(left_part, col) for col in range(6, to_col)]
        to_print_left += [[header] + addition]
        addition = [col_sum(right_part, col) for col in range(1, 3)]
        to_print_right += [[header] + addition]
        to_print_left += left_part
        to_print_right += right_part

    plain_print = get_plain(to_print_left)
    pyperclip.copy(plain_print)
    if not MANUAL_TABLE:
        input('COPIED. Left events part')
    plain_print = get_plain(to_print_right)
    pyperclip.copy(plain_print)
    if not MANUAL_TABLE:
        input('COPIED. Right events part')
    return chistogan_on_month, oleg_5_on_month


def get_events_month(order_groups, margins, overall_margins, grosses,
                     ads_on_venue, operators_on_venue, before):
    to_print_left = []
    to_print_right = []
    chistogans_on_venue = {}
    oleg_5_on_month = 0
    for venue, orders in order_groups:
        percents = [22, 22, 22, 34, 0] if before else PROJECTS[venue]
        row = [venue] + percents
        gross_sum, waste_sum, profit_sum, zriteli_sum = 0, 0, 0, 0
        for _, _, gross, waste, profit, _, zriteli_tax, event_date, _ in orders:
            if not event_date.is_outdated():
                continue
            gross_sum += gross
            waste_sum += waste
            profit_sum += profit
            zriteli_sum += zriteli_tax

        margin = margins.get(venue, 0)
        gross = grosses.get(venue, 0)
        overall_margin = overall_margins.get(venue, 0)
        short_venue = parse_venue(venue)
        ad_spending = ads_on_venue.get(short_venue, 0)
        oper_spending = '' if before else operators_on_venue.get(venue, 0)
        if overall_margin == 0:
            overall_margin = 1
        ads_on_venue_share = ad_spending * margin / overall_margin
        ads_on_venue_share = int(ads_on_venue_share)
        zriteli_str = zriteli_sum if zriteli_sum else ''
        addition = [gross_sum, waste_sum, profit_sum,
                    ads_on_venue_share, oper_spending, zriteli_str]
        second_part = ['', gross, margin]

        row.extend(addition)
        to_print_left.append(row)
        to_print_right.append(second_part)
        if not oper_spending:
            oper_spending = 0
        chistogan = profit_sum - ads_on_venue_share - oper_spending - zriteli_sum
        oleg_5_on_month += zriteli_sum
        chistogan_shares = [chistogan / 100 * percent for percent in percents]
        chistogans_on_venue[venue] = chistogan_shares
    return to_print_left, to_print_right, chistogans_on_venue, oleg_5_on_month


def get_venues(formatted):
    input('INPUT existing venues')
    rows = paste_clip()
    existing_venues = [venue for venue in rows[0] if venue]

    venues = {parse_venue(order[-1]) for order in formatted}

    """db_manager.execute('SELECT venue, id from public.tables_constructor')
    venue_on_scheme = {id_: parse_venue(venue) for venue, id_ in db_manager.fetchall()}
    db_manager.execute('SELECT scheme_id from public.tables_event')
    venues = {venue_on_scheme[row[0]] for row in db_manager.fetchall() if row[0]}"""

    added_venues = [venue for venue in venues if venue not in existing_venues]
    to_print = [existing_venues + added_venues]
    plain = get_plain(to_print)
    pyperclip.copy(plain)
    input(f'COPIED. {len(added_venues)} venues added')


def get_ads():
    if MANUAL_TABLE:
        formatted = []
        for row in MANADS_TABLE.split('\n'):
            formed_row = [item.replace('\r', '') for item in row.split('\t')]
            formatted.append(formed_row)
        rows = formatted
    else:
        input('INPUT an ads table')
        rows = paste_clip()
    cols = [[] for _ in rows[0]]
    for row in rows:
        for i, item in enumerate(row):
            cols[i].append(item)
    money_on_venue = {col[0]: sum(int(item) for item in col[1:] if item) for col in cols}
    venues_with_money = 0
    for money in money_on_venue.values():
        if money:
            venues_with_money += 1
    all_sums = sum(money for money in money_on_venue.values())
    print(f'Ads copied for {venues_with_money}\\{len(money_on_venue)}. Summary is {all_sums}')
    return money_on_venue


def get_plus_by_day(orders_closed):
    not_sasha_orders = [order for order in orders_closed if get_owner(order[-1]) != 'Саша']
    venues = {order[-1] for order in not_sasha_orders}
    dates = {encode_day(order[0]) for order in not_sasha_orders}
    venues = sorted(list(venues))
    dates = sorted(list(dates))
    matrix = [[decode_day(date)] + [0] * (len(venues)) for date in dates]
    to_add = [''] + venues
    matrix.insert(0, to_add)
    for order in not_sasha_orders:
        venue_index = venues.index(order[-1]) + 1
        date_index = dates.index(encode_day(order[0])) + 1
        matrix[date_index][venue_index] += int(order[4])
    plain_print = get_plain(matrix)
    pyperclip.copy(plain_print)
    input('COPIED. Pluses for Misha and Nikita')


def get_overall(closed, chistogan, oleg_5):
    if MANUAL_TABLE:
        rows = []
        for row in SALARY_TABLE.split('\n'):
            formed_row = [item.replace('\r', '') for item in row.split('\t')]
            rows.append(formed_row)
    else:
        input('INPUT salaries on month')
        rows = paste_clip()
    salaries = {month: int(salary) for month, salary in rows if salary}

    owner_earnings = {
        'Никите': 0,
        'Саше С.': 0,
        'Олегу': 0
    }
    for venue, gross in closed.items():
        owner = get_owner(venue)
        owner_alias = OWNER_ALIASES[owner]
        owner_earnings[owner_alias] += gross

    left_table = []
    for month_num, chistogan_on_month in chistogan.items():
        any_project = list(PROJECTS.values())[0]
        cols_number = len(any_project) + 2
        month_str = 'За всё время' if month_num == 'overall' else decode_month(month_num)
        chistogan_row = [0 for _ in range(cols_number)]
        chistogan_row[0] = month_str
        for chistogan_on_venue in chistogan_on_month.values():
            chistogan_row[1] += sum(chistogan_on_venue)
            for i, money in enumerate(chistogan_on_venue):
                chistogan_row[i + 2] += money
        for i, summ in enumerate(chistogan_row):
            if i == 0:
                continue
            chistogan_row[i] = int(summ)
        left_table.append(chistogan_row)

    right_table = []
    for owner, gross in owner_earnings.items():
        new_row = [f'За эквайринг {owner}', int(gross * 0.969 * 0.03)]
        right_table.append(new_row)
    right_table.append(['Олегу 5% за зрители', oleg_5['overall']])

    salary_dict = {}
    for chistogan_row in left_table:
        month_name = chistogan_row[0]
        if month_name not in salaries:
            continue
        chistogan_sum = chistogan_row[1]
        salary_on_month = salaries[month_name]
        for i, chistogan_on_owner in enumerate(chistogan_row[2:]):
            owner = SHARE_OWNER_NAMES[i]
            key = f'ЗП за {month_name} платит {owner}'
            salary_dict[key] = int(chistogan_on_owner / chistogan_sum * salary_on_month)
    for row in salary_dict.items():
        right_table.append(row)

    to_print = []
    any_project = list(PROJECTS.values())[0]
    for left_row, right_row in itertools.zip_longest(left_table, right_table, fillvalue=None):
        if left_row is None:
            left_row = ['' for _ in range(len(any_project) + 2)]
        if right_row is None:
            right_row = ['', '']
        combined_row = list(left_row) + [''] + list(right_row)
        to_print.append(combined_row)
    plain_print = get_plain(to_print)
    pyperclip.copy(plain_print)
    input('COPIED. Overall. Earnings')

    to_print = [[gross] for gross in owner_earnings.values()]
    plain_print = get_plain(to_print)
    pyperclip.copy(plain_print)
    input('COPIED. Overall. Gross by acquiring')


def get_overall_before(orders_closed, to_='01 Янв 2040'):
    to_date = Date(to_ + ' 23:59')
    oleg_earnings = 0
    for order in orders_closed:
        if order[0] > to_date:
            continue
        if order[5] == '0,0':
            oleg_earnings += order[2] * 0.96 * 0.03
    oleg_earnings = str(int(oleg_earnings))
    pyperclip.copy(oleg_earnings)
    print('Olegy chehlim ' + oleg_earnings)


def format_date(date: Date):
    return f'{date.day}.{date.month}.{date.year} {date.hour}:{date.minute}:00'


def get_profit(pay_data, tax=0.9):
    gross, waste, profit = 0, 0, 0
    for ticket in pay_data:
        add_gross = int(ticket['sell_price'])
        tax_gross = int(add_gross * tax)
        gross += add_gross
        start_price = ticket['start_price'] if ticket['start_price'] else 0
        waste += int(start_price)
        refund = ticket['refund'] if 'refund' in ticket else 0
        refund = int(refund) if refund else 0
        profit += tax_gross - int(start_price) - refund
    profit = max(profit, 0)
    return gross, waste, profit


def get_tax(venue, order_date):
    if venue == 'Большой театр' and order_date < Date('31 Дек 2022 23:59'):
        return 0.03
    if order_date < Date('26 Дек 2022 00:01'):
        return 0.0259
    elif order_date < Date('18 Янв 2023 00:01'):
        return 0
    owner = get_owner(venue)
    if (owner == 'Саша') and (order_date < Date('01 Мар 2023 00:01')):
        return 0.035
    return ACQUIRINGS[owner]


def get_gross_tax(venue, order_date, status='Завершено'):
    tax = get_tax(venue, order_date)
    return (1 - tax) * 0.94 if status == 'Завершено' else 1 - tax


def format_ids(ids):
    str_ids = [f"'{id_}'" for id_ in ids]
    joined = ", ".join(str_ids)
    return f'({joined})'


def parse_venue(venue):
    return venue.replace('Театр', '') \
                .replace('театр', '') \
                .strip()[:15]


def paste_clip():
    table = pyperclip.paste()
    formatted = []
    for row in table.split('\n'):
        formed_row = [item.replace('\r', '') for item in row.split('\t')]
        formatted.append(formed_row)
    return formatted


def get_plain(formatted):
    to_print = []
    for row in formatted:
        str_elems = []
        for elem in row:
            str_elem = str(elem)
            str_elems.append(str_elem)
        str_row = '\t'.join(str_elems)
        to_print.append(str_row)
    return '\n'.join(to_print)


def expand_arrs(listed_orders):
    max_operator_len = max(len(printing) for printing in listed_orders)
    for listed in listed_orders:
        add_len = max_operator_len - len(listed)
        additional = [['', '', '', ''] for _ in range(add_len)]
        listed.extend(additional)


def get_earnings(pay_data, percent):
    max_award = {
        3: 500,
        5: 1000,
        7: 1500,
        10: 3000
    }
    margin = get_profit(pay_data)[2]
    return min(round(margin * percent / 100), max_award[percent])


def get_owner(venue):
    shares = PROJECTS[venue]
    owners = {
        1: 'Никита',
        2: 'Саша',
        3: 'Миша'
    }
    max_share = max(shares)
    share_index = shares.index(max_share)
    assert share_index in owners, f'Unknown share owner from: {shares}'
    return owners[share_index]


def col_sum(arr, num):
    summary = 0
    for row in arr:
        if row[num]:
            summary += row[num]
    return summary


if __name__ == '__main__':
    to_date = '11 Апр 2023'
    mode = input('Mode: ')
    if mode == 'after':
        ads_on_venue = get_ads()
        orders, orders_closed, closed_margins, closed_grosses = get_orders(from_='18 Янв 2023', to_=to_date,
                                                                           future_events=False)
        operators_on_venue = get_operators(orders_closed, to_=to_date, before=False)
        chistogan, oleg_5 = get_events(orders, closed_margins, closed_grosses, ads_on_venue,
                                       operators_on_venue, before=False)
        get_overall(closed_grosses['overall'], chistogan, oleg_5)
    elif mode == 'before':
        ads_on_venue = get_ads()
        orders, orders_closed, closed_margins, closed_grosses = get_orders(to_='17 Янв 2023')
        operators_on_venue = get_operators(orders_closed, to_='17 Янв 2023', before=True)
        chistogan, _ = get_events(orders, closed_margins, closed_grosses, ads_on_venue,
                                  operators_on_venue, before=True)
        get_overall_before(orders_closed, to_='17 Янв 2023')
    elif mode == 'operators':
        orders, orders_closed, closed_margins, closed_grosses = get_orders(to_='17 Янв 2023')
        operators_on_venue = get_operators(orders_closed, to_='17 Янв 2023', before=True)
    elif mode == 'nekitmisha':
        # MANUAL_TABLE = True
        orders, _, _, _ = get_orders(from_='18 Янв 2023', to_='01 Янв 3333',
                                     future_events=True, copy=False)
        orders_after_18 = [order for order in orders if order.order_date > Date('18 Янв 2023 00:01')]
        get_plus_by_day(orders_after_18)
    elif mode == 'venues':
        orders, _, _, _ = get_orders(from_='18 Янв 2023', to_='01 Янв 2033',
                                     future_events=True, copy=False)
        get_venues(orders)
    # get_venues()

    # ads_on_venue = get_ads()
    # events, grosses = get_orders(from_='18 Янв 2023')
    # get_events(events, grosses, before=False)
