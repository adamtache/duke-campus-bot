# -*- coding: utf-8 -*-
import json
import urllib

from bs4 import BeautifulSoup, element
from datetime import date, datetime, time, timedelta
from models.availability import Availability
from models.schedule import Schedule
from scraper import Scraper
from util import datetime_util

DUKE_DINING_MENUS_HOURS_URL = 'https://studentaffairs.duke.edu/forms/dining/menus-hours/'

class RestaurantScraper(Scraper):

	def get_schedules(self):
		soup = BeautifulSoup(
	    	urllib.urlopen(DUKE_DINING_MENUS_HOURS_URL).read(),
	    	'html.parser',
	    )
		restaurants_table_html = soup.body.find(id='schedule_table')
		restaurant_table_rows_html = self._get_all_restaurant_rows(restaurants_table_html)
		dates_from_website = self._get_dates_listed_on_website(restaurants_table_html)
		return self._create_restaurant_schedules_with_availabilities(
			restaurant_table_rows_html,
			dates_from_website,
		)

	def _get_all_restaurant_rows(self, restaurants_table_html):
		zebra_rows = restaurants_table_html.find_all(id='schedule_zebra_row')
		no_zebra_rows = restaurants_table_html.find_all(id='schedule_no_zebra_row')
		return zebra_rows + no_zebra_rows

	def _get_dates_listed_on_website(self, restaurants_table_html):
		row_of_dates = restaurants_table_html.find(id='schedule_header_row')
		return self._create_dates_for_listed_dates(row_of_dates)

	def _create_dates_for_listed_dates(self, row_of_dates):
		dates = []
		for date_cell in row_of_dates.find_all(id='schedule_time_data'):
			dates.append(self._create_date_from_listing(date_cell))
		return dates

	def _create_date_from_listing(self, date_cell):
		self._get_rid_of_br_tags(date_cell)
		cell_contents = date_cell.contents
		day_of_week_month_date = cell_contents[0] + " " + cell_contents[1]
		date_time = datetime.strptime(day_of_week_month_date, '%A %B %d')
		date_time = datetime_util.datetime_with_current_year(date_time)
		return date_time.date()

	def _get_rid_of_br_tags(self, date_cell):
		for br_tag in date_cell.findAll('br'):
		    br_tag.extract()

	def _create_restaurant_schedules_with_availabilities(self, restaurant_table_rows, dates):
		schedules = []
		for restaurant_row in restaurant_table_rows:
			schedules.append(
				self._create_restaurant_schedule_with_availabilities_for_dates(
					restaurant_row, 
					dates,
				)
			)
		return schedules

	def _create_restaurant_schedule_with_availabilities_for_dates(self, restaurant_row, dates):
		restaurant_name = restaurant_row.find(id='schedule_place_data').find('a').string
		rows_of_daily_opening_closing_times = restaurant_row.find_all(
			id='schedule_time_data',
		)
		availabilities = self._get_availabilities_from_rows_for_dates(
			rows_of_daily_opening_closing_times, 
			dates,
		)
		return Schedule(restaurant_name, availabilities)

	def _get_availabilities_from_rows_for_dates(self, rows_of_daily_opening_closing_times, dates):
		availabilities = []
		for cell_index, opening_closing_time_cell in enumerate(
			rows_of_daily_opening_closing_times
		):
			date = dates[cell_index]
			avails = self._create_availabilities(date, opening_closing_time_cell)
			for avail in avails:
				availabilities.append(avail)
		return availabilities

	def _create_availabilities(self, date, opening_closing_time_cell):
		opening_closing_datetimes = self._get_opening_closing_datetimes(
			date,
			opening_closing_time_cell,
		)
		availabilities = []
		for opening_closing in opening_closing_datetimes:
			availabilities.append(
				self._create_availability_for_date(
					opening_closing,
					date,
				)
			)
		return availabilities

	def _create_availability_for_date(self, opening_closing_datetimes, date):
		if len(opening_closing_datetimes) < 2:
			return Availability(date, None, None)
		opens_at = opening_closing_datetimes[0]
		closes_at = opening_closing_datetimes[1]
		return Availability(date, opens_at, closes_at)

	def _get_opening_closing_datetimes(self, date, opening_closing_time_cell):
		time_contents = opening_closing_time_cell.contents
		opening_closing_datetimes = []
		for time_string in time_contents:
			if type(time_string) is not element.NavigableString:
				continue
			time_parts = time_string.split('-')
			if len(time_parts) < 2:
				opening_closing_datetimes.append((None, None))
				continue
			opens_at_text = time_parts[0]
			closes_at_text = time_parts[1]
			opening_closing_datetimes.append(
				self._create_opening_closing_datetime(
					opens_at_text,
					closes_at_text,
					date,
				)
			)
		return opening_closing_datetimes

	def _create_opening_closing_datetime(self, opens_at_text, closes_at_text, date):
		opens_at = self._create_datetime(opens_at_text, date)
		closes_at = self._create_datetime(closes_at_text, date)
		if closes_at < opens_at:
			closes_at += timedelta(days=1)
		return (opens_at, closes_at)

	def _create_datetime(self, time_text, date):
		"""Creates timezone unaware datetime, as ndb on GAE only supports UTC and
		not timezone aware datetimes."""
		date_time = datetime.strptime(time_text.rstrip(), '%I:%M%p').time()
		date_time = datetime.combine(date, date_time)
		return datetime_util.datetime_with_current_year(date_time)
