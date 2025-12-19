import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, TypeVar, Union

import frappe

BASE_DIR = Path(__file__).parent

# Colored logging setup
COLORS: dict[str, str] = {
	"DEBUG": "\033[94m",
	"INFO": "\033[92m",
	"WARNING": "\033[93m",
	"ERROR": "\033[91m",
	"CRITICAL": "\033[91m\033[1m",
	"RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		levelname = record.levelname
		if levelname in COLORS:
			record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
			record.msg = f"{COLORS[levelname]}{record.msg}{COLORS['RESET']}"
		return super().format(record)


def setup_logger(level: int = logging.INFO) -> logging.Logger:
	formatter = ColoredFormatter("%(message)s")
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logger = logging.getLogger()
	logger.setLevel(level)
	logger.handlers = [handler]
	return logger


logger = setup_logger()


def safe_insert_doc(
	doctype: str, data: dict[str, Any], unique_key: str | dict[str, Any] | None = None
) -> bool:
	"""
	Insert a document if not exists by unique_key.

	Args:
	    doctype: The Frappe DocType to insert
	    data: Document data to insert
	    unique_key: Unique key to check for existence
	        If dict: filter criteria, e.g. {"fieldname": value}
	        If str: assume a field name in data to use as unique filter

	Returns:
	    bool: True if document was inserted, False otherwise
	"""
	try:
		if unique_key is None:
			# fallback no unique key - always insert (not recommended)
			frappe.get_doc(data).insert()
			return True

		if isinstance(unique_key, str):
			filter_criteria = {unique_key: data.get(unique_key)}
		elif isinstance(unique_key, dict):
			filter_criteria = unique_key
		else:
			raise ValueError("unique_key must be str or dict")

		if frappe.db.exists(doctype, filter_criteria):
			return False

		frappe.get_doc(data).insert()
		return True

	except Exception as e:
		logger.exception(f"Error inserting {doctype}: {str(e)}")
		return False


def get_doc_or_create(
	doctype: str, filters: dict[str, Any], defaults: dict[str, Any] | None = None
) -> Any | None:
	"""
	Get a document by filters or create new with defaults.

	Args:
	    doctype: The Frappe DocType to fetch/create.
	    filters: A dictionary of filters to fetch the document.
	    defaults: A dictionary of default values to use if creating a new document.

	Returns:
	    Optional[Any]: The document if found or created, None on error
	"""
	if not isinstance(filters, dict):
		logger.error(f"Filters must be a dictionary, got: {type(filters)}")
		return None

	try:
		name = frappe.db.get_value(doctype, filters)
		if name:
			doc = frappe.get_doc(doctype, name)
			return doc
	except Exception as e:
		logger.debug(f"Document not found: {doctype} with {filters}. Will attempt to create. Reason: {e}")

	try:
		data = defaults.copy() if defaults else {}
		data.update(filters)
		doc = frappe.get_doc({"doctype": doctype, **data})
		doc.insert()
		return doc
	except Exception as e:
		logger.exception(f"Error creating new {doctype} with filters {filters}: {e}")
		return None


def safe_load_json(path: str | Path) -> list[Any] | dict[str, Any] | None:
	"""
	Safely load JSON from a file path.

	Args:
	    path: Path to the JSON file

	Returns:
	    Optional[Union[List[Any], Dict[str, Any]]]: Parsed JSON content or None on failure
	"""
	try:
		full_path = BASE_DIR / path if isinstance(path, str) else path
		with open(full_path, encoding="utf-8") as f:
			data = json.load(f)
			return data
	except Exception as e:
		logger.exception(f"Error loading JSON from {path}: {str(e)}")
		return None


def insert_from_json(filename: str, doctype: str, unique_key: str | dict[str, Any]) -> None:
	"""
	Generic function to insert records from JSON file.

	Args:
	    base_dir: Path or str directory where JSON files live
	    filename: JSON file name
	    doctype: DocType name to insert
	    unique_key: Unique key to check for existence
	"""
	path = Path(BASE_DIR) / filename
	if not path.exists():
		logger.warning(f"File {filename} not found in {BASE_DIR}")
		return

	records = safe_load_json(path)
	if not records:
		return

	success_count = 0
	for record in records:
		try:
			data = {"doctype": doctype, **record}
			if safe_insert_doc(doctype, data, unique_key):
				success_count += 1
		except Exception as e:
			logger.exception(f"Error inserting {doctype} record: {str(e)}")
