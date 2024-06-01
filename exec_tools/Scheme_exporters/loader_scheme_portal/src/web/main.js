let data_to_send = {}

async function post_inform() {
    let input_url = document.querySelector("#input_url");
    let input_name = document.querySelector("#input_name");
    let input_venue = document.querySelector("#input_venue");
    let input_time_sleep = document.querySelector("#input_time_sleep");
    let input_correct_all_sectors = document.querySelector("#input_correct_all_sectors");
    let input_url_value = input_url.value;
    let input_name_value = input_name.value;
    let input_venue_value = input_venue.value;
    let input_time_sleep_value = input_time_sleep.value;
    let input_correct_all_sectors_value = input_correct_all_sectors.checked; // true or false
    let result = await eel.post_inform(
        input_url_value,
        input_name_value,
        input_venue_value,
        input_time_sleep_value,
        input_correct_all_sectors_value
    )();
    document.querySelector("#result").innerHTML = result;
    post_inform_button.disabled = false;
}

let post_inform_button = document.querySelector("#post_inform");
post_inform_button.addEventListener("click", function() {
    document.querySelector("#result").innerHTML = '';
    post_inform_button.disabled = true;
    post_inform();
})

eel.expose(update_seats_in_sector);
function update_seats_in_sector(list_seats_in_this_sector, sector_name) {
    let h1 = document.createElement('h1');
    h1.id = 'sector_name';
    h1.innerHTML = sector_name;
    document.querySelector('body').appendChild(h1);

    let data_for_table = create_data_for_table(list_seats_in_this_sector);
    let array_coordinate = data_for_table[0];
    let max_x_coordinate = data_for_table[1];
    let max_y_coordinate = data_for_table[2];
    let min_x_coordinate = data_for_table[3];
    let min_y_coordinate = data_for_table[4];
    create_table(array_coordinate, max_x_coordinate, max_y_coordinate, min_x_coordinate, min_y_coordinate);
    return
}

function create_data_for_table(dict_data_input) {
    let max_x_coordinate = -1;
    let max_y_coordinate = -1;
    let min_x_coordinate = 1000000;
    let min_y_coordinate = 1000000;

    let array_coordinate = [];
    for (const [key, value] of Object.entries(dict_data_input)) {
        let coordinates = key.split(' ');
        let coordinate_x = Math.round(coordinates[0]);
        let coordinate_y = Math.round(coordinates[1]);
        array_coordinate.push([coordinate_x, coordinate_y]);
        if (coordinate_x > max_x_coordinate) {
            max_x_coordinate = coordinate_x;
        };
        if (coordinate_y > max_y_coordinate) {
            max_y_coordinate = coordinate_y;
        };
        if (coordinate_x < min_x_coordinate) {
            min_x_coordinate = coordinate_x;
        };
        if (coordinate_y < min_y_coordinate) {
            min_y_coordinate = coordinate_y;
        };

        data_to_send[`${coordinate_x} ${coordinate_y}`] = value;
    }
    
    return [array_coordinate, max_x_coordinate, max_y_coordinate, min_x_coordinate, min_y_coordinate]
}

function create_table(array_coordinate, max_x_coordinate, max_y_coordinate, min_x_coordinate, min_y_coordinate) {
    const range_coordinate_x = max_x_coordinate - min_x_coordinate;
    const range_coordinate_y = max_y_coordinate - min_y_coordinate;
    const all_coordinate_to_svg = `${min_x_coordinate-20} ${min_y_coordinate-20} ${range_coordinate_x+40} ${range_coordinate_y+40}`;

    const iconSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    iconSvg.setAttribute('fill', 'none');
    iconSvg.setAttribute('viewBox', all_coordinate_to_svg);
    iconSvg.setAttribute('stroke', 'none');
    iconSvg.id = 'main_svg';

    for (coordinate of array_coordinate) {
        let iconCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        iconCircle.setAttributeNS(null, 'cx', new String(coordinate[0]));
        iconCircle.setAttributeNS(null, 'cy', new String(coordinate[1]));
        iconCircle.setAttributeNS(null, 'r', 10);
        iconCircle.classList.add('is_real_coordinate');
        iconCircle.classList.add(`${new String(coordinate[0])},${new String(coordinate[1])}`);

        iconSvg.appendChild(iconCircle);
    }
    document.querySelector('body').appendChild(iconSvg);

    create_input_and_button();
}

