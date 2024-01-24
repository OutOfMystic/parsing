import datetime
import itertools

import numpy as np

from . import base
from ..connection import db_manager
from ..manager.backend import AISolver
from ..models.ai_nlp import solve
from ..models.ai_nlp.collect import make_matrix, solve_pairs, build_connection
from ..models.ai_nlp.venue import VenueAliases
from parse_module.manager.group import crop_url
from ..utils import utils
from ..utils.date import Date
from ..utils.logger import logger

solver, cache_dict = solve.get_model_and_cache()


def route_cmd(args_row):
    """
    Methods for monitoring AI decisions. Multiple use cases:
        - ai solutions (parser_key): summarize AI solutions in website-parser pair with {parser_key} occurrences
        - ai venues: show assignment table for venues. Venues are event parameters collected from event parsers
        - ai events (events_key): list events with {events_key} occurrences and assigned parsers to them
        - ai pair [origin] [alias]: manually solve origin-alias pair with AI
        - ai doubts (min) (max): list AI estimates from {min} to {max} for pairs. By def., {min} == 0.9, {max} == 0.999
    """
    args = base.split_args(args_row)
    commands = {
        'events': list_events,
        'solutions': ai_solutions,
        'doubts': ai_doubts,
        'pair': ai_pair,
        'venues': show_venues
    }
    available = ', '.join(commands)
    if not args:
        raise AttributeError(f'Specify attribute. '
                             f'Available attributes are: {available}')
    cmd = args.pop(0)
    if cmd not in commands:
        raise AttributeError(f'"ai" attribute "{cmd}" wasn\'t found. '
                             f'Available attributes are: {available}')
    return commands[cmd](args)


def list_events(args):
    if len(args) > 1:
        raise RuntimeError('Too much arguments (should be 0 or 1)')
    search_key = args[0] if args else ''

    print('Obtaining data from the database...')
    ai_evs = {}
    venues = VenueAliases(solver)
    subjects = db_manager.get_events_for_parsing()
    objects = db_manager.get_parsed_events()
    types_on_site = db_manager.get_site_parsers()

    print('Initialising a neural network...')
    for pairs, submatrix_shapes, priority, margin, _, _ in make_matrix(subjects, objects, venues, types_on_site):
        names_from_pairs = [(subject['event_name'], object_['event_name'],) for subject, object_ in pairs]
        assignments = solve_pairs(names_from_pairs, submatrix_shapes, solver, cache_dict, originals=pairs)
        connections = [build_connection(*assignment, priority, margin) for assignment in assignments]
        for conn in connections:
            event_id = conn['event_id']
            if event_id not in ai_evs:
                ai_evs[event_id] = []
            urls_on_events = ai_evs[event_id]
            urls_on_events.append(conn['url'])

    print('Formatting output...')
    db_manager.execute("SELECT id, name FROM public.tables_sites")
    sites = {id_: name for id_, name in db_manager.fetchall()}
    db_manager.execute("SELECT url FROM public.tables_parsedevents")
    pred_evs = [crop_url(row[0]) for row in db_manager.fetchall()]
    db_manager.execute("SELECT id, name, date, site_id, parsed_url FROM public.tables_event")
    records = [[id_, f'{name} {three_hrs(date)}', sites[site_id], handle_parsers(parsers, pred_evs, id_, ai_evs)]
               for id_, name, date, site_id, parsers in db_manager.fetchall()
               if not three_hrs(date).is_outdated()]
    records.sort(key=lambda row: int(row[0]))

    to_print = []
    for site, rows in utils.groupby(records, lambda row: row[2]):
        if site == 'theater-tickets.store':
            continue
        searched_records = [record for record in rows if
                            search_key.lower() in record[1].lower()]
        if not searched_records:
            continue
        to_print.append(['', f'--{site}--', '', ''])
        to_print.extend(searched_records)
    base.print_cols(to_print, (7, 50, 30, 1000))


def result_message(step, legend, success):
    message = f'{step}. {legend}'
    log_func = logger.success if success else logger.error
    log_func(message)


