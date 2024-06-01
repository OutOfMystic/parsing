from src.data_parse.main_data import formatting_json_data_and_write_in_file


if __name__ == '__main__':
    SCHEME_NAME = 'ETIHAD ARENA ticketmaster ICE'
    output_json_data = formatting_json_data_and_write_in_file(SCHEME_NAME)