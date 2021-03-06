from time import sleep

import requests
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent

WEEKDAYS = ["понедельник", 'вторник', 'среда', 'четверг', 'пятница', 'суббота']


class Parser:
    def __init__(self, url):
        self.ua = UserAgent(use_cache_server=False)
        self.url = url
        self.session = requests.Session()
        self.soup = bs()
        self.date = ""
        self.update()

    def update(self, recon_max=5, recon_time=60, count=1):
        try:
            self.session.headers.update({'User-Agent': self.ua.random})
            response = self.session.get(self.url, timeout=5).content
            self.soup = bs(response, "html.parser")
            self._update_date()
        except:
            count += 1

            if count % (recon_max*4) == 0:
                sleep(recon_time*120)
            elif count % (recon_max*2) == 0:
                sleep(recon_time*10)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.update(count=count)

    @staticmethod
    def _have_num(string):
        numbers = "0123456789"
        for char in string:
            if char in numbers:
                return True
        return False

    @staticmethod
    def _find_weekday(string):
        for day in WEEKDAYS:
            if day in string:
                return day
        return ""

    def _update_date(self):
        strings = self.__pars_spans_text()
        for string in strings:
            string = string.lower()

            day = self._find_weekday(string)
            if day:
                texts_words = string.split()
                date = ""

                # Отделение строк с информацией
                for word in texts_words:
                    if day in word or self._have_num(word):
                        date += word

                date = date.title()

                break

        else:
            date = ""

        self.date = date

    def get_date(self):
        return self.date

    @staticmethod
    def tables_to_group_names(tables):
        return [table[0][1].replace("(ДИСТ)", "") for table in tables]

    def _pars_today_tables(self):
        tables = self.soup.find_all("table")

        text_lines = []
        for table in tables:
            lines = table.find_all("tr")

            for line in lines:
                cells = line.find_all("td")

                texts = []
                for cell in cells:
                    text = cell.text.upper()

                    # Привод значений в понятный вид
                    text = text.strip("\n")
                    text = text.replace("\n", " ")
                    text = text.replace(u"\xa0", "")
                    text = text.replace(
                        "ЭТОТ АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ ЗАЩИЩЕН ОТ СПАМ-БОТОВ. У ВАС ДОЛЖЕН БЫТЬ ВКЛЮЧЕН JAVASCRIPT ДЛЯ ПРОСМОТРА.",
                        "ПОЧТА НА САЙТЕ.")

                    while "  " in text:
                        text = text.replace("  ", " ")

                    text = text.strip()
                    # Поиск и вставка ссылки/ок
                    cell_a = cell.find_all("a")
                    if cell_a:
                        for a in cell_a:
                            link = a.get("href")
                            if "http" not in link:
                                link = f"https://katt44.ru{link}"
                            text += " " + link

                    texts.append(text)

                if texts.count("") != len(texts) and texts.count([]) != len(texts):
                    text_lines.append(texts)

        return text_lines

    @staticmethod
    def _split_table_by_lines(text_table):
        last_line = 0
        new_tables = []
        for line_num, line in enumerate(text_table):
            if "ГРУППА" in line[0]:
                new_tables.append(text_table[last_line: line_num])
                last_line = line_num
        new_tables.append(text_table[last_line: -1])

        return new_tables[1:]

    @staticmethod
    def _split_tables_by_columns(tables):
        group_tables = []
        for table in tables:

            for group_num in range(1, len(table[0])):
                group_tables.append([[line[0], line[group_num]] for line in table])

        return group_tables

    def _split_table(self, table):
        return self._split_tables_by_columns(
               self._split_table_by_lines(table))

    @staticmethod
    def _delete_uninformative_table_lines(table):
        table = [[cell for cell in line] for line in table]

        for line in table[::-1]:
            if not line[1]:
                table.remove(line)
            else:
                break
        return table

    @staticmethod
    def _reformat_table(table):
        table = [[cell for cell in line] for line in table]

        for line in table:

            if len(line) == 2:
                titles = []
                additions = []
                if "http" in line[1]:
                    splited = line[1].split()

                    for word in splited:
                        if "http" in word:
                            additions.append(word)
                        else:
                            titles.append(word.strip())

                    line[1] = " ".join(titles)

                if "КАБ" in line[1]:
                    splited = line[1].split('КАБ')

                    title = splited[0].replace("(", "").strip()
                    cabinet_number = splited[1].replace(")", "").replace(".", "").strip()

                    line[1] = title
                    additions.insert(0, cabinet_number)

                line.append(" ".join(additions))

        # если в клетке названия группы есть что то кроме группы оно переносится в другую колонку
        table[0][1] = table[0][1].replace(' ', "")
        first_line = table[0][1].split(" ")
        table[0][1] = first_line[0]
        if len(first_line) > 1:
            table[0][2] += f' {first_line[1]}'

        return table

    def _tables_to_group_tables(self, tables):
        group_tables = []

        for table in tables:
            table = self._delete_uninformative_table_lines(table)
            if table:
                table = self._reformat_table(table)

                group_tables.append(table)

        return self._delete_duplicates(group_tables)
    
    @staticmethod
    def _delete_duplicates(tables):
        group_tables = []
        groups = []
        
        for num, table in enumerate(tables):
            if num == len(tables)-1:
                num -= 1
            if table[0][1] in groups and tables[num+1][0][1] in groups:
                break

            groups.append(table[0][1])
            group_tables.append(table)
        
        return group_tables

    def get_tables(self):
        return self._tables_to_group_tables(
               self._split_table(
               self._pars_today_tables()))

    def __pars_spans_text(self):
        spans = self.soup.find_all("b")
        spans_text = [span.text for span in spans]
        return spans_text

    @staticmethod
    def __theme_0(table, column_width):
        table_str = ""
        for line_num, line in enumerate(table):
            for cell_num, cell in enumerate(line):

                if not (line_num == 0 and cell_num == 0):
                    if line_num == 0 and cell_num == 1:
                        table_str += cell.ljust((column_width[cell_num] + column_width[cell_num - 1] + 3), " ")
                    else:
                        table_str += cell.ljust(column_width[cell_num], " ")

                    if not cell == line[-1]:
                        table_str += " | "

            table_str += "\n"
        return table_str

    @staticmethod
    def __theme_1(table, column_width):
        table_str = ""
        for line_num, line in enumerate(table):
            for cell_num, cell in enumerate(line):

                if not (line_num == 0 and cell_num == 0):
                    if cell_num == 0:
                        table_str += str(line_num)

                    elif line_num == 0 and cell_num == 1:
                        table_str += cell.ljust((column_width[cell_num] + 4), " ")

                    else:
                        table_str += cell.ljust(column_width[cell_num], " ")

                    if not cell == line[-1]:
                        table_str += " | "

            table_str += "\n"
        return table_str

    @staticmethod
    def __column_width_by_table(table):
        column_width = []
        for column in range(len(table[0])):
            max_width = 0
            for line in table[1:]:
                width = len(line[column])
                if width > max_width:
                    max_width = width
            column_width.append(max_width)
        return column_width

    def table_to_str(self, table, style_id: int = 0):
        # Глубокое копирование для избежания внешнего изменения таблицы
        table = [[cell if "http" in cell else cell.title() for cell in line] for line in table]

        for line in table[1:]:
            line[0] = line[0].replace("–", "-").replace(" ", "")
            splited = line[0].split("-")
            line[0] = "-".join(spl.zfill(5) for spl in (splited[0], splited[-1]))

        if table[0][1]:
            table[0][1] = f"{table[0][1]} Группа"

        # column_width = self.__column_width_by_table(table)
        # Из за кривого отображения в ВК пробелы то сжираются то добавляют лишние переводы строк
        column_width = [0, 0, 0]

        if style_id == 0:
            table_str = self.__theme_0(table, column_width)
        elif style_id == 1:
            table_str = self.__theme_1(table, column_width)
        else:
            table_str = self.__theme_0(table, column_width)

        date = self.get_date()
        table_str = date + "\n" + table_str

        if table_str.count("\n") <= 2:
            table_str += "Пар нет\n"

        return table_str


if __name__ == '__main__':
    import time

    start_time = time.time()

    pars = Parser("http://www.katt44.ru/index.php?option=com_content&view=article&id=252&Itemid=129")
    tabl = pars.get_tables()
    for i in tabl:
        print(pars.table_to_str(i))
    print(pars.tables_to_group_names(tabl))

    print("--- %s seconds ---" % (time.time() - start_time))
