import datetime
import itertools
import time

from parse_module.connection import db_manager
from parse_module.utils import utils
from parse_module.utils.date import Date
from parse_module.utils.logger import logger


def cross_subject_object(subjects, objects, venues, solver, cache_dict, types_on_site, labels=None):
    matrix_generator = make_matrix(subjects, objects, venues, types_on_site, labels=labels)
    for pairs, submatrix_shapes, priority, margin, _, _ in matrix_generator:
        names_from_pairs = [(subject['event_name'], object_['event_name'],) for subject, object_ in pairs]
        assignments = solve_pairs(names_from_pairs, submatrix_shapes, solver, cache_dict, originals=pairs)
        connections = [build_connection(subj, obj_, priority, margin) for subj, obj_ in assignments]
        for connection in connections:
            yield connection

    """start_time = time.time()
    matricies_data = list(data[:4] for data in make_matrix(subjects, objects, venues, types_on_site))
    chained_pairs = itertools.chain.from_iterable(row[0] for row in matricies_data)
    chained_shapes = itertools.chain.from_iterable(row[1] for row in matricies_data)
    names_from_pairs = [(subject['event_name'], object_['event_name'],) for subject, object_ in chained_pairs]
    chained_solutions = get_packed_solutions(names_from_pairs, chained_shapes, originals=list(chained_pairs))
    solutions_index = 0
    for pairs, shapes, priority, margin in matricies_data:
        x_amount = shapes[0]
        solutions = chained_solutions[solutions_index: x_amount]
        solutions_index += x_amount
        assignments = assign_pairs(solutions)
        connections = [build_connection(*assignment, priority, margin) for assignment in assignments]
        for connection in connections:
            yield connection
    logger.debug(time.time() - start_time)"""


def build_connection(subject, object_, priority, margin):
    signature = {
        'priority': priority,
        'event_id': subject['event_id'],
        'scheme_id': subject['scheme_id'],
        'date': str(subject['date']),
        'url': object_['url'],
        'margin': margin
    }
    connection = {
        'event_id': subject['event_id'],
        'scheme_id': subject['scheme_id'],
        'event_name': subject['event_name'],
        'date': subject['date'],
        'url': object_['url'],
        'venue': object_['venue'],
        'extra': object_['extra'],
        'parsing_id': object_['type_id'],
        'priority': priority,
        'signature': signature,
        'margin': margin,
        'parent': object_['parent']
    }
    indicator = signature.copy()
    del indicator['priority']
    connection['indicator'] = str(indicator)
    return connection


def make_matrix(subjects, objects, venues, types_on_site, labels=None):
    if not objects:
        return
    if labels:
        site_labels, parsers_labels, already_warned = labels
    else:
        site_labels, parsers_labels, already_warned = {}, {}, set()

    for subject in subjects:
        transform_date(subject, hrsdelta=0)
    for object_ in objects:
        transform_date(object_)
    subjects.sort(key=sort_by_date)
    objects.sort(key=sort_by_date)

    all_types = set()
    for types in types_on_site.values():
        for type_id in types:
            all_types.add(type_id)
    object_venues = {object_['venue'] for object_ in objects if object_['type_id'] in all_types}
    object_venues.discard(None)
    venues.update_names(object_venues)
    aliases = venues.aliases

    subjects_on_sites = utils.groupdict(subjects, lambda subj: subj['site_id'])
    for site_id, types in types_on_site.items():
        subjects_on_site = subjects_on_sites.get(site_id, [])
        subjects_dict = utils.groupdict(subjects_on_site, lambda subj: venues.schemes[subj['scheme_id']])
        for priority, type_id in enumerate(types):
            objects_on_type = [object_ for object_ in objects if object_['type_id'] == type_id]
            if not objects_on_type:
                if labels:
                    site_name = site_labels.get(site_id, site_id)
                    type_name = parsers_labels.get(type_id, type_id)
                    record_key = (site_name, type_name,)
                    if record_key not in already_warned:
                        already_warned.add(record_key)
                        message = (f'Event parser doesn\'t seem correct '
                                   f'(TYPE "{type_name}", SITE "{site_name}")')
                        logger.warning(message, name='Controller (Backend)')
                continue
            object_gen = utils.groupby(objects_on_type, lambda o: o['venue'])
            objects_list = list(object_gen)
            margin = types[type_id]
            if (objects_list[0][0] is None) and len(objects_list) == 1:
                pairs, shapes = separate_by_date(subjects_on_site, objects_on_type)
                yield pairs, shapes, priority + 10, margin, site_id, type_id
                continue
            for object_venue, objects_on_venue in objects_list:
                if object_venue is None:
                    continue
                object_schemes = aliases[object_venue]
                for object_scheme in object_schemes:
                    if object_scheme in subjects_dict:
                        subjects_on_venue = subjects_dict[object_scheme]
                        pairs, shapes = separate_by_date(subjects_on_venue, objects_on_venue)
                        if not pairs:
                            continue
                        # if site_id == 304:
                        #     print(object_scheme, '|', object_venue, '|', type_id, '|', site_id)
                        #     pprint(pairs)
                        yield pairs, shapes, priority + 10, margin, site_id, type_id
                    # else:
                    #    print(utils.yellow(f'Object venue {object_venue} ({object_scheme}) was not found in subjects '
                    #                       f'    site {site_id}, parsing {type_}'))