function create_input_and_button() {
    let div_for_content = document.createElement('div');
    div_for_content.className = 'div_for_content';

    let div_for_no_auto = document.createElement('div');
    div_for_no_auto.className = 'div_for_no_auto';

    let button_to_update = document.createElement('button');
    button_to_update.id = 'button_to_update_not_auto';
    button_to_update.innerHTML = 'Закрепить ряд и места в нем или ctrl+q';
    div_for_no_auto.appendChild(button_to_update);

    let button_reset_last_click = document.createElement('button');
    button_reset_last_click.id = 'button_reset_last_click';
    button_reset_last_click.innerHTML = 'Отменить последнее выделение места или ctrl+z';
    div_for_no_auto.appendChild(button_reset_last_click);
    
    let button_reset_last_row = document.createElement('button');
    button_reset_last_row.id = 'button_reset_last_row';
    button_reset_last_row.innerHTML = 'Отменить последний ряд';
    div_for_no_auto.appendChild(button_reset_last_row);
    
    let input_number_row = document.createElement('input');
    input_number_row.id = 'number_row';
    input_number_row.value = 1;
    input_number_row.placeholder = 'Выбор ряда';
    div_for_no_auto.appendChild(input_number_row);

    let input_number_seat = document.createElement('input');
    input_number_seat.id = 'number_seat';
    input_number_seat.value = 1;
    input_number_seat.placeholder = 'Выбор места';
    div_for_no_auto.appendChild(input_number_seat);

    let input_danse_seat = document.createElement('input');
    input_danse_seat.id = 'danse_seat';
    input_danse_seat.value = 0;
    input_danse_seat.placeholder = 'Если 1 то место для танцпола';
    div_for_no_auto.appendChild(input_danse_seat);

    div_for_content.appendChild(div_for_no_auto);

    let div_for_auto = document.createElement('div');
    div_for_auto.className = 'div_for_auto';

    let auto_text = document.createElement('span');
    auto_text.id = 'auto_text';
    div_for_auto.appendChild(auto_text);

    let input_row = document.createElement('input');
    input_row.id = 'auto_update_row';
    input_row.placeholder = 'Выбор направления рядов для автоматического обнавления: 0 на лево а 1 на право 2 вверх 3 вниз';
    div_for_auto.appendChild(input_row);

    let input_seat = document.createElement('input');
    input_seat.id = 'auto_update_seats';
    input_seat.placeholder = 'Выбор направления мест для автоматического обнавления: 0 на лево а 1 на право 2 вверх 3 вниз';
    div_for_auto.appendChild(input_seat);

    let input_first_row = document.createElement('input');
    input_first_row.id = 'first_row';
    input_first_row.value = '1';
    input_first_row.placeholder = 'С какого номера начинается ряд';
    div_for_auto.appendChild(input_first_row);
    
    let input_first_seat = document.createElement('input');
    input_first_seat.id = 'first_seat';
    input_first_seat.value = '1';
    input_first_seat.placeholder = 'С какого номера начинаются места';
    div_for_auto.appendChild(input_first_seat);

    let button_auto = document.createElement('button');
    button_auto.style['display'] = 'block';
    button_auto.id = 'auto_update';
    button_auto.innerHTML = 'Автоматичекое обновление сектора';
    div_for_auto.appendChild(button_auto);
    
    div_for_content.appendChild(div_for_auto);

    let div_for_management = document.createElement('div');
    div_for_management.className = 'div_for_management';

    let informathion_text = document.createElement('span');
    informathion_text.id = 'informathion_text';
    div_for_management.appendChild(informathion_text);

    let button = document.createElement('button');
    button.id = 'send_sector';
    button.innerHTML = 'отправить сектор';
    div_for_management.appendChild(button);
    
    let button_reset = document.createElement('button');
    button_reset.id = 'button_reset';
    button_reset.innerHTML = 'Сброс сектора';
    div_for_management.appendChild(button_reset);
    
    let button_origin_svg = document.createElement('button');
    button_origin_svg.id = 'button_origin_svg';
    button_origin_svg.innerHTML = 'обычная высота svg или 1000px';
    div_for_management.appendChild(button_origin_svg);

    div_for_content.appendChild(div_for_management);
    
    document.querySelector('body').appendChild(div_for_content);
}