def subject_object_check(args):
    if len(args) == 2:
        raise RuntimeError('Number of arguments should be 2')
    event_id, url = args

    subjects = db_manager.get_events_for_parsing()
    sycceded = event_id in [subj['event_id'] for subj in subjects]
    result_message(0, 'Проверка на наlичие event_id в системе', sycceded)
    if not sycceded:
        return

    parsing_types = db_manager.get_parsing_types()
    objects = db_manager.get_parsed_events(types=parsing_types)

    ai_solver = AISolver()
    connections = ai_solver.get_connections(subjects, set(), parsing_types, objects)


def ai_solutions(args):
    def mark_obj(object_, to_site, to_type_):
        mark_key = (to_site, to_type_, object_['url'],)
        return '(CONFLICT) ' if mark_key in pred_urls else ''

    def mark_subj(subject, to_site, to_type_):
        mark_key = (to_site, to_type_, subject['event_id'],)
        return '(RESOLVED) ' if mark_key in pred_ids else ''

    if len(args) > 1:
        raise RuntimeError('Too much arguments (should be 0 or 1)')
    search_key = args[0] if args else ''

    print('Obtaining data from the database...')
    not_empty_assignments = {}
    venues = VenueAliases(solver)
    subjects = db_manager.get_events_for_parsing()
    parsing_types = db_manager.get_parsing_types()
    objects = db_manager.get_parsed_events()
    db_manager.execute("SELECT id, name FROM public.tables_sites")
    sites = {id_: name for id_, name in db_manager.fetchall()}
    db_manager.execute("SELECT url, parent FROM public.tables_parsedevents")
    parsed_evs = {crop_url(url): parent for url, parent in db_manager.fetchall()}
    db_manager.execute("SELECT id, name, date, site_id, parsed_url FROM public.tables_event")
    subj_data = db_manager.fetchall()
    types_on_site = db_manager.get_site_parsers()
    subj_data.sort(key=lambda data_row: Date(data_row[2]))
    sites_with_subjs = set(subject[3] for subject in subj_data)
    no_subjects = [site_id for site_id, site_name in sites.items() if site_id not in sites_with_subjs]
    pred_urls = set()
    pred_ids = set()

    print('Initialising a neural network...')
    for pairs, submatrix_shapes, priority, margin, site_id, type_id\
            in make_matrix(subjects, objects, venues, types_on_site):
        if type_id is None:
            continue
        type_ = parsing_types[type_id]
        site = sites[site_id]
        if not pairs:
            continue
        venue = pairs[0][1]['venue']
        scheme = venues.get(venue) if venue else None
        key = (site, type_, venue, str(scheme))

        names_from_pairs = [(subject['event_name'], object_['event_name'],) for subject, object_ in pairs]
        assignments = solve_pairs(names_from_pairs, submatrix_shapes, solver, cache_dict, originals=pairs)
        connections = [build_connection(*assignment, priority, margin) for assignment in assignments]
        connections.sort(key=lambda conn: conn['date'])
        predefined = []
        for id_, name, date, cur_site_id, parsers in subj_data:
            url = get_url(parsers, parsed_evs, type_)
            if not url:
                continue
            pred_urls.add((site, type_, url,))
            pred_ids.add((site, type_, id_,))
            date = three_hrs(date)
            date = str(date)
            row = (date, name, url,)
            predefined.append(row)

        ass_subjects = [pair[0] for pair in assignments]
        ass_objects = [pair[1] for pair in assignments]
        unass_objects = [object_ for _, object_ in pairs
                         if object_ not in ass_objects]
        unass_subjects = [subject for subject, _ in pairs
                          if subject not in ass_subjects]

        # assert key not in not_empty_assignments, "Matrix reading: already grabbed unassigned objects and subjects"
        not_empty_assignments[key] = (predefined, connections, unass_subjects, unass_objects,)

    print('Formatting output...')
    for group_key, events_data in not_empty_assignments.items():
        site, type_, venue, scheme = group_key
        predefined, connections, subjects, objects = events_data
        if site == 'theater-tickets.store':
            continue
        venue = f'; {venue}->{scheme}' if venue else ''
        key = f'--{site}; {type_}{venue}--'
        if search_key.lower() not in key.lower():
            continue
        print(key)

        message = '1. Predefined parsers. These parsers have been ' \
                  'assigned in our CRM system (nebilet.fun)'
        print(utils.green(message))
        base.print_cols(predefined, (30, 50, 100), indent=2)

        message = '2. Paired subjects and objects:'
        print(utils.green(message))
        rows = [[conn["date"], conn["event_name"], conn["url"]] for conn in connections]
        base.print_cols(rows, (30, 50, 100), indent=2)

        message = '3. Subjects in tables_event. ' \
                  'None of the parsed events matches to events ' \
                  '(on our websites) below:'
        print(utils.yellow(message))
        rows = [[subject["date"], subject["event_name"], mark_subj(subject, site, type_)]
                for subject in subjects]
        base.print_cols(rows, (30, 50, 11), indent=2)

        message = '4. Objects in tables_parsedevents. ' \
                  'These event names were parsed, but were not ' \
                  'assigned to a specific event on the site:'
        print(utils.yellow(message))
        rows = [[object_["date"], object_["event_name"], mark_obj(object_, site, type_), object_["url"]]
                for object_ in objects]
        base.print_cols(rows, (30, 50, 11, 100), indent=2)

    # empty sites
    type_on_site = [[(site_id, type_id,) for type_id in types]
                    for site_id, types in db_manager.get_site_parsers().items()]
    type_on_site_str = [(sites[site_id], parsing_types[type_id],)
                        for site_id, type_id in itertools.chain.from_iterable(type_on_site)]
    not_empty_site_and_type = [(row[0], row[1],) for row in not_empty_assignments]
    empty_keys = [site_and_type for site_and_type in type_on_site_str
                  if site_and_type not in not_empty_site_and_type]
    for site, type_ in empty_keys:
        if site == 'theater-tickets.store':
            continue
        key = f'--{site}; {type_}--'
        if search_key.lower() not in key.lower():
            continue
        print(key)
        if key in no_subjects:
            print(utils.red(f'  {site} is empty!.\n'
                            f'  Most likely, this site is a mirror of another site'))
        else:
            print(utils.red(f'  There are no {type_} events that could be applied to {site}.\n'
                            f'  Most likely, this parser didn\'t parse any event'))


