import json


def _get_sector_data(get_all_sector_with_svg_path: json) -> dict[str, str]:
    sectors_data = {}
    all_sector = get_all_sector_with_svg_path['sectors']
    for sector in all_sector:
        sector_name = sector.get('i')
        sector_path_in_svg = sector.get('o')
        if sector_path_in_svg:
            sectors_data[sector_name] = sector_path_in_svg
    return sectors_data


def _get_coordinates_seats_generator(
    get_all_seats: json
) -> list[tuple[int, ...]]:
    coordinates_seats = []
    all_seats = get_all_seats['coordinates']
    for seat in all_seats:
        x = seat['x']
        y = seat['y']
        coordinates_seats.append((x, y))
    return coordinates_seats
