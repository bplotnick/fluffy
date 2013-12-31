import time
import os
import json
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from fluffy.models import StoredFile
from fluffy.utils import get_backend, get_human_size, encode_obj, decode_obj, \
	trim_filename
from fluffy.backends import BackendException

def index(request):
	return render(request, "index.html")

def upload(request):
	"""Process an upload, storing each uploaded file with the configured
	storage backend. Redirects to a status page which displays the uploaded
	file(s).

	Returns JSON containing the URL to redirect to; the actual redirect is done
	by the JavaScript on the upload page.
	"""
	try:
		backend = get_backend()
		file_list = request.FILES.getlist("file")
		stored_files = [StoredFile(file) for file in file_list]

		start = time.time()
		print("Storing {} files...".format(len(stored_files)))

		for stored_file in stored_files:
			print("Storing {}...".format(stored_file.name))
			backend.store(stored_file)

		elapsed = time.time() - start
		print("Stored {} files in {:.1f} seconds.".format(len(stored_files), elapsed))

		details = [get_details(f) for f in stored_files]
		details_encoded = encode_obj(details)

		details_url = reverse("details", kwargs={"enc": details_encoded})

		response = {
			"success": True,
			"redirect": details_url
		}
	except BackendException as e:
		print("Error storing files: {}".format(e))
		print("\t{}".format(e.display_message))

		response = {
			"success": False,
			"error": e.display_message
		}
	except Exception as e:
		print("Unknown error storing files: {}".format(e))

		response = {
			"success": False,
			"error": "An unknown error occured."
		}

	return HttpResponse(json.dumps(response), content_type="application/json")

def get_details(stored_file):
	"""Returns a tuple of details of a single stored file to be included in the
	parameters of the info page.

	Details in the tuple:
	  - stored name
	  - human name without extension (to save space)
	  - human size (to save space)
	"""
	human_name = os.path.splitext(stored_file.file.name)[0]
	human_size = get_human_size(stored_file.file.size)

	return (stored_file.name, human_name, human_size)

def details(request, enc=encode_obj([])):
	"""Displays details about an upload (or any set of files, really).

	enc is the encoded list of detail tuples, as returned by get_details.
	"""
	req_details = decode_obj(enc)
	details = [get_full_details(file) for file in req_details]

	return render(request, "details.html", {"details": details})

def get_full_details(file):
	"""Returns a dictionary of details for a file given a detail tuple."""
	stored_name = file[0]
	name = file[1] # original file name
	size = file[2]
	ext = os.path.splitext(stored_name)[1]

	return {
		"download_url": settings.FILE_URL.format(name=stored_name),
		"info_url": settings.INFO_URL.format(name=stored_name),
		"name": trim_filename(name + ext, 17), # original name is stored w/o extension
		"size": size,
		"extension": ext[1:] if ext else "unknown"
	}