def show_venues(_):
    print('Obtaining data from the database...')
    venues = VenueAliases(solver)
    types_on_site = db_manager.get_site_parsers()
    parsing_types = db_manager.get_parsing_types()
    objects = db_manager.get_parsed_events(types=parsing_types)

    all_types = set()
    for types in types_on_site.values():
        for type_ in types:
            all_types.add(type_)
    object_venues = {object_['venue'] for object_ in objects if object_['type_id'] in all_types}
    object_venues.discard(None)

    print('Initialising a neural network...')
    venues.update_names(object_venues)
    schemes_on_alias = {alias: schemes for alias, schemes in venues.aliases.items() if schemes is not None}
    objects_on_alias = utils.groupdict(objects, lambda object_: object_['venue'])
    parsers_on_alias = {alias: {obj['type_id'] for obj in schemes} for alias, schemes in objects_on_alias.items()}
    all_schemes_gen = (schemes for schemes in venues.aliases.values() if schemes is not None)
    all_schemes = itertools.chain.from_iterable(all_schemes_gen)
    all_schemes = list(set(all_schemes))
    all_types = {object_['type_id'] for object_ in objects if object_['type_id'] is not None}
    all_types = list(all_types)

    print('Formatting output...')
    matrix = np.full((len(all_schemes), len(all_types)), -1, np.int_)
    for alias_ind, alias in enumerate(venues.aliases):
        if alias is None:
            continue
        schemes = schemes_on_alias[alias]
        parsers = parsers_on_alias[alias]
        for scheme in schemes:
            for scheme_ind, got_scheme in enumerate(all_schemes):
                if got_scheme != scheme:
                    continue
                for parser in parsers:
                    parser_ind = all_types.index(parser)
                    matrix[scheme_ind, parser_ind] = alias_ind

    separator = '    ---------'
    all_aliases = list(venues.aliases.keys())
    first_row = [''] + [parsing_types[type_id] for type_id in all_types]
    rows = [first_row]
    for scheme_ind, aliases_on_scheme in enumerate(matrix):
        scheme = all_schemes[scheme_ind]
        row = [f'[{scheme}]']
        for alias_ind in aliases_on_scheme:
            if alias_ind == -1:
                row.append(separator)
            else:
                alias = all_aliases[alias_ind]
                row.append(alias)
        rows.append(row)

    for col in range(len(rows[0]) - 1, -1, -1):
        if is_col_empty(rows, col, value=separator):
            for row in rows:
                del row[col]

    cols_count = len(all_types) + 1
    widths = [50] * cols_count
    base.print_cols(rows, widths)


