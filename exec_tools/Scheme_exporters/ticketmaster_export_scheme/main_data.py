from src.loading.loading_files import (loading_all_data_from_ticketmaster,
                                       write_list_to_json)
from src.svg.main_svg import work_with_svg
from src.data_parse.main_data import (get_data_with_all_sectors,
                                      make_structure_with_all_sectors_and_seats)
from src.data_parse.work_with_data import make_data_to_fill_svg

def prepare_and_work_with_data(NEED_REF=True):
    #Загрузка файлов
    url_with_seats = 'https://mapsapi.tmol.co/maps/geometry/3/event/10709/placeDetailNoKeys?systemId=MFX&useHostGrids=true&domain=UnitedArabEmirates&app=PRD1741_ICCP-FE'
    #'https://mapsapi.tmol.co/maps/geometry/3/event/10705/placeDetailNoKeys?systemId=MFX&useHostGrids=true&domain=UnitedArabEmirates&app=PRD1741_ICCP-FE'
    #input('Enter the URL having information about all places')
    url_with_svg = 'https://mapsapi.tmol.co/maps/geometry/image/33/39/333922?removeFilters=ISM_Shadow&tmSansFonts=true&app=PRD1741_ICCP-FE'
    #'https://mapsapi.tmol.co/maps/geometry/image/33/56/335692?removeFilters=ISM_Shadow&tmSansFonts=true&app=PRD1741_ICCP-FE'
    #input('Enter the URL with svg scheme')
    loading_all_data_from_ticketmaster(url_with_seats, url_with_svg)

    #SCALE_X, SCALE_Y - Константы для преобразования в новых масштабах схемы svg
    #Задаем желаемые масштабы новой схемы svg
    #ticketmaster_svg.svg - базовая(родная) схема
    #ticketmaster_svg_FINISH.svg - схема после манипуляций с размерами
    SCALE_X, SCALE_Y, svg = work_with_svg(
                viewBox_width_new=7785,
                viewBox_height_new=5447,
                svg_width_new=7785,
                svg_height_new=5447
    )

    #словарь со всеми секторами и их данными
    data_with_all_sectors = get_data_with_all_sectors(SCALE_X,SCALE_Y,
                                                      need_reformat=NEED_REF)
    list_sector, list_seats = make_structure_with_all_sectors_and_seats(data_with_all_sectors,
                                                                        SCALE_X,SCALE_Y,
                                                                        need_reformat=NEED_REF)
    print('total SECTORS count:', len(list_sector))
    print('total SEATS  count', len(list_seats))


    #параметры цвета для секторов с местами
    dict_with_all_sectors_and_their_coordinates = make_data_to_fill_svg(
                        list_sector,
        (('fill', '#f0f8ff'),
                        ('stroke', '#003153')))
    #редактирование ticketmaster_svg.svg и создание ticketmaster_svg_FINISH.svg
    svg.make_new_svg(dict_with_all_sectors_and_their_coordinates,
                     need_reformat=NEED_REF,
                     need_fill=False)

    write_list_to_json(list_sector, 'list_sector') #list_sector запись
    write_list_to_json(list_seats, 'list_seats') #list_seats


if __name__ == '__main__':
    prepare_and_work_with_data(NEED_REF=True)
