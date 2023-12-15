import os
import configparser
import logging
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from lxml import etree
from pathlib import Path

# Constants
MISSING = 'Missing'
DEFAULT_LOG_LEVEL = logging.DEBUG
USER_DIR = Path.home() / 'Documents' / 'xml_tool'
USER_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = USER_DIR / 'config.ini'


# Function to set up the configuration
def setup_config():
  # Check if config file exists
  if not CONFIG_PATH.exists():
    # Create a new config file with default values
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'TargetPath': 'ectd',
        'LogLevel': 'DEBUG',
        'FileExtension': '.xml',
        'FileName': 'index.xml',
    }
    with open(CONFIG_PATH, 'w') as configfile:
      config.write(configfile)

  # Read config file
  config = configparser.ConfigParser()
  config.read(CONFIG_PATH)

  # Get config values
  target_path = config.get('DEFAULT', 'TargetPath', fallback='ectd')
  log_level = config.get('DEFAULT', 'LogLevel', fallback=DEFAULT_LOG_LEVEL)
  file_extension = config.get('DEFAULT', 'FileExtension', fallback='.xml')
  file_name = config.get('DEFAULT', 'FileName', fallback='index.xml')

  return target_path, log_level, file_extension, file_name


# Function to set up the logging
def setup_logging(log_level):
  log_level = getattr(logging, log_level.upper(), DEFAULT_LOG_LEVEL)
  formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  debug_logger = logging.getLogger('debugLogger')
  debug_logger.setLevel(log_level)
  debug_handler = logging.FileHandler(USER_DIR / 'debug.log')
  debug_handler.setFormatter(formatter)
  debug_logger.addHandler(debug_handler)

  warning_logger = logging.getLogger('warningLogger')
  warning_logger.setLevel(log_level)
  warning_handler = logging.FileHandler(USER_DIR / 'warning.log')
  warning_handler.setFormatter(formatter)
  warning_logger.addHandler(warning_handler)

  return debug_logger, warning_logger


# Function to extract data from XML
def extract_data_from_xml(xml_file_path, debug_logger, warning_logger):
  debug_logger.debug(f"Processing file: {xml_file_path}")
  data = []
  try:
    tree = etree.parse(xml_file_path)
    root = tree.getroot()
    drug_substance_elements = root.xpath('//m3-2-s-drug-substance')
    drug_product_elements = root.xpath('//m3-2-p-drug-product')
    if drug_substance_elements:
      for drug_substance in drug_substance_elements:
        manufacturer_substance = drug_substance.get('manufacturer') or MISSING
        substance_name = drug_substance.get('substance') or MISSING
        data.append([
            'drug_substance', xml_file_path, manufacturer_substance,
            substance_name, 'N/A'
        ])
      debug_logger.debug(
          f"File {xml_file_path}: Found {len(drug_substance_elements)} 'drug_substance' elements"
      )
    else:
      data.append(['drug_substance', xml_file_path, MISSING, MISSING, 'N/A'])
    if drug_product_elements:
      for drug_product in drug_product_elements:
        manufacturer_drug = drug_product.get('manufacturer') or MISSING
        drug_product_name = drug_product.get('product-name') or MISSING
        form_of_drug = drug_product.get('dosageform') or MISSING
        data.append([
            'drug_product', xml_file_path, manufacturer_drug,
            drug_product_name, form_of_drug
        ])
  except etree.XMLSyntaxError:
    warning_logger.warning(
        f"File {xml_file_path} is not a well-formed XML file.")
  except Exception as e:
    warning_logger.warning(
        f"Unexpected error occurred while processing file {xml_file_path}: {e}"
    )
  return data


# Function to browse and extract data
def browse_and_extract(target_path, debug_logger, warning_logger,
                       file_extension, file_name):
  debug_logger.info(f"Starting to process files in directory: {target_path}")
  data = []
  with ThreadPoolExecutor() as executor:
    for foldername, subfolders, filenames in os.walk(target_path):
      xml_files = [
          f for f in filenames if f.endswith(file_extension) and f == file_name
      ]
      futures = [
          executor.submit(extract_data_from_xml,
                          Path(foldername) / filename, debug_logger,
                          warning_logger) for filename in xml_files
      ]
      for future in futures:
        data.extend(future.result())
  debug_logger.info(f"Finished processing files in directory: {target_path}")
  return data


# Main function
def main():
  target_path, log_level, file_extension, file_name = setup_config()
  debug_logger, warning_logger = setup_logging(log_level)

  # Use the function
  data = browse_and_extract(target_path, debug_logger, warning_logger,
                            file_extension, file_name)

  # Get current timestamp
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

  # Write the data to a CSV file with a timestamp in the filename
  if data:
    with open(USER_DIR / f'output_{timestamp}.csv', 'w', newline='') as f:
      writer = csv.writer(f)
      writer.writerow(['Type', 'File Path', 'Manufacturer', 'Name', 'Form'])
      writer.writerows(data)
  else:
    debug_logger.info("No data to write to CSV file.")


if __name__ == "__main__":
  main()