def ai_pair(words):
    if len(words) != 2:
        raise RuntimeError('Too much arguments (should be 0 or 2)')
    print('Initialising a neural network...')
    accuracy = solver.solve(words)
    match = accuracy > 0.999
    print(f'Pair {", ".join(words)} is valid with accuracy {accuracy} ({match})')


def ai_doubts(args):
    if (len(args) != 2) and (args != ['']):
        raise RuntimeError('Too much arguments (should be 0 or 2)')
    if args == ['']:
        search_min, search_max = 0.9, 0.999
    else:
        search_min, search_max = args
    search_min = float(search_min)
    search_max = float(search_max)
    assert (search_min >= -1.0) and (search_min <= 1.0), 'minimum should be a float in range [-1.0, 1.0]'
    assert (search_max >= -1.0) and (search_max <= 1.0), 'maximum should be a float in range [-1.0, 1.0]'
    assert search_max > search_min, 'maximum should be more than minimum'

    print('Obtaining data from the database...')
    subjects = db_manager.get_events_for_parsing()
    parsing_types = db_manager.get_parsing_types()
    sites = db_manager.get_site_names()
    objects = db_manager.get_parsed_events(types=parsing_types)
    types_on_site = db_manager.get_site_parsers()

    print('Initialising a neural network...')
    results = []
    venues = VenueAliases(solver)
    for pairs, shapes, priority, margin, site_id, type_id in make_matrix(subjects, objects, venues, types_on_site):
        site = sites[site_id]
        if type_id is None:
            continue
        type_ = parsing_types[type_id]
        row = [site, type_, '', '']
        results.append(row)
        print('.', end='')

        names_from_pairs = [(subject['event_name'], object_['event_name'],) for subject, object_ in pairs]
        solved = solver.solve_pack(names_from_pairs)

        pointer = 0
        for x_shape, y_shape in shapes:
            flat_shape = x_shape * y_shape
            solved_part = solved[pointer: pointer + flat_shape]
            pairs_part = pairs[pointer: pointer + flat_shape]
            rows_to_print = []
            for pair, solution in zip(pairs_part, solved_part):
                subject, object_ = pair
                if solution < search_min:
                    continue
                if solution > search_max:
                    continue
                row = [subject['event_name'], object_['event_name'], solution, ' ' + object_['url']]
                rows_to_print.append(row)
            if rows_to_print:
                date = pairs_part[0][0]["date"]
                row = ['    ' + str(date), '', '', '']
                results.append(row)
                results.extend(rows_to_print)
            pointer += flat_shape
    base.print_cols(results, (50, 50, 10, 120))


def three_hrs(date):
    return Date(date + datetime.timedelta(hours=3))


def is_col_empty(array, col, value=None):
    for i, row in enumerate(array):
        if i == 0:
            continue
        if row[col] != value:
            return False
    else:
        return True


def handle_parsers(parsers, pred_evs, id_, ai_evs):
    result = ''
    if not parsers:
        parsers = []
    for i, parser in enumerate(parsers):
        if parser is None:
            continue
        url, margin = parser
        sign = '+' if crop_url(url) in pred_evs else '-'
        url = f' ({sign}){url}'
        result += url
        # color = utils.Fore.LIGHTGREEN_EX if crop_url(url) in pred_evs else utils.Fore.RED
        # formatted = utils.colorize(url, color)
    if id_ not in ai_evs:
        return result
    ai_events_on_id = ai_evs[id_]
    for url in ai_events_on_id:
        result += f' (ai){url}'
    return result


def get_url(parsers, parsed_evs, parsing_type):
    if not parsers:
        parsers = []
    for url, _ in parsers:
        for parsed_url, parsed_type in parsed_evs.items():
            if parsing_type != parsed_type:
                continue
            if crop_url(url) == parsed_url:
                return url
