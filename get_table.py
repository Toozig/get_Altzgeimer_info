########################################################################################################
# Retrive information  from https://www.worldometers.info/coronavirus/ according to a given date
#
# run on cmd "python3 get_info.py DATE
# the DATE format is MMDD
# written by adob
########################################################################################################


import urllib
import bs4 as bs
import pandas as pd
from urllib import request
import time


def get_web(url):
    """
    creates a beautiful soup object from a given url
    """
    web = None
    i = 0
    while web is None or web is False:
        web = get_site_html(url)
        i += 1
        if i > 1:
            time.sleep(SLEEP_TIME)
        if i > AMOUNT_OF_TRIES:
            return None
    return web


def get_site_html(url):
    try:
        # pretend to be Firefox
        req = urllib.request.Request(url,
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as url_file:
            url_byte = url_file.read()
    except urllib.request.HTTPError as e:  # HTTP status code
        print(e.__str__())
        return False
    except urllib.request.URLError as e:  # General Error
        print(e.__str__())
        return False
    except OSError as e:  # Vague Error
        print(e.__str__())
        return False
    except Exception as e:  # Anything
        print(e.__str__())
        return False
    try:
        url_string = url_byte.decode(encoding='latin1').encode(
            encoding='utf-8')
    except UnicodeDecodeError as e:
        print(e.__str__())
        return False
    except Exception as e:
        print(e.__str__())
        return False
    return bs.BeautifulSoup(url_string, "html.parser")


def get_table_columns(table_first_row):
    row_info = table_first_row.find_all('td')
    row_data = [i.text.replace("\n", "") for i in row_info[0:len(row_info)]]
    return row_data


def get_tables(web) -> list:
    """
    Parse the html into a dataframe
    """
    table = web.find_all('table')
    table_list = []
    for table in table:
        df = get_table(table)
        if df is not None:
            table_list.append(df)
    return table_list


def get_table(table):
    table = table.find_all_next("tr")
    columns = get_table_columns(table[0])
    df = pd.DataFrame(columns=columns)
    for row in table[1:]:
        row_data = get_table_columns(row)
        if len(row_data) != len(columns):
            return None
        row_data = pd.Series(data=row_data, index=columns)

        df = df.append(row_data, ignore_index=True)
    return df


def process_table(table: pd.DataFrame):
    for col in table.columns:
        try:
            table[col] = table[col].str.replace(",", "").astype(float)

        except ValueError:
            continue
    return table



def generate_tables_csv(url,title):
    web = get_web(url)
    tabel_list = get_tables(web)
    tabel_list = [process_table(i) for i in tabel_list]
    for idx in range(len(tabel_list)):
        tabel_list[idx].to_csv(title + "_" + str(idx) + ".csv")
