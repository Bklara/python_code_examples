import logging
from multiprocessing import Pool
import numpy as np
import pandas as pd
import argparse
from functools import reduce
import requests

url='###'
t_n = 8
n=0
s=requests.Session()
a = requests.adapters.HTTPAdapter(max_retries=10)
s.mount('http://', a)

logger =logging.getLogger('main') 
logger.setLevel(logging.DEBUG)
empty = logging.FileHandler('spell.log')
empty.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
empty.setFormatter(formatter)
logger.addHandler(empty)

error = logging.FileHandler('spell_error.log')
error.setLevel(logging.ERROR)
error.setFormatter(formatter)
logger.addHandler(error)


def check(word):
# if response 0 word misspell, if not 0 word OK
    link=url+q
    global logger

    try:

        r=s.get(link,timeout=40)
        if (int(r.text)==0):
            return False
        else :
            return True

    except Exception as e:
        logger.error("Status"+str(r.ok)+str(q)+str(r.text)+ str(e))
        return True

def part(query_string):
    global logger
    logger.info(query_string)
    bool_arr = list(map(lambda x: check(x), str(query_string).strip().split(' '))) #send every word to spellchecker
    
    return int(reduce((lambda x, y: x*y), bool_arr)) # if there is only one False user_query with a typo

def prtpool(df):
    df['spell'] = list(map(part,df['query'].values))
    
    return df


def main():
    parser = argparse.ArgumentParser(description='number of querys')
    parser.add_argument('-i', '--input', required=False, default='./content/mytoys/normquery0305.tsv')
    parser.add_argument('-o', '--output', required=False, default ='./content/mytoys/spell.tsv')
    parser.add_argument('-c', '--client', required=False, default='mytoys')

    args = parser.parse_args()

    global url,t_n

    print(url)

    if(False):

        print(args.check)
        bool_arr = list(map(lambda x: spl.check(x), args.check.split(' ')))
        print(bool_arr)
        print(int(reduce((lambda x, y: x*y), bool_arr)))

    else:

        df = pd.read_csv(args.input, sep='\t', index_col=None)
        print(df.head(2))
        
        
        index = np.array_split(range(df.shape[0]), t_n)
        dfs = list(map(lambda x: df.iloc[x], index))

        print(dfs[0])
        print("Start checking")

        pool = Pool(t_n)
        spell = pool.map(prtpool, dfs)
        pool.close()
        pool.join()

        print(spell[0])
        print('done')

        result = pd.concat(spell)

        result.to_csv(args.output, sep='\t', header=True)

        print(result.head())


if __name__ == "__main__":
    main()
