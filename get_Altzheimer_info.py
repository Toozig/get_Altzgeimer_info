import os
import re
import time
import bs4 as bs
import pandas as pd
import numpy as np
import urllib.request

LOW_AGE_VAL = 30
COLS = ["Country",
        "Age group",
        "Men with dementia",
        "Women with dementia",
        "Total",
        "women_population",
        "men_population",
        "total_population"]
ALTZ_COUNTRY_LIST_URL = "https://www.alzheimer-europe.org/Policy/Country-comparisons/2013-The-prevalence-of-dementia-in-Europe/United-Kingdom-Scotland"

FEMALE_IDX = 4

MALE_IDX = 3

HIGH_VAL = 999
COUNTRY_ID_REGEX = 'countryId = ([0-9]*);'
NONE_NUM_CHAR = "[^0-9]"
ALTZ = True
POP = False


class AppURLopener(urllib.request.FancyURLopener):
    version = "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.69 Safari/537.36"



AMOUNT_OF_TRIES = 30

SLEEP_TIME = 25

def get_web(url, type='html'):
    """
    creates a beautiful soup object from a given url
    """
    web = None
    i = 0
    while web is None or web is False:
        web = get_site_html(url, type)
        i += 1
        if i > 1:
            time.sleep(SLEEP_TIME)
        if i > AMOUNT_OF_TRIES:
            return None
    return web


def get_site_html(url, type):
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
    return bs.BeautifulSoup(url_string, "%s.parser" %type)


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
    table = table.find_all("tr")
    columns = get_table_columns(table[0])
    df = pd.DataFrame(columns=columns)
    for row in table[1:]:
        row_data = get_table_columns(row)
        if len(row_data) != len(columns):
            return None
        row_data = pd.Series(data=row_data, index=columns)
        df = df.append(row_data, ignore_index=True)
    return df if df.shape[0] > 1 else None


def process_table(table: pd.DataFrame):
    for col in table.columns:
        try:
            table[col] = table[col].str.replace(",", "").astype(float)

        except ValueError:
            continue
    return table



def generate_tables(url):
    web = get_web(url)
    tabel_list = get_tables(web)
    tabel_list = [process_table(i) for i in tabel_list]
    return tabel_list




def split_age_range(df: pd.DataFrame, altz: bool):
    total = None
    if altz:
        total = df.iloc[-1].values.tolist()
        total = [LOW_AGE_VAL, HIGH_VAL] + total
    work_df = df.iloc[:-1] if altz else df

    splitted = work_df[work_df.columns[0]].astype(str).str.split('-')
    low = [int(re.sub(NONE_NUM_CHAR, '', i[0])) for i in splitted]
    high = [int(re.sub(NONE_NUM_CHAR, '', i[1])) for i in splitted[:-1]]
    if len(low) > len(high):
        high.append(HIGH_VAL)
    work_df.insert(0, 'high', high, True)
    work_df.insert(0, 'low', low, True)
    if altz:
        work_df = work_df.append(pd.Series(total, index=work_df.columns),
                                 ignore_index=True)
    else:
        work_df.iloc[-2, [MALE_IDX, FEMALE_IDX]] += work_df.iloc[-1, [MALE_IDX, FEMALE_IDX]]
        work_df = work_df.iloc[:-1]
        work_df.iloc[-1, 1] = HIGH_VAL
    return work_df


def brave_heart(country_url_dict: dict):
    """
    This function gets the information about united kingdom
    """
    uk_parts = ["United Kingdom (England, Wales and Northern Ireland)", "United Kingdom (Scotland)", "Jersey"]
    alz_tabels = [
        generate_tables("https://www.alzheimer-europe.org" + country_url_dict[i])[0 if i != uk_parts[1] else 1] for i
        in uk_parts]
    dem_table = alz_tabels[0]
    for i in alz_tabels[1:]:
        dem_table.iloc[1:, 1:] += i.iloc[1:, 1:]
    pop_table = get_pop("United Kingdom")
    country_res = sync_tables(dem_table, pop_table)
    country_res.insert(0, 'Country', "United Kingdom", True)
    country_res.columns = COLS
    return country_res


def get_pop(country):
    """
    Gets the 2013 country's population information from /www.populationpyramid.net
    """
    fname = "2013_pop/%s.csv" % country
    if not os.path.isfile(fname):
        url = "https://www.populationpyramid.net/%s/2013/" % country.lower().replace(" ", '-')
        web = get_web(url)
        country_id = web.find_all('script', {'type': "application/javascript"})[0].contents[0]
        title_search = re.search(COUNTRY_ID_REGEX, country_id)
        if title_search:
            country_id = title_search.group(1)

        url = "https://www.populationpyramid.net/api/pp/%s/2013/?csv=true" % country_id
        urllib._urlopener = AppURLopener()
        urllib._urlopener.retrieve(url, fname)
    return pd.read_csv(fname)


def sync_tables(dem_table, pop_table):
    """
    synchronize the information from both of the tables into one table
    """
    work_dem_table = split_age_range(dem_table, ALTZ)
    work_pop_table = split_age_range(pop_table, POP)
    total_male = []
    total_female = []
    for index, data in work_dem_table.iterrows():
        mini_pop = work_pop_table[np.logical_and(work_pop_table['low'] >= data['low']
                                                 , work_pop_table['high'] <= data['high'])]
        pop_sum = np.sum(mini_pop.iloc[:, [MALE_IDX, FEMALE_IDX]], axis=0)
        total_male.append(pop_sum['M'])
        total_female.append(pop_sum['F'])
    dem_table.insert(dem_table.shape[1], 'women_population', total_female)
    dem_table.insert(dem_table.shape[1], 'men_population', total_male)
    dem_table.insert(dem_table.shape[1], 'total_population', pd.Series(total_male) + pd.Series(total_female))
    return dem_table


def generate_BCG_table():
    """
    Main function to generate the wanted table and saves it as csv filr
    """
    country_url_dict = get_country_list()
    res = pd.DataFrame(columns=COLS)
    for i in country_url_dict: # the following items had some issues in their web page, had to be handle differently
        if i == "Jersey" or i == "References" or "United Kingdom" in i:
            continue
        print(i)
        table = generate_tables("https://www.alzheimer-europe.org" + country_url_dict[i])
        if len(table) > 1 and i != "Ireland":
            continue
        alz_table = table[0]
        pop_table = get_pop(i)
        country_res = sync_tables(alz_table, pop_table)
        country_res.insert(0, 'Country', i, True)
        country_res.columns = COLS
        res = pd.concat([res, country_res])
    uk = brave_heart(country_url_dict)
    res = pd.concat([res, uk])
    res.to_csv("output_BCG.csv")
    print("Done")


def get_country_list():
    web = get_web(ALTZ_COUNTRY_LIST_URL)
    raw_list = web.find_all('div', {"id": "sidebar"})[0]
    raw_list = raw_list.find_all('li')
    country_url_dict = {}
    for i in raw_list:
        country_url_dict[i.text] = i.a['href']
    return country_url_dict

