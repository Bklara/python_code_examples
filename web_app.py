  GNU nano 2.9.2                                                                main_suggest_mytoys.py                                                                          

import daemon
from bottle import route, run, debug, template, request,get,static_file
import argparse
from operator import attrgetter
import subprocess
import json
import bottle
import requests 
from  urllib import parse
import urllib
import sqlite3
from collections import defaultdict

table_ru = str.maketrans("йцукенгшщзхъфывапролджэячсмитьбю","qwertyuiop[]asdfghjkl;'zxcvbnm,.")
table_en = str.maketrans("qwertyuiop[]asdfghjkl;'zxcvbnm,.","йцукенгшщзхъфывапролджэячсмитьбю")
subprocess.run("lsof -i tcp:8089 | awk 'FNR==2{print $2}' | xargs  kill -9", shell=True, check=False)
MAX=10

another_url="https://s3.eu-central-1.amazonaws.com/detectum-runs/mytoys/suggest/mytoys_cluster_suggest.db"
uri='mytoys/suggests/_search'
ES_HOST="h33.htz17.i.detectum.com"
#"0.0.0.0"
ES_PORT=8022
LOG=open('log.txt','a+')
conn = sqlite3.connect("mytoys_cluster_suggest.db")    
cursor = conn.cursor()

def get_clusters(query,query_ru,query_en):
    
    j="""
{
"_source": {"excludes": "query_4matching"}, 
  "query": {
    "bool": {
      "must": [
        {"bool": {"should": [
          {
          "wildcard": {
            "query_4matching": "%s*"
          }
        },{"wildcard":{"query_4matching":"%s*"}}
        ,{"wildcard":{"query_4matching":"%s*"}}
        ]}}
      ]    }
           },
  "aggs": {
    "by_clusters": {
      "terms": {
        "field": "cluster",
        "size": 100000
      },      
          "aggs": {
            "top": {
              "top_hits": {
                "sort": [
                  {
                    "count": {
                      "order": "desc"
                    }
                  }
                ],
                "size": 1
              }
            }
          }
       }
      }
    }

  """ %(query,query_ru,query_en)

    return j



def get_clusters_after(query,query_ru,query_en):

    j="""
{
 "_source": {
        "excludes": [ "query_4matching" ]
    },

  "query": {
    "bool": {
      "must": [
        {"bool": {"should": [

         {
          "wildcard": {
            "query_4matching": "* %s*"
          }
        },
          {
          "wildcard": {
            "query_4matching": "* %s*"
          }
        },
          {
          "wildcard": {
            "query_4matching": "* %s*"
          }
        }


        ]}}

      ]
    }
  },
  "aggs": {
    "by_clusters": {
      "terms": {
        "field": "cluster",
        "size": 100000
      },    
          "aggs": {
            "top": {
              "top_hits": {
                "sort": [
                  {
                    "count": {
                      "order": "desc"
                    }
                  }
                ],
                "size": 1
              }
            }
          }
        }
      }
    }""" %(query,query_ru,query_en)
    return j


def  get_cluster(n):

    j="""
        {
  "query": {
    "bool": {
      "must": [
        {
          "term": {
            "cluster": "%d"
          }
        }
      ]
    }
  },

"sort": [
    {
      "count": {
        "order": "asc"
      }
    }
  ]
,
"size":10000
}     """ %n
    return j

def get_another_suggest(prefix):
    
    try:

        url_old="http://suggest.mytoys.clients.detectum.com/prefix?term=%s"%prefix

        results=requests.post(url_old).json()
        print(results)
        al=[("?","cluster")]
        e=[]
        for element in results:
            cursor.execute('select  power as count, razbor_id as cluster from requests where request=="{0}"'.format(element))
            al = cursor.fetchall()
            try:
                e.append({'_source':{'query': str(element), 'count': al[0][0], 'cluster':al[0][1]}})
            except Exception as ex:
                e.append({'_source':{'query': str(element), 'count': 0, 'cluster':0}})
        return(e)
    except Exception as inst:
        LOG.write('get_another_suggest'+prefix + str(inst) +'\n') 
        #print('get_another_suggest '+prefix +' '+ str(inst) +'\n')
        return None


def old_get_cluster(n):
    try:
        conn = sqlite3.connect("another_suggest_mytoys.db")

        cursor = conn.cursor()
 
        cursor.execute('select request as text, power as count, razbor_id as cluster from requests where cluster=="{0}" order by count DESC '.format(n))
        results = cursor.fetchall()
        print(results)
        conn.close()
    
        e = []
        for i,element in enumerate(results):
            #print(element)
            e.append({'_source':{'query': str(element[0]), 'count': element[1], 'cluster': element[2]}})
    
        return(e)
    except Exception as inst:
        LOG.write('old_get_cluster'+ str(inst) +'\n')
        return None




 


