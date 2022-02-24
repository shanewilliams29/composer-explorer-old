import math
from flask import session, request
from app.main.classes import ComposerChart


class BornDied(object):

    def __init__(self, born, died, datemin, datemax):

        def get_x_position(date):
            scale_factor = ((self.date_max - self.date_min) / 100)
            position = (date - self.date_min) / scale_factor
            return position

        self.born = born
        self.died = died
        self.date_min = int(datemin)
        self.date_max = int(datemax)
        self.xborn = get_x_position(born)
        self.xdied = get_x_position(died)

class Masterpieces(object):

    def __init__(self, masterpiece_list, datemin, datemax):

        #masterpiece_date = masterpiece_list[1]['date']
        self.date_min = int(datemin)
        self.date_max = int(datemax)
        self.masterpiece_list = masterpiece_list

    def generate_masterpieces(self):

        def get_x_position(date):
            scale_factor = ((self.date_max - self.date_min) / 100)
            position = (date - self.date_min) / scale_factor
            return position

        for masterpiece in self.masterpiece_list:
            xdate = get_x_position(masterpiece['date'])
            masterpiece['xposition'] = xdate

        return self.masterpiece_list


class ComposerHeader(ComposerChart):

    def generate_dates(self, composer):

        if request.MOBILE:
            self.date_min = int(math.ceil(self.date_min / 25)) * 25 - 25
            self.date_max = int(math.ceil(self.date_max / 25)) * 25 + 100
        elif composer.view:
            self.date_min = int(str(composer.view)[:4])
            self.date_max = int(str(composer.view)[4:])
        else:
            self.date_min = int(math.ceil(self.date_min / 25)) * 25 - 25
            self.date_max = int(math.ceil(self.date_max / 25)) * 25 + 50

        rangeDate = self.date_max - self.date_min

        bicentury = rangeDate / 200
        century = rangeDate / 100
        fifty = rangeDate / 50
        quarter = rangeDate / 25
        decade = rangeDate / 10

        if request.MOBILE:
            numLabels = 6
        else:
            numLabels = 20

        rangeList = [bicentury, century, fifty, quarter, decade]
        rangeListValues = [200, 100, 50, 25, 10]

        i = 0
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

    def generate_ages(self, year_list, born, died):

        ages = {}
        for year in year_list:
            if year >= born and year <= died:
                age = year - born
                ages[age] = year_list[year]

        return ages

    def create_chart(self, works):

        workno = 1
        barheight = 19
        yposition_final = 0

        if len(works) < 1:
            self.svgheight = 0

        else:
            for i in range(0, len(works)):
                if not works[i].genre == works[i - 1].genre or i == 0:
                    workno += 2
                    works[i].heading = works[i].genre

                if not works[i].cat == works[i - 1].cat or i == 0:
                    works[i].opus = works[i].cat
                    if works[i].suite:
                        works[i].opus = works[i].suite + ", " + works[i].cat

                if not works[i].date == works[i - 1].date:
                    works[i].opus = works[i].cat
                    if works[i].suite:
                        works[i].opus = works[i].suite + ", " + works[i].cat

                if works[i].cat.strip() == "":  # for works without opus
                    works[i].opus = " "

                workno += 1
                works[i].xposition = self.get_x_position(int(works[i].date))
                works[i].yposition = workno * barheight
                works[i].barheight = barheight
                yposition_final = workno * barheight

        self.svgheight = yposition_final + barheight * 2

        return works
