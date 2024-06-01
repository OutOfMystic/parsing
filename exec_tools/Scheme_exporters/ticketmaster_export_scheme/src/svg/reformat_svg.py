import os
import re
import xml.etree.ElementTree as ET

from svgpathtools import parse_path, Path, Line, CubicBezier, QuadraticBezier, Arc

from ..loading.loading_files import file_path_for_REFORMAT_svg, file_path_for_svg

def scale_path_data(d, scale_x, scale_y):
    '''преобразование координат под новый размер
    d = <path d="M1685 658.112c0 449.564-352.21 816.85-795.72 840.87-6.86.372-12.62-5.119-12.62-11... >'''
    path = parse_path(d)
    scaled_path = Path()

    for element in path:
        if isinstance(element, Line):
            scaled_path.append(Line(
                start=complex(element.start.real * scale_x, element.start.imag * scale_y),
                end=complex(element.end.real * scale_x, element.end.imag * scale_y)
            ))
        elif isinstance(element, CubicBezier):
            scaled_path.append(CubicBezier(
                start=complex(element.start.real * scale_x, element.start.imag * scale_y),
                control1=complex(element.control1.real * scale_x, element.control1.imag * scale_y),
                control2=complex(element.control2.real * scale_x, element.control2.imag * scale_y),
                end=complex(element.end.real * scale_x, element.end.imag * scale_y)
            ))
        elif isinstance(element, QuadraticBezier):
            scaled_path.append(QuadraticBezier(
                start=complex(element.start.real * scale_x, element.start.imag * scale_y),
                control=complex(element.control.real * scale_x, element.control.imag * scale_y),
                end=complex(element.end.real * scale_x, element.end.imag * scale_y)
            ))
        elif isinstance(element, Arc):
            scaled_path.append(Arc(
                start=complex(element.start.real * scale_x, element.start.imag * scale_y),
                radius=element.radius * scale_x,  # Assuming uniform scaling
                rotation=element.rotation,
                arc=element.arc,
                sweep=element.sweep,
                end=complex(element.end.real * scale_x, element.end.imag * scale_y)
            ))

    return scaled_path.d()