let sector_is_good_is_work = true;
function start_update() {
    setInterval(function() {
        if (sector_is_good_is_work == true) {
            let button = document.querySelectorAll('button#send_sector');
            if (button.length > 0) {
                sector_is_good_is_work = false;
                sector_is_good();
            }
        }
    }, 2000);
}

start_update()

function sector_is_good() {
    let button_origin_svg = document.querySelector('#button_origin_svg')
    let check_status_svg = 0
    button_origin_svg.addEventListener('click', function() {
        if (check_status_svg == 0) {
            let svg = document.querySelector('svg')
            svg.style['display'] = 'inline'
            svg.style['height'] = 'auto'
            let all_circle = document.querySelectorAll('circle')
            for (let circle of all_circle) {
                circle.setAttribute('r', '5')
            }
            check_status_svg = 1
        }
        else {
            let svg = document.querySelector('svg')
            svg.style['display'] = 'block'
            svg.style['height'] = '1000px'
            let all_circle = document.querySelectorAll('circle')
            for (let circle of all_circle) {
                circle.setAttribute('r', '10')
            }
            check_status_svg = 0
        }
    })
    let data_to_send_in_python = [];
    let all_circle = document.querySelectorAll('.is_real_coordinate');
    let circle_is_final = [];
    let circle_is_ready = [];
    let row_circle_is_final = [];
    let row_text_is_final = [];
    let row_data_is_final = [];

    function check_count_list() {
        remove_all_event_to_remove_final_circle()
        add_event_to_remove_final_circle()
        const data_to_ready = data_to_send_in_python.length;
        const all_data = Object.keys(data_to_send).length;
        let informathion_text = document.querySelector('#informathion_text')
        informathion_text.innerHTML = `готово ${data_to_ready} из ${all_data}`
    }

    const event_to_remove_final_circle = ( circle ) => ( event ) => {
        if ((event.ctrlKey || event.metaKey) && ('is_ready_real_coordinate' == circle.classList[0])) {
            const index = circle_is_final.indexOf(circle);
            if (index > -1) {
                circle_is_final.splice(index, 1);
            }
            let coordinate = circle.classList[1].split(',');
            
            let text_in_svg = document.querySelector(`text[x='${coordinate[0]}'][y='${coordinate[1]}']`)
            if (text_in_svg == null) {
                return
            }
            const row_and_seat = text_in_svg.textContent.split('-')
            const row = row_and_seat[0]
            const seat = row_and_seat[1]
            for (text_in_data of row_text_is_final) {
                const index_in_text = text_in_data.indexOf(text_in_svg);
                if (index_in_text > -1) {
                    text_in_data.splice(index_in_text, 1);
                    break
                }
            }
            text_in_svg.remove();

            let str_coordinate_to_find = coordinate[0] + ' ' + coordinate[1];
            let get_data_in_data_dict = JSON.parse(data_to_send[str_coordinate_to_find]);
            get_data_in_data_dict.push(+row)
            get_data_in_data_dict.push(+seat)
            
            let count_index = 0
            let index_in_final_array = -1;
            for (data of data_to_send_in_python) {
                if (get_data_in_data_dict.toString() == data.toString()){
                    index_in_final_array = count_index;
                    break
                }
                count_index += 1
            }
            
            if (index_in_final_array > -1) {
                data_to_send_in_python.splice(index_in_final_array, 1);
            }
            
            for (data_row of row_data_is_final) {
                let index_in_data = 0
                let index_in_final_array = -1;
                for (data of data_row) {
                    if (get_data_in_data_dict.toString() == data.toString()){
                        index_in_final_array = index_in_data;
                        if (index_in_data > -1) {
                            data_row.splice(index_in_data, 1);
                        }
                        break
                    }
                    index_in_data += 1
                }
            }

            for (circle_in_data of row_circle_is_final) {
                const index_in_circle = circle_in_data.indexOf(circle);
                if (index_in_circle > -1) {
                    circle_in_data.splice(index_in_circle, 1);
                    break
                }
            }
            
            circle.classList = 'is_real_coordinate ' + coordinate[0] + ',' + coordinate[1];
            remove_event_to_remove_final_circle(circle)
        }
    }

    function add_event_to_remove_final_circle() {
        let all_final_circle = document.querySelectorAll('.is_ready_real_coordinate');
        for (let circle of all_final_circle) {
            circle.addEventListener('mousemove', event_to_remove_final_circle(circle))
        }
    }
    
    function remove_event_to_remove_final_circle(circle) {
        circle.removeEventListener('mousemove', event_to_remove_final_circle)
    }
    function remove_all_event_to_remove_final_circle() {
        let all_final_circle = document.querySelectorAll('.is_ready_real_coordinate');
        for (let circle of all_final_circle) {
            circle.removeEventListener('mousemove', event_to_remove_final_circle)
        }
    }

    for (let circle of all_circle) {
        circle.addEventListener('mousemove', function(event) {
            if ((circle_is_ready.indexOf(circle) == -1) && (circle_is_final.indexOf(circle) == -1) && !(event.ctrlKey || event.metaKey)) {
                if (!('is_ready_real_coordinate' in circle.classList)) {
                    let coordinate = circle.classList[1].split(',')
                    circle.classList = 'is_choice_real_coordinate ' + coordinate[0] + ',' + coordinate[1];
                    circle_is_ready.push(circle);
                    circle_is_final.push(circle);
                }
            }
        })
    }

    let button_to_update_not_auto = document.querySelector('button#button_to_update_not_auto');
    function update_not_auto() {
        let this_circle = [];
        let this_text = [];
        let this_data = [];

        let seat = +document.querySelector('input#number_seat').value;
        for (let circle of circle_is_ready) {
            let coordinate = circle.classList[1].split(',');
            circle.classList = 'is_ready_real_coordinate ' + coordinate[0] + ',' + coordinate[1];
            let str_coordinate_to_find = coordinate[0] + ' ' + coordinate[1];
            let get_data_in_data_dict = JSON.parse(data_to_send[str_coordinate_to_find]);
            let row = +document.querySelector('input#number_row').value;

            get_data_in_data_dict.push(row);
            get_data_in_data_dict.push(seat);
            data_to_send_in_python.push(get_data_in_data_dict);

            const iconSvg = document.querySelector('svg')
            const seatAndRow = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            seatAndRow.setAttributeNS(null, 'x', new String(coordinate[0]));
            seatAndRow.setAttributeNS(null, 'y', new String(coordinate[1]));
            seatAndRow.setAttributeNS(null, 'text-anchor', 'middle');
            seatAndRow.setAttributeNS(null, 'dominant-baseline', 'middle');
            seatAndRow.setAttributeNS(null, 'stroke', 'black');
            seatAndRow.setAttributeNS(null, 'stroke-width', '.5px');
            seatAndRow.innerHTML = `<tspan class="tspan_row">${row}</tspan>-${seat}`;
            seatAndRow.classList.add('for_remove');
            iconSvg.appendChild(seatAndRow);

            seat += 1;

            this_circle.push(circle);
            this_text.push(seatAndRow);
            this_data.push(get_data_in_data_dict);
        }
        let number_row = document.querySelector('input#number_row')
        number_row.value = new Number(number_row.value) + 1
        all_circle = document.querySelectorAll('.is_real_coordinate');
        circle_is_ready = [];
        row_circle_is_final.push(this_circle);
        row_text_is_final.push(this_text);
        row_data_is_final.push(this_data);
        check_count_list()
    }
    button_to_update_not_auto.addEventListener('click', update_not_auto)
    document.addEventListener('keydown', function(event) {
        if (event.code == 'KeyQ' && (event.ctrlKey || event.metaKey) && (circle_is_ready.length > 0)) {
            let this_circle = [];
            let this_text = [];
            let this_data = [];

            let danse_seat = +document.querySelector('input#danse_seat').value;
            let seat = +document.querySelector('input#number_seat').value;
            for (let circle of circle_is_ready) {
                let coordinate = circle.classList[1].split(',');
                circle.classList = 'is_ready_real_coordinate ' + coordinate[0] + ',' + coordinate[1];
                let str_coordinate_to_find = coordinate[0] + ' ' + coordinate[1];
                let get_data_in_data_dict = JSON.parse(data_to_send[str_coordinate_to_find]);
                let row = +document.querySelector('input#number_row').value;

                get_data_in_data_dict.push(row);
                get_data_in_data_dict.push(seat);
                if (danse_seat == 1) {
                    get_data_in_data_dict.push(1)
                }
                data_to_send_in_python.push(get_data_in_data_dict);

                const iconSvg = document.querySelector('svg')
                const seatAndRow = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                seatAndRow.setAttributeNS(null, 'x', new String(coordinate[0]));
                seatAndRow.setAttributeNS(null, 'y', new String(coordinate[1]));
                seatAndRow.setAttributeNS(null, 'text-anchor', 'middle');
                seatAndRow.setAttributeNS(null, 'dominant-baseline', 'middle');
                seatAndRow.setAttributeNS(null, 'stroke', 'black');
                seatAndRow.setAttributeNS(null, 'stroke-width', '.5px');
                seatAndRow.innerHTML = `<tspan class="tspan_row">${row}</tspan>-${seat}`;
                seatAndRow.classList.add('for_remove');
                iconSvg.appendChild(seatAndRow);

                seat += 1;

                this_circle.push(circle);
                this_text.push(seatAndRow);
                this_data.push(get_data_in_data_dict);
            }
            let number_row = document.querySelector('input#number_row')
            number_row.value = new Number(number_row.value) + 1
            all_circle = document.querySelectorAll('.is_real_coordinate');
            circle_is_ready = [];
            row_circle_is_final.push(this_circle);
            row_text_is_final.push(this_text);
            row_data_is_final.push(this_data);
            check_count_list()
        }
    })

    let button_reset_last_click = document.querySelector('button#button_reset_last_click');
    function reset_last_click() {
        let last_element = circle_is_ready.pop();
        let coordinate = last_element.classList[1];
        circle_is_final.pop();
        last_element.classList = 'is_real_coordinate ' + coordinate.split(',')[0] + ',' + coordinate.split(',')[1];
        all_circle = document.querySelectorAll('.is_real_coordinate');
    }
    button_reset_last_click.addEventListener('click', reset_last_click);
    document.addEventListener('keydown', function(event){
        if (event.code == 'KeyZ' && (event.ctrlKey || event.metaKey) && (circle_is_ready.length > 0)) {
            let last_element = circle_is_ready.pop();
            let coordinate = last_element.classList[1];
            circle_is_final.pop();
            last_element.classList = 'is_real_coordinate ' + coordinate.split(',')[0] + ',' + coordinate.split(',')[1];
            all_circle = document.querySelectorAll('.is_real_coordinate');
        }
    });

    let button_reset_last_row = document.querySelector('button#button_reset_last_row');
    button_reset_last_row.addEventListener('click', function() {
        reset_circle = row_circle_is_final.pop();
        reset_text = row_text_is_final.pop();
        reset_data = row_data_is_final.pop();
        for (let circle of circle_is_ready) {
            let last_element = circle;
            let coordinate = last_element.classList[1];
            circle_is_final.pop();
            last_element.classList = 'is_real_coordinate ' + coordinate.split(',')[0] + ',' + coordinate.split(',')[1];
        }
        circle_is_ready = [];
        for (let circle of reset_circle) {
            let coordinate = circle.classList[1];
            circle_is_final.pop();
            circle.classList = 'is_real_coordinate ' + coordinate.split(',')[0] + ',' + coordinate.split(',')[1];
        }
        for (let text of reset_text) {
            text.remove();
        }
        const old_length_array = data_to_send_in_python.length - reset_data.length
        data_to_send_in_python = data_to_send_in_python.slice(0, old_length_array)

        all_circle = document.querySelectorAll('.is_real_coordinate');
        check_count_list()
    });

    let button_reset = document.querySelector('button#button_reset');
    button_reset.addEventListener('click', function() {
        remove_all_event_to_remove_final_circle()
        data_to_send_in_python = [];
        let all_circle_is = document.querySelectorAll('[class^="is_"');
        for (let circle of all_circle_is) {
            let coordinate = circle.classList[1]
            circle.classList = 'is_real_coordinate ' + coordinate.split(',')[0] + ',' + coordinate.split(',')[1];
        }
        let all_text_tag = document.querySelectorAll('text.for_remove')
        for (let text_tag of all_text_tag) {
            text_tag.remove();
        }
        circle_is_ready = [];
        circle_is_final = [];
        row_circle_is_final = [];
        row_text_is_final = [];
        row_data_is_final = [];
        
        all_circle = document.querySelectorAll('.is_real_coordinate');
        check_count_list()
    });

    let auto_update = document.querySelector('button#auto_update');
    auto_update.addEventListener('click', function() {
        let auto_update_row = new Number(document.querySelector('input#auto_update_row').value);
        let auto_update_seats = new Number(document.querySelector('input#auto_update_seats').value);
        let number_first_row = new Number(document.querySelector('input#first_row').value);
        let number_first_seat = new Number(document.querySelector('input#first_seat').value);

        let dict_coordinate_y = {};
        let dict_coordinate_x = {};
        let all_circle_for_auto_update = document.querySelectorAll('circle.is_real_coordinate')
        for (let circle of all_circle_for_auto_update) {
            circle_is_final.push(circle);

            let coordinate = circle.classList[1].split(',');
            let str_coordinate_to_find = coordinate[0] + ' ' + coordinate[1];
            let str_coordinate_y = coordinate[1];
            let str_coordinate_x = coordinate[0];

            if (str_coordinate_y in dict_coordinate_y) {
                dict_coordinate_y[str_coordinate_y].push(str_coordinate_to_find);
            }
            else {
                dict_coordinate_y[str_coordinate_y] = [];
                dict_coordinate_y[str_coordinate_y].push(str_coordinate_to_find);
            }

            if (str_coordinate_x in dict_coordinate_x) {
                dict_coordinate_x[str_coordinate_x].push(str_coordinate_to_find);
            }
            else {
                dict_coordinate_x[str_coordinate_x] = [];
                dict_coordinate_x[str_coordinate_x].push(str_coordinate_to_find);
            }
        }

        function auto_update_with_data(list_for_seat, row) {
            let seat = number_first_seat;
            for (coordinate of list_for_seat) {
                const this_coordinate = coordinate.split(' ')
                let str_coordinate_to_find = this_coordinate[0] + ' ' + this_coordinate[1];
                let get_data_in_data_dict = JSON.parse(data_to_send[str_coordinate_to_find]);

                get_data_in_data_dict.push(+row);
                get_data_in_data_dict.push(seat);
                data_to_send_in_python.push(get_data_in_data_dict);

                let this_circle = document.querySelector(`circle[cx='${this_coordinate[0]}'][cy='${this_coordinate[1]}']`)
                let js_coordinate = this_coordinate[0] + ',' + this_coordinate[1]
                console.log(this_circle, js_coordinate)
                this_circle.classList = 'is_ready_real_coordinate ' + js_coordinate;

                const iconSvg = document.querySelector('svg')
                const seatAndRow = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                seatAndRow.setAttributeNS(null, 'x', new String(this_coordinate[0]));
                seatAndRow.setAttributeNS(null, 'y', new String(this_coordinate[1]));
                seatAndRow.setAttributeNS(null, 'text-anchor', 'middle');
                seatAndRow.setAttributeNS(null, 'dominant-baseline', 'middle');
                seatAndRow.setAttributeNS(null, 'stroke', 'black');
                seatAndRow.setAttributeNS(null, 'stroke-width', '.5px');
                seatAndRow.innerHTML = `<tspan class="tspan_row">${row}</tspan>-${seat}`;
                seatAndRow.classList.add('for_remove');
                iconSvg.appendChild(seatAndRow);

                seat += 1;
            }
        }
        
        let row = number_first_row;
        if (auto_update_row == 2) {
            for (const [key, value] of Object.entries(dict_coordinate_y).reverse()) {
                let list_for_seat = [];
                for (coordinate of value) {
                    list_for_seat.push(coordinate)
                }
                if (auto_update_seats == 0) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[0]);
                        const second_number = new Number(b.split(' ')[0]);
                        return second_number - first_number;
                    });
                }
                else if (auto_update_seats == 1) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[0]);
                        const second_number = new Number(b.split(' ')[0]);
                        return first_number - second_number;
                    });
                }
                auto_update_with_data(list_for_seat, row);
                row += 1;
            }
        }
        else if (auto_update_row == 3) {
            for (const [key, value] of Object.entries(dict_coordinate_y)) {
                let list_for_seat = [];
                for (coordinate of value) {
                    list_for_seat.push(coordinate)
                }
                if (auto_update_seats == 0) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[0]);
                        const second_number = new Number(b.split(' ')[0]);
                        return second_number - first_number;
                    });
                }
                else if (auto_update_seats == 1) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[0]);
                        const second_number = new Number(b.split(' ')[0]);
                        return first_number - second_number;
                    });
                }
                auto_update_with_data(list_for_seat, row);
                row += 1;
            }
        }
        else if (auto_update_row == 0) {
            for (const [key, value] of Object.entries(dict_coordinate_x).reverse()) {
                let list_for_seat = [];
                for (coordinate of value) {
                    list_for_seat.push(coordinate)
                }
                if (auto_update_seats == 2) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[1]);
                        const second_number = new Number(b.split(' ')[1]);
                        return second_number - first_number;
                    });
                }
                else if (auto_update_seats == 3) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[1]);
                        const second_number = new Number(b.split(' ')[1]);
                        return first_number - second_number;
                    });
                }
                auto_update_with_data(list_for_seat, row);
                row += 1;
            }
        }
        else if (auto_update_row == 1) {
            for (const [key, value] of Object.entries(dict_coordinate_x)) {
                let list_for_seat = [];
                for (coordinate of value) {
                    list_for_seat.push(coordinate)
                }
                if (auto_update_seats == 2) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[1]);
                        const second_number = new Number(b.split(' ')[1]);
                        return second_number - first_number;
                    });
                }
                else if (auto_update_seats == 3) {
                    list_for_seat.sort(function(a, b) {
                        const first_number = new Number(a.split(' ')[1]);
                        const second_number = new Number(b.split(' ')[1]);
                        return first_number - second_number;
                    });
                }
                auto_update_with_data(list_for_seat, row);
                row += 1;
            }
        }

        let auto_text = document.querySelector('span#auto_text');
        auto_text.innerHTML = 'Автоматическое обновлениие данных завершенно'
        check_count_list()
    });

    let button = document.querySelector('button#send_sector');
    button.addEventListener('click', function() {
        const data_to_ready = data_to_send_in_python.length;
        const all_data = Object.keys(data_to_send).length;
        let result = true
        if (data_to_ready != all_data) {
            result = confirm('Количество отправляемых данных не совпадает с количеством определенных мест в этом секторе, продолжить?');
        }
        if (result == true) {
            send_data_ajax(data_to_send_in_python)
            let main_svg = document.querySelector('#main_svg');
            let div_for_content = document.querySelector('div.div_for_content');
            let h1 = document.querySelector('h1#sector_name');
            main_svg.remove();
            div_for_content.remove();
            h1.remove();
            data_to_send = {};
            sector_is_good_is_work = true;
        }
    });
}

async function send_data_ajax(data_to_send_in_python) {
    let number_port = 8040;
    const myUrl = `http://127.0.0.1:${number_port}`;
    var request = new Request(myUrl, {method: "POST", mode: "no-cors", body: JSON.stringify(data_to_send_in_python)});

    fetch(request).then(function(response) {
        console.log(response);
        // return response.json();
    }).then(function(j) {
        console.log(JSON.stringify(j));
    }).catch(function(error) {
        console.log('Request failed', error);
    });
}