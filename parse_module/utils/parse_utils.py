


def utf_ignore(str_):
    return str_.encode('cp1251', 'ignore').decode('cp1251', 'ignore')


def double_split(source, lstr, rstr, n=0):
    # Возвращает n-ый эелемент
    SplPage = source.split(lstr, 1)[n + 1]
    SplSplPage = SplPage.split(rstr)[0]
    return SplSplPage


def inclusive_split(source, lstr, rstr, n=0):
    splitted = double_split(source, lstr, rstr, n=n)
    return lstr + source + rstr


def lrsplit(source, lstr, rstr):
    # Возвращает массив эелементов
    if not lstr in source:
        return []
    SplPage = source.split(lstr)
    SplPage.pop(0)
    SplSplPage = [splitted.split(rstr)[0] for splitted in SplPage]
    return SplSplPage


def contains_class(obj, slash='//'):
    xpath = f"{slash}*[contains(@class,'{obj}')]"
    return xpath


def class_names_to_xpath(obj, slash='//'):
    xpath = f"{slash}*[@class='{obj}']"
    return xpath


def html_decode(text):
    return text \
    .replace(u"&amp;", u"&") \
    .replace(u"&quot;", u'"') \
    .replace(u"&#039;", u"'") \
    .replace(u"&lt;", u"<") \
    .replace(u"&gt;", u">")