@route('/suggest')
def get_suggest():
    
    try:  

        prefix=request.query.prefix.lower()
        prefix=prefix.strip()
        print(prefix)
        MAX=int(request.query.count)
        prefix_ru=prefix.translate(table_ru)
        prefix_en=prefix.translate(table_en)
        json_data=json.loads(get_clusters(prefix,prefix_ru,prefix_en))
        r=requests.post("http://%s:%s/%s?filter_path=aggregations&size=0" % (ES_HOST,ES_PORT,uri), json=json_data)
        po= r.json()
        res=po['aggregations']['by_clusters']['buckets']

        if (len(res)<MAX):
            print("LEN<MAX")
            json_data=json.loads(get_clusters_after(prefix,prefix_ru,prefix_en))
            r=requests.post("http://%s:%s/%s?filter_path=aggregations&size=0" % (ES_HOST,ES_PORT,uri), json=json_data)
            po= r.json()
            try:
                res_after=po['aggregations']['by_clusters']['buckets']
                querys=list(map(lambda x: x['top']['hits']['hits'][0]['_source']['query_4showing'] , res ))
                clusters=list(map(lambda x: x['top']['hits']['hits'][0]['_source']['cluster'] , res ))
                
                res_after=list(filter(lambda x: (( x['top']['hits']['hits'][0]['_source']['query_4showing'] not in querys)\
           and (x['top']['hits']['hits'][0]['_source']['cluster'] not in clusters))  ,res_after))
                print(list(map(lambda x: (( x['top']['hits']['hits'][0]['_source']['query_4showing'] not in querys)\
           , (x['top']['hits']['hits'][0]['_source']['cluster'] not in clusters),\
    x['top']['hits']['hits'][0]['_source']['cluster'],x['top']['hits']['hits'][0]['_source']['query_4showing']),res_after)))
                res=res+res_after[:(MAX-len(res))]
            except Exception as ex:
                print(ex)
                
        try:
            
            res.sort(key=lambda x:int( x['top']['hits']['hits'][0]['_source']['count']), reverse=True)
            

        except Exception as Ex:
           
            pass

       
        res.sort( key = lambda x: 2*int( (x['top']['hits']['hits'][0]['_source']['query_4matching'][:len(prefix)]==prefix))+ \
           int( (x['top']['hits']['hits'][0]['_source']['query_4matching'][:len(prefix_ru)]==prefix_ru) )+ \
           int( (x['top']['hits']['hits'][0]['_source']['query_4matching'][:len(prefix_en)]==prefix_en) ),reverse=True)
        
        a=res[:MAX]
        res= json.dumps(a)
                
    except Exception as e:
        #print(res)
        
        res= json.dumps({})
        LOG.write('suggest'+ request.query.prefix+ str(e) +'\n')
        #print(e)

    return res


@route('/suggest_old')
def get_old_suggest():
    try:

        prefix=request.query.prefix

        res=get_another_suggest(prefix)
        res=json.dumps(res)

    except Exception as e:
        res= json.dumps({})
        #print('old_get_suggest'+ request.query+str(e) +'\n')

        LOG.write('old_get_suggest'+ request.query+str(e) +'\n')

    return res
 
@route('/cluster')
def show_cluster():

    try:
        cluster = request.params.get('cluster_number', type=int)        
        json_data=json.loads(get_cluster(cluster))
        r=requests.post("http://%s:%s/%s?filter_path=hits.hits._source&size=10000" % (ES_HOST,ES_PORT,uri), json=json_data)
        res=json.dumps(r.json())


    except Exception as e:
        res= json.dumps({})
        LOG.write('show_cluster'+ request.query+str(e) +'\n')
    
    return res

@route('/old_cluster')
def old_show_cluster():
    try:
        cluster = request.params.get('cluster_number', type=int)
        res=json.dumps(old_get_cluster(cluster))
    
    except Exception as e:
        res= json.dumps({})
        LOG.write('old_cluster'+ request.query+str(e) +'\n')
        print('old_cluster'+ request.query+str(e) +'\n')
    return res

@route('/js_part.js')
def script():

    return template('js_part.js')


@route('/css_part.css')
def script():

    return static_file('css_part.css',root=".")



@route('/old_description')
def old_show_description():
    try:
        prefix=request.query.prefix

        r=requests.get("http://yenisei.detectum.com/clusters-viewer/cluster_viewer_mvideo.py?rq={0}".format(prefix))
        res=r.content
 
    except Exception as e:
        res= json.dumps({})
        LOG.write('old_show_description'+ request.query+str(e) +'\n')
    
    return res


@route('/')
def index():
       
    return template('index.html', request=request)

run(host='0.0.0.0', port=8089,debug=True)




