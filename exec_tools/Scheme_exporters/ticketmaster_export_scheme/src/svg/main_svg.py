from .reformat_svg import SVG

def work_with_svg(viewBox_width_new=7785,
            viewBox_height_new=5447,
            svg_width_new=7785,
            svg_height_new=5447):
    '''
    Инициализируем класс SVG
    Вычисляем константы для дальнейшего преобразования масштабов
    '''
    svg = SVG(viewBox_width_new=viewBox_width_new,
            viewBox_height_new=viewBox_height_new,
            svg_width_new=svg_width_new,
            svg_height_new=svg_height_new)
    print((svg.viewBox_width_original,
             svg.viewBox_height_original,
             svg.svg_width_original,
             svg.svg_height_original), 'THIS COORDINATES USING IN ticketmaster_svg.svg')

    SCALE_X = svg.SCALE_X #Значение для преобразования старых координат на новые
    SCALE_Y = svg.SCALE_Y
    print(SCALE_X, SCALE_Y, 'scale_x, scale_y POSITIONS CONSTANT')
    return SCALE_X, SCALE_Y, svg