def get_packed_solutions(pairs, shapes, solver, cache_dict, originals=None):
    pairs = tuple(pairs)
    if originals is None:
        originals = pairs
    solved = cache_dict.get(pairs, None)

    if solved is None:
        solved = solver.solve_pack(pairs)
        cache_dict[pairs] = solved
    return pack_back(originals, solved, shapes)


def solve_pairs(pairs, shapes, solver, cache_dict, originals=None):
    packed_pairs = get_packed_solutions(pairs, shapes, solver, cache_dict, originals=originals)
    return assign_pairs(packed_pairs)


def separate_by_date(subjects, objects):
    events_by_date = {}
    subjects.sort(key=lambda subj: subj['event_name'])
    objects.sort(key=lambda obj: obj['event_name'])
    for subject in subjects:
        subject_date = subject['date'].delta()
        appended = False
        for date in events_by_date:
            if abs(date - subject_date) > 590:
                continue
            on_date = events_by_date[date][0]
            on_date.append(subject)
            appended = True
        if not appended:
            event_by_date = [[subject], []]
            events_by_date[subject_date] = event_by_date

    for object in objects:
        object_date = object['date'].delta()
        for date in events_by_date:
            if abs(date - object_date) > 590:
                continue
            on_date = events_by_date[date][1]
            on_date.append(object)

    matrix = []
    matrix_shapes = []
    for date, events_on_date in events_by_date.items():
        subjects, objects_ = events_on_date
        if not objects_:
            continue
        matrix_shape = (len(subjects), len(objects_))
        for pair in itertools.product(subjects, objects_):
            matrix.append(pair)
        matrix_shapes.append(matrix_shape)
    return matrix, matrix_shapes


def pack_back(pairs, solved, shapes):
    pointer = 0
    packed = []
    for x_shape, y_shape in shapes:
        flat_shape = x_shape * y_shape
        solved_part = solved[pointer: pointer + flat_shape]
        pairs_part = pairs[pointer: pointer + flat_shape]
        for x in range(x_shape):
            solutions = solved_part[x * y_shape: (x + 1) * y_shape]
            best = x * y_shape + solutions.index(max(solutions))
            solution = pairs_part[best]
            solution = list(solution)
            solution.append(max(solutions))
            packed.append(solution)
        pointer += flat_shape
    return packed


def assign_pairs(packed_pairs):
    assigned = set()
    assignments = []
    for subject, object_, score in packed_pairs:
        if score < 0.999:
            continue
        if subject['event_id'] in assigned:
            continue
        assigned.add(subject['event_id'])
        pair = (subject, object_,)
        assignments.append(pair)
    return assignments


def transform_date(event_data, hrsdelta=0):
    date = event_data['date']
    if hrsdelta:
        date += datetime.timedelta(hours=hrsdelta)
    event_data['date'] = Date(date)


def sort_by_date(elem):
    delta = elem['date'].datetime() - datetime.datetime.now()
    return delta.total_seconds()
