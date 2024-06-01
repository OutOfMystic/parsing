def make_row_and_seats(all_rows,
                       SCALE_X,
                       SCALE_Y,
                       need_reformat=True):
    all_rows_and_seats = []
    for segment in all_rows:
        name = segment.get('name')
        segmentCategory = segment.get('segmentCategory')#категория?
        segments = segment.get('segments')#все ряды в этом секторе
        for row in segments:
            row_name = row.get('name')
            placeSize = row.get('placeSize')
            placesNoKeys = row.get('placesNoKeys')#все места в ряду
            for place in placesNoKeys:
                # [
                #     "IYWUMTBUHJATUMI",
                #     "1",
                #     4247.96,
                #     4227.93,
                #     "4 ROOLF",
                #     0,
                #     0
                # ]
                place_info = dict(
                    row = row_name,
                    place_number = place[1],
                    x = place[2] * SCALE_X if need_reformat else place[2],
                    y = place[3] * SCALE_Y if need_reformat else place[3],
                    some_name = place[4]
                )
                all_rows_and_seats.append(place_info)
    return all_rows_and_seats

def make_data_to_fill_svg(list_sector,
                          fill_sectors_with_seats=(
                                  ('fill', '#f0f8ff'),
                                  ('stroke', '#003153')
                          )):
    '''
    Структура для передачи в svg конвертер
    Создаем словарь с именами секторов и желаемым цветом для них
    Координаты нужны для создания текста на svg схеме

    fill="#ffffff" Определяет цвет заливки элемента
    fill-opacity="1.0" Определяет прозрачность заливки элемента.
    stroke="#dddddd" Определяет цвет обводки (границы) элемента
    stroke-opacity="1.0" Определяет прозрачность обводки элемента
    stroke-width="7.0" Определяет ширину обводки элемента.
    '''
    dict_with_all_sectors_and_their_coordinates = {}
    for sector in list_sector:
        dict_with_all_sectors_and_their_coordinates.setdefault(sector['name'], {}).update({
            'x': sector['x'],
            'y': sector['y'],
            'fill_rules': fill_sectors_with_seats,
            'text_about_sector': {
                'font-family': 'ArialMT, Arial',
                'font-size': '80',
                'fill-rule': 'nonzero',
                'fill': '#666',
                'font-weight': 'normal'
            }
        })
    return dict_with_all_sectors_and_their_coordinates