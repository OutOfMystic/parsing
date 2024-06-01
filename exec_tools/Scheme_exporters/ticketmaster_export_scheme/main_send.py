from src.send.send_to_server import send_json_data_on_server
from src.loading.loading_files import get_file_to_export

if __name__ == "__main__":
    SCHEME_NAME = 'ETIHAD ARENA ticketmaster ICE'
    SCHEME_VENUE = 'ETIHAD ARENA'

    output_json_data = get_file_to_export(SCHEME_NAME)
    if output_json_data is not None:
        send_to_server = send_json_data_on_server(
                        output_json_data=output_json_data,
                        name_scheme=SCHEME_NAME,
                        venue_scheme=SCHEME_VENUE,
                        url_to_send='http://193.178.170.180')
    else:
        print('CANNOT FIND', SCHEME_NAME)