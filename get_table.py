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
import sys
import re

AMOUNT_OF_TRIES = 30

SLEEP_TIME = 25

DATE = 1
NONE_NUM_CHAR = "[^0-9]"
COLUMNS = ['Country,Other', 'TotalCases', 'NewCases', 'TotalDeaths', 'NewDeaths',
           'TotalRecovered', 'ActiveCases', 'Serious,Critical',
           'Tot Cases/1M pop', 'Deaths/1M pop', 'TotalTests',
           'Tests/1M pop']


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

def get_table(web) -> pd.DataFrame:
    """
    Parse the html into a dataframe
    """
    table = web.find_all('table')[-1]
    table = table.find_all_next("tr")
    df = pd.DataFrame(columns=COLUMNS)
    for i in range(1, len(table[1:])):
        row_info = table[i].find_all('td')
        country = row_info[0].text.replace('\n', '')
        row_data = [re.sub(NONE_NUM_CHAR, '', i.text) for i in row_info[1:min(len(COLUMNS), len(row_info))]]
        if len(row_info) < len(COLUMNS):
            row_info = [country] + row_data + [-1] * (len(COLUMNS) - len(row_info))
        else:
            row_info = [country] + row_data
        row = pd.Series(data=row_info, index=COLUMNS)
        df.loc[i - 1] = row
    return df



def process_table(table):
    table.drop(table[table['Country,Other'] == 'Country,Other'].index, inplace=True)
    table.reset_index(drop=True)
    for col in table.columns[1:]:
        if table[col].dtype != object:
            continue
        table[col] = table[col].replace('', -1).astype(float)



if __name__ == '__main__':
    for i in sys.argv[DATE:]:
        print(i)
        url = "https://web.archive.org/web/2020%s/https://www.worldometers.info/coronavirus/" % i

        web = get_web(url)
        info = get_table(web)
        df = info.table
        df.to_csv(i + ".csv")
