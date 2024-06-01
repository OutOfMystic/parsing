import json

from ..data_processing_after_receipt.conversion_data_seats_and_sectors import _conversion_data_seats_and_sectors
from ..data_processing_after_receipt.get_sector_data_and_coordinate import (_get_coordinates_seats_generator,
                                                                          _get_sector_data)


def processing_data_to_json_data(
    get_svg_scheme: str,#get_svg_scheme.svg
    get_all_sector_with_svg_path: json,# {'Ложа 4, стол 36': ' M149.0 675.0 L207.0 675.0 C213.6274185180664...' , }
    get_all_seats: json,# [(39.0, 479.0), (59.0, 479.0), (39.0, 610.0), (59.0, 610.0),...]
    correct_all_sectors
) -> tuple[list]:
    sectors_data = _get_sector_data(get_all_sector_with_svg_path)
    coordinates_seats = _get_coordinates_seats_generator(get_all_seats)
    sectors_for_json, seats_for_json = _conversion_data_seats_and_sectors(
        get_svg_scheme,
        sectors_data,
        coordinates_seats,
        correct_all_sectors
    )
    # sectors_for_json {'name': 'Ложа 4, стол 36', 'x': 129.308, 'y': 564.0, 'outline': ' M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0
    # 219.0 680.3725829124451 219.0 687.0 L219.0 753.0 C219.0 759.6274185180664 213.6274185180664
    # 765.0 207.0 765.0 L149.0 765.0 C142.37258291244507 765.0 137.0 759.6274185180664 137.0 753.0
    # L137.0 687.0 C137.0 680.3725829124451 142.37258291244507 675.0 149.0 675.0 Z', ...}
    # seats_for_json[[158.0, 710.0, 0, 0, 0, 0, 0], [158.0, 730.0, 0, 0, 0, 0, 0], [178.0, 744.0, 0, 0, 0, 0, 0], [198.0, 744.0, 0, 0, 0, 0, 0], ...]
    return sectors_for_json, seats_for_json
