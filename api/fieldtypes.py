import re

# All _error variables start with no capital letter and end with a period.
numeric_error = "must be a number."
def numeric(str):
	if not re.match('^\d+$', str):
		return None
	return str
	
integer_error = "must be a number."
def integer(str):
	if not re.match('^\d+$', str):
		return None
	return int(str)
	
float_num_error = "must be a number."
def float_num(str):
	if not re.match('^\d+(.\d+)?$', str):
		return None
	return float(str)
	
long_num_error = "must be a number."
def long_num(str):
	if not re.match('^\d+$', str):
		return None
	return long(str)

rating_error = "must >= 1.0 and <= 5.0 in increments of	0.5."
def rating(str):
	r = float_num(str)
	if not r:
		return None
	if r < 1 or r > 5:
		return None
	if not (r * 10) % 5 == 0:
		return None
	return r
