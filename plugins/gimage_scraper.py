#!/usr/bin/env python
# In[ ]:
#  coding: utf-8

import codecs
import datetime
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from http.client import BadStatusLine, IncompleteRead
from urllib.parse import quote
from urllib.request import HTTPError, Request, URLError, urlopen

http.client._MAXHEADERS = 1000

class googleimagesdownload:
    def __init__(self):
        pass

    def _extract_data_pack(self, page):
        start_line = page.find("AF_initDataCallback({key: \\'ds:1\\'") - 10
        start_object = page.find("[", start_line + 1)
        end_object = page.rfind("]", 0, page.find("</script>", start_object + 1)) + 1
        object_raw = str(page[start_object:end_object])
        return bytes(object_raw, "utf-8").decode("unicode_escape")

    def _image_objects_from_pack(self, data):
        image_objects = json.loads(data)[31][-1][12][2]
        image_objects = [x for x in image_objects if x[0] == 1]
        return image_objects

    def download_page(self, url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req)
            respData = str(resp.read())
            return self._image_objects_from_pack(self._extract_data_pack(respData))
        except Exception as e:
            print(f"Could not open URL. Error: {e}")
            return None

    def format_object(self, obj):
        data = obj[1]
        main = data[3]
        info = data[9]
        if info is None:
            info = data[11]
        
        formatted_object = {
            "image_height": main[2],
            "image_width": main[1],
            "image_link": main[0],
            "image_format": main[0][-1 * (len(main[0]) - main[0].rfind(".") - 1) :],
            "image_description": info.get("2003", [None, None, None, ""])[3],
            "image_host": info.get("2003", [None]*18)[17],
            "image_source": info.get("2003", [None, None, ""])[2],
            "image_thumbnail_url": data[2][0],
        }
        return formatted_object

    def build_url_parameters(self, arguments):
        lang_url = ""
        if arguments.get("language"):
            lang = "&lr="
            lang_param = {"English": "lang_en", "Arabic": "lang_ar"} # Simplified for bot use
            lang_url = lang + lang_param.get(arguments["language"], "lang_en")

        built_url = "&tbs="
        counter = 0
        params = {
            "color": [arguments.get("color"), {"red": "ic:specific,isc:red", "blue": "ic:specific,isc:blue"}],
            "size": [arguments.get("size"), {"large": "isz:l", "medium": "isz:m", "icon": "isz:i"}],
            "type": [arguments.get("type"), {"face": "itp:face", "photo": "itp:photo", "clipart": "itp:clipart"}],
            "time": [arguments.get("time"), {"past-24-hours": "qdr:d", "past-7-days": "qdr:w"}],
            "aspect_ratio": [arguments.get("aspect_ratio"), {"tall": "iar:t", "square": "iar:s", "wide": "iar:w"}],
            "format": [arguments.get("format"), {"jpg": "ift:jpg", "gif": "ift:gif", "png": "ift:png"}],
        }
        for value in params.values():
            if value[0] is not None:
                ext_param = value[1].get(value[0])
                if ext_param:
                    if counter == 0:
                        built_url += ext_param
                    else:
                        built_url = f"{built_url},{ext_param}"
                    counter += 1
        return lang_url + built_url

    def build_search_url(self, search_term, params, safe_search):
        url = (
            "https://www.google.com/search?q="
            + quote(search_term.encode("utf-8"))
            + "&espv=2&biw=1366&bih=667&site=webhp&source=lnms&tbm=isch"
            + params
            + "&sa=X&ei=XosDVaCXD8TasATItgE&ved=0CAcQ_AUoAg"
        )
        if safe_search:
            url += "&safe=active"
        return url

    def create_directories(self, main_directory, dir_name):
        try:
            if not os.path.exists(main_directory):
                os.makedirs(main_directory)
            
            if dir_name: # Only create sub-directory if a name is provided
                sub_directory = os.path.join(main_directory, dir_name)
                if not os.path.exists(sub_directory):
                    os.makedirs(sub_directory)
        except OSError as e:
            if e.errno != 17:
                raise

    def download_image(self, image_url, main_directory, dir_name, count, prefix, no_numbering):
        try:
            req = Request(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
                },
            )
            response = urlopen(req, None, 10)
            data = response.read()
            info = response.info()
            response.close()

            qmark = image_url.rfind("?")
            if qmark == -1:
                qmark = len(image_url)
            slash = image_url.rfind("/", 0, qmark) + 1
            image_name = str(image_url[slash:qmark]).lower()

            type = info.get_content_type()
            if type == "image/jpeg" or type == "image/jpg":
                if not image_name.endswith((".jpg", ".jpeg")): image_name += ".jpg"
            elif type == "image/png":
                if not image_name.endswith(".png"): image_name += ".png"
            elif type == "image/webp":
                if not image_name.endswith(".webp"): image_name += ".webp"
            elif type == "image/gif":
                if not image_name.endswith(".gif"): image_name += ".gif"
            else:
                return "fail", "Invalid image format", None

            prefix = prefix + " " if prefix else ""
            
            if no_numbering:
                file_name = prefix + image_name
            else:
                file_name = f"{prefix}{str(count)}.{image_name}"

            path = os.path.join(main_directory, dir_name, file_name)

            with open(path, "wb") as output_file:
                output_file.write(data)
            
            absolute_path = os.path.abspath(path)
            return "success", "Completed", absolute_path

        except (URLError, HTTPError, ssl.CertificateError, IncompleteRead, BadStatusLine, IOError) as e:
            return "fail", f"Error: {e}", None

    def _get_all_items(self, image_objects, main_directory, dir_name, limit, arguments):
        items = []
        abs_path_list = []
        errorCount = 0
        i = 0
        count = 1
        while count <= limit and i < len(image_objects):
            obj = self.format_object(image_objects[i])
            if not obj or not obj.get("image_link"):
                i += 1
                continue

            status, message, absolute_path = self.download_image(
                obj["image_link"],
                main_directory,
                dir_name,
                count,
                arguments.get("prefix"),
                arguments.get("no_numbering"),
            )
            
            if status == "success":
                abs_path_list.append(absolute_path)
                count += 1
            else:
                errorCount += 1
            
            i += 1
        
        return abs_path_list, errorCount

    def download(self, arguments):
        paths = {}
        total_errors = 0

        search_keyword = [str(item) for item in arguments.get("keywords", "").split(",")]
        limit = int(arguments.get("limit", 100))
        main_directory = arguments.get("output_directory", "downloads")
        
        for keyword in search_keyword:
            dir_name = keyword if not arguments.get("no_directory") else ""
            self.create_directories(main_directory, dir_name)

            params = self.build_url_parameters(arguments)
            url = self.build_search_url(keyword, params, arguments.get("safe_search"))

            image_objects = self.download_page(url)
            if image_objects is None:
                print(f"Failed to fetch images for '{keyword}'")
                continue

            abs_paths, errors = self._get_all_items(image_objects, main_directory, dir_name, limit, arguments)
            paths[keyword] = abs_paths
            total_errors += errors

        return paths, total_errors