class SVG:
    current_dir = os.getcwd()
    def __init__(self,
                 viewBox_width_new=7785,
                 viewBox_height_new=5447,
                 svg_width_new=7785,
                 svg_height_new=5447
                 ):
        self.path_to_svg = file_path_for_svg
        self.path_to_reformat_svg = file_path_for_REFORMAT_svg

        self.viewBox_width_new = viewBox_width_new
        self.viewBox_height_new = viewBox_height_new
        self.svg_width_new = svg_width_new
        self.svg_height_new = svg_height_new

        (self.svg_width_original,
         self.svg_height_original,
         self.viewBox_width_original,
         self.viewBox_height_original) = self.find_width_and_height()

        (self.SCALE_X,
         self.SCALE_Y) = self.set_scales()

    def find_width_and_height(self):
        '''
        Поиск размеров по умолчанию
        '''
        with open(self.path_to_svg, 'r', encoding='utf-8') as svg_file:
            # Читаем первые строки файла (предположим, что нужные нам атрибуты находятся в первых 10 строках)
            #<svg width="1024px" height="768px" viewBox="0 0 10240 7680" x="0px" y="0px"
            lines = []
            for _ in range(10):
                line = svg_file.readline()
                if not line:
                    break
                lines.append(line)
            svg_data = ''.join(lines)
        width = re.search(r'width="([\d]+)', svg_data)
        height = re.search(r'height="(\d+)', svg_data)
        viewBox = re.search(r'viewBox="([^"]+)"', svg_data)

        width_value = width.group(1) if width else None
        height_value = height.group(1) if height else None
        viewBox_value = viewBox.group(1) if viewBox else None
        *_, viewBox_width_original, viewBox_height_original = viewBox_value.split()
        #print(viewBox_width_original, viewBox_height_original, 'viewBox_width_original, viewBox_height_original')
        #print(list(map(int, (width_value, height_value, viewBox_width_original, viewBox_height_original))))
        return map(int, (width_value, height_value, viewBox_width_original, viewBox_height_original))

    def set_scales(self):
        '''
        Вычисляем значение для преобразования старых координат на новые
        '''
        #print(self.viewBox_width_new ,self.viewBox_width_original, 'self.viewBox_width_new / self.viewBox_width_original')
        #print(self.viewBox_height_new,self.viewBox_height_original, 'self.viewBox_height_new / self.viewBox_height_original')
        scale_x = self.viewBox_width_new / self.viewBox_width_original
        scale_y = self.viewBox_height_new / self.viewBox_height_original
        return scale_x, scale_y

    def add_text_element(self, parent_element, sector_info, element_id):
        # Создание элемента <text> с нужными атрибутами
        text_elem = ET.Element('text', sector_info.get('text_about_sector'))

        # Создание подэлемента <tspan> с нужными атрибутами и текстом
        tspan_elem = ET.SubElement(text_elem, 'tspan', {
            'x': str(sector_info.get('x')),
            'y': str(sector_info.get('y'))
        })
        tspan_elem.text = str(element_id)

        # Добавление <text> элемента в родительский элемент
        parent_element.append(text_elem)
    def make_new_svg(self,
                     dict_with_all_sectors_and_their_coordinates=None,
                     need_reformat=True,
                     need_fill=False):
        '''
        Создание нового svg, согласно желаемым масштабам
        '''
        # Чтение SVG
        tree = ET.parse(self.path_to_svg)
        root = tree.getroot()
        sectors_we_looked_before = set()
        # Обработка каждого <path> в SVG и его изменение
        for elem in root.findall('.//{http://www.w3.org/2000/svg}path'):
            d = elem.attrib['d']
            if need_reformat:
                scaled_d = scale_path_data(d, self.SCALE_X, self.SCALE_Y)
            else:
                scaled_d = d
            elem.attrib['d'] = scaled_d
            element_id = elem.attrib.get('id').upper()
            #обработка секторов с местами в них
            if (element_id in dict_with_all_sectors_and_their_coordinates
                    and element_id not in sectors_we_looked_before):
                #print(element_id, 'FINDING')
                sectors_we_looked_before.add(element_id)
                sector_info = dict_with_all_sectors_and_their_coordinates.get(element_id)
                if need_fill:
                    for name_attribute, value in sector_info.get('fill_rules'):
                        #('fill', '#888')
                        elem.attrib[name_attribute] = value
                if sector_info.get('text_about_sector'):
                    self.add_text_element(root, sector_info, element_id)
            else:
                #print(element_id, 'ELSE')
                for name_sector in dict_with_all_sectors_and_their_coordinates.keys():
                    if (name_sector in element_id and
                            name_sector not in sectors_we_looked_before):
                        sectors_we_looked_before.add(name_sector)
                        sector_info = dict_with_all_sectors_and_their_coordinates.get(name_sector)
                        if need_fill:
                            for name_attribute, value in sector_info.get('fill_rules'):
                                # ('fill', '#888')
                                elem.attrib[name_attribute] = value
                        if sector_info.get('text_about_sector'):
                            self.add_text_element(root, sector_info, name_sector)
        if need_reformat:
            new_root = ET.Element('svg', {
                'width': f'{self.svg_width_new}px',
                'height': f'{self.svg_height_new}px',
                'viewBox': f'0 0 {self.viewBox_width_new} {self.viewBox_height_new}'

            })
        else:
            new_root = ET.Element('svg', {
                'width': f'{self.svg_width_original}px',
                'height': f'{self.svg_height_original}px',
                'viewBox': f'0 0 {self.viewBox_width_original} {self.viewBox_height_original}'

            })
        # Копирование всех элементов из старого root в новый root
        for elem in root:
            new_root.append(elem)
        # Сохранение измененного SVG
        tree = ET.ElementTree(new_root)
        # Переход к корректному формату тегов в строке
        ET.register_namespace("", "http://www.w3.org/2000/svg")  # Регистрация пространства имен для корректного вывода
        with open(self.path_to_reformat_svg, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)
        # Открытие и перезапись файла для замены <svg:path> на <path>
        with open(self.path_to_reformat_svg, 'r', encoding='utf-8') as file:
            filedata = file.read()
        filedata = filedata.replace('<svg:path', '<path').replace('</svg:path', '</path')
        with open(self.path_to_reformat_svg, 'w', encoding='utf-8') as file:
            file.write(filedata)
