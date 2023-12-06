import json
import time
from parse_module.utils.captcha import API_KEY
from pathlib import Path
from parse_module.drivers.proxelenium import ProxyWebDriver
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class WebdriverChrome(ProxyWebDriver):

    def __init__(self, **kwargs):
        self.delay_authorization_and_to_load = 1.5
        self.delay_to_load_extension = .75
        self.delay_input = .125
        self.count_window = 0

        account = kwargs.get('account')
        self.username = account.get('username')
        self.password = account.get('password')

        options = webdriver.ChromeOptions()
        base_dir = Path(__file__).resolve().parent.joinpath('data_to_big_theatre')
        file_extension = base_dir.joinpath('extension_3_3_1_0.crx.crx')
        options.add_extension(file_extension)

        options.add_argument('disable-infobars')
        options.add_argument('-disable-gpu')
        options.add_argument("--no-startup-window")
        # options.add_argument('blink-settings=imagesEnabled=false')

        id_profile = kwargs.get('id_profile')
        dir_with_profile = base_dir.joinpath(f'profile{id_profile}')
        # options.add_argument('--allow-profiles-outside-user-dir')
        # options.add_argument('--enable-profile-shortcut-manager')
        options.add_argument(f'user-data-dir={dir_with_profile}')
        super().__init__(chrome_options=options, **kwargs)

    def parse_seats(self, url_to_parse):
        if len(self.window_handles) > 4:
            self.quit()

        self.set_page_load_timeout(10)
        self.get(url=url_to_parse)
        if self.current_url == 'https://ticket.bolshoi.ru/login':
            start_time_for_authorization = time.time()
            authorization_readiness = None
            while authorization_readiness is None:
                time_now = time.time()
                if (time_now - start_time_for_authorization) > 240:
                    self.quit()
                authorization_readiness = self.authorization()
                self.refresh()
            self.get(url=url_to_parse)

        text_json = WebDriverWait(self, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "pre"))
                )
        return json.loads(text_json[0].text) if len(text_json) > 0 else None

    def first_update_extension_rucatcha(self):
        if len(self.window_handles) > 4:
            self.quit()
        new_window = self.open_window_and_switch()
        self.get('chrome-extension://fkofobllimjijoclbdkacclffjhbchoj/options/options.html')

        rucaptcha = self.execute_script(f'return document.querySelector("#isPluginEnabled").checked')
        auto_recatcha_v2 = self.execute_script(
            f'return document.querySelector("#autoSolveRecaptchaV2").checked')
        api_key = self.execute_script(f'return document.querySelector("input").value')

        actions = ActionChains(self)
        if api_key == '':
            self.execute_script(
                f'document.querySelector("input").value = "{API_KEY}"')
            actions.send_keys(Keys.TAB * 3 + Keys.ENTER)
            if rucaptcha is True:
                actions.send_keys(Keys.TAB * 2 + Keys.SPACE)
                if auto_recatcha_v2 is False:
                    actions.send_keys(Keys.TAB * 6 + Keys.SPACE)
        elif rucaptcha is True:
            actions.send_keys(Keys.TAB * 5 + Keys.SPACE)
            if auto_recatcha_v2 is False:
                actions.send_keys(Keys.TAB * 6 + Keys.SPACE)
        actions.perform()
        self.execute_script("window.alert = function() {};")
        time.sleep(self.delay_to_load_extension)
        self.execute_script("window.alert = function() {};")
        time.sleep(self.delay_to_load_extension)
        self.close_window(new_window)

    def second_update_extension_rucatcha(self):
        if len(self.window_handles) > 4:
            self.quit()
        new_window = self.open_window_and_switch()
        self.get('chrome-extension://fkofobllimjijoclbdkacclffjhbchoj/options/options.html')

        rucaptcha = self.execute_script(f'return document.querySelector("#isPluginEnabled").checked')
        actions = ActionChains(self)
        if rucaptcha is False:
            actions.send_keys(Keys.TAB * 5 + Keys.SPACE)
        actions.perform()

        self.close_window(new_window)

    def authorization(self):
        try:
            if len(self.window_handles) > 4:
                self.quit()

            self.first_update_extension_rucatcha()
            window_authorization = self.open_window_and_switch(self.window_handles[0])
            self.get(url='https://ticket.bolshoi.ru/login')
            self.second_update_extension_rucatcha()
            _ = self.open_window_and_switch(window_authorization)
            start_time_decision_recaptcha = time.time()

            input_login = WebDriverWait(self, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#login"))
            )
            for word in self.username:
                input_login.send_keys(word)
                time.sleep(self.delay_input)
            time.sleep(self.delay_authorization_and_to_load)

            password_input = WebDriverWait(self, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#password"))
            )
            for word in self.password:
                password_input.send_keys(word)
                time.sleep(self.delay_input)
            time.sleep(self.delay_authorization_and_to_load)

            div_rucaptcha = WebDriverWait(self, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".captcha-solver_inner"))
            )
            if len(div_rucaptcha) == 0:
                return None

            while True:
                time_now = time.time()
                ready_or_not_recatcha = div_rucaptcha[0].find_element(
                    by=By.CSS_SELECTOR,
                    value='.captcha-solver-info'
                ).text
                if time_now - start_time_decision_recaptcha > 150:
                    return None
                if 'Капча решена!' in ready_or_not_recatcha:
                    break
                time.sleep(.5)
                if 'Решается...' in ready_or_not_recatcha:
                    continue
                if (time_now - start_time_decision_recaptcha > 10) and 'Решить с 2Captcha' in ready_or_not_recatcha:
                    return None

            # iframe = WebDriverWait(self, 5).until(
            #     EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='reCAPTCHA']"))
            # ).get_attribute('src')
            # googlekey = double_split(iframe, '&k=', '&co=')
            # url = self.current_url
            # captcha = non_selenium_recaptcha(googlekey, url)
            # print(captcha)
            # self.execute_script(f'document.querySelector("#g-recaptcha-response").textContent = "{captcha}"')
            # time.sleep(10)
            # actions = ActionChains(self)
            # actions.send_keys(Keys.TAB * 3 + Keys.SPACE)
            # actions.perform()
            # self.execute_script('document.querySelector(\'div[style="width: 100%; height: 100%; position: fixed; top: 0px; left: 0px; z-index: 2000000000; background-color: rgb(255, 255, 255); opacity: 0.05;"]\').click()')

            time.sleep(self.delay_authorization_and_to_load)
            button = WebDriverWait(self, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.login__enter"))
            )
            button.click()

            time.sleep(self.delay_authorization_and_to_load)
        except WebDriverException:
            return True if len(self.find_elements(by=By.CSS_SELECTOR, value='input#password')) == 0 else None
        return True if len(self.find_elements(by=By.CSS_SELECTOR, value='input#password')) == 0 else None

    def open_window_and_switch(self, window=None):
        if window:
            self.switch_to.window(str(window))
            return window
        else:
            self.count_window += 1
            new_wundow = 'tab' + str(self.count_window)
            self.execute_script(f"window.open('about:blank', '{new_wundow}');")
            self.switch_to.window(new_wundow)
            return new_wundow

    def close_window(self, number_window):
        _ = self.open_window_and_switch(number_window)
        if len(self.window_handles) > 1:
            self.close()
        _ = self.open_window_and_switch(self.window_handles[0])

    def check_ip(self):
        self.get('https://api.ipify.org/')
        self.implicitly_wait(10)
        ip = self.find_element(By.CSS_SELECTOR, 'pre').text
        print(ip)
