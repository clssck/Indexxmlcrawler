import os
import logging
import csv
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from lxml import etree
from pathlib import Path
from tqdm import tqdm

# Constants
MISSING = 'Missing'
DEFAULT_LOG_LEVEL = 'DEBUG'
SCRIPT_DIR = Path(__file__).parent.absolute()
FILE_EXTENSION = '.xml'
FILE_NAME = 'index.xml'

# Function to set up the logging
def setup_logging(log_level, output_dir):
    log_level = getattr(logging, log_level.upper(), logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    debug_logger = logging.getLogger('debugLogger')
    debug_logger.setLevel(log_level)
    debug_handler = logging.FileHandler(output_dir / 'debug.log')
    debug_handler.setFormatter(formatter)
    debug_logger.addHandler(debug_handler)

    warning_logger = logging.getLogger('warningLogger')
    warning_logger.setLevel(log_level)
    warning_handler = logging.FileHandler(output_dir / 'warning.log')
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
    xml_file_count = 0  # Add this line
    with ThreadPoolExecutor() as executor:
        tasks = []
        for foldername, subfolders, filenames in os.walk(target_path):
            xml_files = [
                f for f in filenames if f.endswith(file_extension) and f == file_name
            ]
            xml_file_count += len(xml_files)  # Add this line
            for filename in xml_files:
                tasks.append((Path(foldername) / filename, debug_logger, warning_logger))
        results = list(tqdm(executor.map(lambda params: extract_data_from_xml(*params), tasks), total=len(tasks)))
        for result in results:
            data.extend(result)
    debug_logger.info(f"Finished processing files in directory: {target_path}")
    return data, xml_file_count

# Main function
def main():
    # Use argparse to handle command line arguments
    parser = argparse.ArgumentParser(description='Process some XML files.')
    parser.add_argument('target_path', help='The target path to process')
    parser.add_argument('-o', '--output_dir', default=SCRIPT_DIR,
                        help='The output directory (optional)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    debug_logger, warning_logger = setup_logging(DEFAULT_LOG_LEVEL, output_dir)

    # Use the function
    data, xml_file_count = browse_and_extract(args.target_path, debug_logger, warning_logger,
                                              FILE_EXTENSION, FILE_NAME)

    # Count the number of 'drug_substance' and 'drug_product' entries
    drug_substance_count = sum(1 for row in data if row[0] == 'drug_substance')
    drug_product_count = sum(1 for row in data if row[0] == 'drug_product')

     # Print the summary
    print("\nSummary of results:")
    print("-" * 20)
    print(f"Drug substances found: {drug_substance_count}")
    print(f"Drug products found: {drug_product_count}")
    print(f"XML files parsed: {xml_file_count}") 

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write the data to a CSV file with a timestamp in the filename
    if data:
        with open(output_dir / f'output_{timestamp}.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'File Path', 'Manufacturer', 'Name', 'Form'])
            writer.writerows(data)
    else:
        debug_logger.info("No data to write to CSV file.")


if __name__ == "__main__":
    main()