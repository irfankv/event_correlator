import re
import datetime
import os
import sys
import pymongo
import json
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import time

client = pymongo.MongoClient("asr9k-dtpxe-lnx.cisco.com",27017)
db = client.bng.dev_reg


class MacDatabase:
	
	def insert(self, user, ip, device_name, username, password, device_details):
		self.user = user
		self.ip = ip
		self.device_name = device_name
		self.username = username
		self.password = password
		self.device_details = device_details
		try:
			db.insert_one(
				{
				    "user":                  self.user,
					"ip":                    self.ip,
					"device_name":           self.device_name,
					"username":              self.username,
					"password":              self.password,
					"device_details":		 self.device_details
				}
			)
			return True
		except Exception as e:
			print(str(e))
			return False

	def findmac(self, device):	
		try :
			faqs = db.find({'device_name': device})
			return faqs
		except Exception as e:
			print(str(e))
			return False

	def count_collec(self):
		return(db.count())

	def findUserDevice(self, username, device):	
		try :
			res = db.find_one({'user' : username, 'device_name': device})
			return res
		except Exception as e:
			print(str(e))
			return False
