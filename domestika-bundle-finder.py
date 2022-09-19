import datetime
import json
import requests
import sys
import re
from os import linesep
from pathlib import Path
from bs4 import BeautifulSoup

def updateDB(args):
    update = True

    if "--update" not in args:
        datafile = Path("bundles.json")
        if datafile.is_file():
            today = datetime.datetime.today()
            modified_date = datetime.datetime.fromtimestamp(datafile.stat().st_mtime)
            duration = today - modified_date
            if (duration.days < 7) and "--update" not in args:
                try:
                    bundledata = json.loads(datafile.read_text())
                    update = False
                except:
                    update = True
        
    if update:
        bundleURLs = getBundleURLs()
        bundledata = getBundles(bundleURLs)
        with open('bundles.json', 'w') as outfile:
            json.dump(bundledata, outfile)

    return bundledata

def getBundleURLs(url="https://www.domestika.org/en/courses/packs"):
    r = requests.get(url)
    parsed = BeautifulSoup(r.text, features="html.parser")
    bundle_urls = parsed.find_all("h3", class_="o-course-card__title")
    urls = []
    for bundle_url in bundle_urls:
        urls.append(bundle_url.find("a").get("href"))
    return urls

def getMetaData(r):
    metadata = {}
    parsed = BeautifulSoup(r.text, features="html.parser")
    metadata["title"] = parsed.find("meta", property="og:title").get("content")
    metadata["url"] = parsed.find("meta", property="og:url").get("content")
    try: 
        price = parsed.find("div", class_="m-price-tag__price").text
        metadata["price"] = float(''.join(c for c in price if (c.isdigit() or c =='.')))
    except:
        metadata["price"] = "0"
    return metadata

def parseBundlePage(r):
    parsed = BeautifulSoup(r.text, features="html.parser")
    titles = parsed.find_all("h3", class_="o-course-card__title")
    ls = []
    for title in titles:
        ls.append(title.a.string)
    return ls

def parseBundle(bundleURL):
    bundle = {}
    page = 2
    
    # get metadata
    r = requests.get(bundleURL)
    bundle = getMetaData(r)
    bundle["items"] = []
    print("Parsing", bundle["title"])

    while (temp := parseBundlePage(r)):
        bundle["items"] += parseBundlePage(r)
        r = requests.get("".join(["https://www.domestika.org/en/course_packs/180-discover-the-depths-of-your-abilities", "/?page=", str(page)]))
        page += 1

    return bundle

def getBundles(bundleURLs):
    bundles = []
    for url in bundleURLs:
        bundles.append(parseBundle(url))
    return bundles

def findBundle(args, bundledata):
    matches = []
    for bundle in bundledata:
        temp = []
        for searchterm in args:
            for course in bundle["items"]:
                if searchterm.lower() in course.lower():
                    temp.append(course)
        if len(temp) > 0:
            matches.append({"title": bundle["title"], "url": bundle["url"], "price": bundle["price"], "items": temp})
    return matches   

def printMatches(matches):
    for bundle in matches:
        print(bundle["title"], bundle["url"], bundle["price"], sep=" - ")
        for course in bundle["items"]:
            print("* ",course)

def usage():
    deco = "="*24
    print(linesep.join([deco, "Domestika Bundle Finder" , deco]))
    print("Usage: domestika-bundle-finder.py \"courses that\" \"you are\" \"looking for\"")
    print("--update: updates data")
    

if __name__ == "__main__":

    if len(sys.argv) == 1:
        usage()
        sys.exit(0)
    args = sys.argv[1:]

    print(args)

    # load bundles.json from disk or fetch it from domestika if it's older than 7 days    
    bundledata = updateDB(args)
    if "--update" in args:
        args.remove("--update")

    matches = findBundle(args, bundledata)
    print("Searching for: ", ", ".join(args))
    printMatches(matches)
