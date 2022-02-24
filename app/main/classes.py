import json
import datetime
from flask import session, request


class ComposerBars(object):

    def __init__(self, lastname, xposition, width, yposition, barheight, flag, pId, catalogued):
        self.name = lastname
        self.xposition = xposition
        self.width = width
        self.yposition = yposition
        self.barheight = barheight
        self.flag = flag
        self.id = pId
        self.catalogued = catalogued


class ComposerChart(object):

    width = 0
    xposition = 0
    yposition = 0

    def __init__(self, composerchart, datemin, datemax):
        self.composerchart = composerchart
        self.date_min = int(datemin)
        self.date_max = int(datemax)  # to add scaling functionality later

    def create_chart(self):

        self.composers = list()
        composerno = 0
        barheight = 19
        now = datetime.datetime.now()
        this_year = now.year

        with open('app/static/countries.json') as f:
            flags = json.load(f)

        if len(self.composerchart) < 1:
            self.svgheight = 0

        else:
            for composer in self.composerchart:

                composerno += 1
                name = composer.name_short
                pId = composer.id
                catalogued = composer.catalogued

                if composer.died >= this_year:
                    composer.died = this_year

                xposition1 = self.get_x_position(int(composer.born))
                xposition2 = self.get_x_position(int(composer.died))
                width = xposition2 - xposition1
                yposition = composerno * barheight

                flag = flags[composer.nationality]
                flag = flag.lower()

                self.composers.append(ComposerBars(name, xposition1, width, yposition, barheight, flag, pId, catalogued))

            self.svgheight = yposition + barheight * 2

    def get_x_position(self, date):
        scale_factor = ((self.date_max - self.date_min) / 100)
        position = (date - self.date_min) / scale_factor
        return position

    def generate_dates(self):

        rangeDate = self.date_max - self.date_min

        bicentury = rangeDate / 200
        century = rangeDate / 100
        fifty = rangeDate / 50
        quarter = rangeDate / 25
        decade = rangeDate / 10

        if request.MOBILE:
            numLabels = 6
        else:
            numLabels = 13

        rangeList = [bicentury, century, fifty, quarter, decade]
        rangeListValues = [200, 100, 50, 25, 10]

        i = 0
        labelSize = 0
        numLines = 0
        for each in rangeList:
            if each <= numLabels:
                labelSize = i
                numLines = rangeList[i]
                i += 1
        yearGap = rangeListValues[labelSize]

        i = 0
        year_list = {}
        while i <= numLines:
            year = int(self.date_min + yearGap * i)
            year_list[year] = self.get_x_position(year)
            i += 1

        return year_list

    def generate_eras(self):

        with open('app/static/eras.json') as f:
            periodArray = json.load(f)

        for line in periodArray:
            start = self.get_x_position(line[1])
            end = self.get_x_position(line[2])
            line.append(start)
            line.append(end)

        return periodArray


class SortFilter(object):

    def get_era_filter(self, period):
        date_minmax = []

        with open('app/static/eras_filter.json') as f:
            periodArray = json.load(f)

            for era in periodArray:
                if era[0] == period:
                    if era[0] == "Romantic" or era[0] == "20th/21st Century":
                        date_minmax = [era[1], era[2], "region"]
                        break
                    else:
                        date_minmax = [era[1], era[2], "birth"]
                        break
                elif period == "Common":
                    date_minmax = [1500, 1907, "region"]
                elif period == "Early":
                    date_minmax = [1000, 1600, "birth"]
                elif period == "All":
                    date_minmax = [1000, 2051, "region"]
                else:
                    date_minmax = [1500, 2051, "region"]

        return date_minmax

    def get_era_view(self, period):
        date_minmax = []

        with open('app/static/eras_view.json') as f:
            periodArray = json.load(f)

            for era in periodArray:
                if era[0] == period:
                    if era[0] == "Romantic" or era[0] == "20th/21st Century":
                        date_minmax = [era[1], era[2], "region"]
                        break
                    else:
                        date_minmax = [era[1], era[2], "birth"]
                        break
                elif period == "Common":
                    date_minmax = [1500, 2050, "region"]
                elif period == "Early":
                    date_minmax = [1000, 1800, "birth"]
                elif period == "All":
                    date_minmax = [1000, 2200, "region"]
                else:
                    date_minmax = [1500, 2000, "region"]

        return date_minmax


class SearchObject(object):

    def __init__(self, composer, genre, title, cat):
        self.composer = composer
        self.genre = genre
        self.title = title
        self.cat = cat
        self.placeholders = False
        self.check = composer + genre + title + cat


class Artist(object):

    def __init__(self, artist, composer, genre, title, cat):
        self.artist = artist
        self.composer = composer
        self.genre = genre
        self.title = title
        self.cat = cat
        self.placeholders = False
        self.check = artist + composer + genre + title + cat
