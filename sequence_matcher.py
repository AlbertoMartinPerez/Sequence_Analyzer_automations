from dataclasses import dataclass, field
import time
import subprocess
from typing import Dict, List, Tuple
import re
from loguru import logger

import os

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

TIMING_FACTOR = 1


@dataclass
class RDPSequenceData:
    id: str
    # name: str
    # strain: str
    # other_id: str
    sequence: str


@dataclass
class CorrectedSequence:
    id: str
    specie_name: str
    sequence: str
    num_seq: int


@dataclass
class SequenceMatcher:
    web_page: str = field(default="http://rdp.cme.msu.edu/seqmatch/")
    web_driver: WebDriver = field(init=False)
    download_path: str = field(init=False)

    def quit(self) -> None:
        """
        Removes webdriver and kills all Google Chrome and ChromeDriver processes.
        """
        self.web_driver.quit()
        time.sleep(1 * TIMING_FACTOR)
        subprocess.call("TASKKILL /f  /IM  CHROME.EXE")
        subprocess.call("TASKKILL /f  /IM  CHROMEDRIVER.EXE")
        time.sleep(1 * TIMING_FACTOR)

    def configure_browser(self, download_path: str, driver_path: str) -> WebDriver:
        """
        Configure Selenium browser and then returns the WebDriver object.
        """
        self.download_path = download_path

        options = webdriver.ChromeOptions()
        options.add_argument("no-sandbox")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": download_path,  # Change default directory for downloads
                "download.prompt_for_download": False,  # To auto download the file
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,  # It will not show PDF directly in chrome
            },
        )

        # Hide warning messages (like USB warning messages)
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Mute the audio
        options.add_argument("--mute-audio")

        self.web_driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.web_driver.maximize_window()

    def wait_for_downloads(self) -> None:
        """Wait for downloads to finish with a specified timeout."""
        waiting = True

        while waiting:
            time.sleep(1)

            files: List[str] = os.listdir(self.download_path)

            still_downloading = [True if file.endswith(".crdownload") else False for file in files]

            if any(still_downloading):
                waiting = True
            else:
                waiting = False

    def query_sequence(self, sequence: str) -> str:
        """
        Query a sequence to find selectable matches. Returns the name of the file downloaded.
        """
        # Open URL
        logger.info("Accessing URL, please wait...")
        self.web_driver.get(self.web_page)
        logger.info("URL loaded!")

        try:
            # Copy the sequence to the text area
            textarea = self.web_driver.find_element(By.XPATH, "//textarea[@name='sequence']")
        except NoSuchElementException:
            # If a previous query has been made, must click on "new match" button
            WebDriverWait(self.web_driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div[2]/a[1]"))
            ).click()

            textarea = self.web_driver.find_element(By.XPATH, "//textarea[@name='sequence']")

        textarea.click()
        textarea.clear()
        textarea.send_keys(sequence)

        # Check the "Strain" radio button to "Type"
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@name, 'strain') and contains(@value, 'type')]")
            )
        ).click()

        # Check the "Source" radio button to "Isolates"
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@name, 'source') and contains(@value, 'isolates')]")
            )
        ).click()

        # Check the "Size" radio button to "Both"
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@name, 'size') and contains(@value, 'both')]")
            )
        ).click()

        # Click on the "Submit" button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@name, 'submit') and contains(@class, 'button')]")
            )
        ).click()

        time.sleep(5 * TIMING_FACTOR)

        # Click on the "view selectable matches"
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), '[view selectable matches]')]")
            )
        ).click()

        # Find all elements that can be selectable
        checkboxes = self.web_driver.find_elements(
            By.XPATH, "//input[contains(@name, 'visibleSeqs') and contains (@type, 'checkbox')]"
        )
        num_selectable_seqs = len(checkboxes)

        logger.debug(f"Number of checkboxes with selectable matches found: {num_selectable_seqs}")

        # Click on every selectable match checkbox
        for checkbox in checkboxes:
            checkbox.click()

        # Click on "save selection and return to summary" button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//input[contains(@class, 'button') and contains(@value, 'Save selection and return to summary')]",
                )
            )
        ).click()

        # Click on "SEQCART" menu button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'SeqCart')]"))
        ).click()

        # Click on "download" button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'download')]"))
        ).click()

        # Click on "Remove all gaps" radio button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[contains(@id, 'remall')]"))
        ).click()

        # Click on download button containing "RDPX-Bacteria-2" text
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    # f"//input[contains(@class, 'button') and contains(@value, 'Download {num_selectable_seqs} sequence(s) for alignment model: RDPX-Bacteria-2')]",
                    "//input[contains(@class, 'button') and contains(@value, 'RDPX-Bacteria-2')]",
                )
            )
        ).click()

        # Wait for file to be downloaded
        self.wait_for_downloads()

        # Check the number of sequences that will be downloaded in the RDPX-Bacteria-2 file
        button_rdpx_bacteria_2 = self.web_driver.find_element(
            By.XPATH, "//input[contains(@class, 'button') and contains(@value, 'RDPX-Bacteria-2')]"
        )
        button_value_attr = button_rdpx_bacteria_2.get_attribute("value")
        num_selectable_seqs = int(button_value_attr.split("Download ")[-1].split(" ")[0])

        return f"rdp_download_{num_selectable_seqs}seqs.fa"


def modify_rdp_file(file_path: str, output_file: str, main_sequence: CorrectedSequence) -> None:

    sequences: List[RDPSequenceData] = list()

    # Read the .fa file
    with open(file_path) as file:

        lines = file.readlines()

        for line in lines:
            if ">" in line:

                # Get the information of the RDP Sequence
                rdp_seq = RDPSequenceData(
                    id=line,
                    sequence="",
                )

                sequences.append(rdp_seq)
            else:
                # Add the sequence to the RDP specie directly from the list of "sequences"
                # Replace the "-" with "". Remove also \n
                sequences[-1].sequence = sequences[-1].sequence + line.replace("-", "").replace(
                    "\n", ""
                )

    # Save to new file
    with open(f"{output_file}.fa", "w") as file:
        # Write original sequence first!
        file.write(
            f">(ORIGINAL SEQUENCE) {main_sequence.id} - {main_sequence.specie_name}\n{main_sequence.sequence}\n\n"
        )

        # Write queried sequences
        for sequence in sequences:
            file.write(sequence.id)
            file.write(sequence.sequence)
            file.write("\n\n")


if __name__ == "__main__":
    PATH_CHROME_DRIVER = "C:/Program Files (x86)/chromedriver.exe"
    dir_sequences = "C:/Users/alber/Desktop/Sequence_automations/Placa_2/Sequence_match"
    corrected_seqs_file = "C:/Users/alber/Desktop/Sequence_automations/Placa_2/Sequence_match/Secuencias_corregidas.txt"

    corrected_sequences: List[CorrectedSequence] = list()

    seq_line_num = 0
    num_seq = 1
    # Read file with corrected sequences
    with open(corrected_seqs_file, "r") as file:
        lines = file.readlines()

        for line in lines:
            if ">" in line:
                seq_line_num += 1

                # Get the information of the Sequence
                corr_seq = CorrectedSequence(
                    id=line.replace(">", "").replace("\n", ""),
                    specie_name="",
                    sequence="",
                    num_seq=num_seq,
                )
                num_seq += 1

                corrected_sequences.append(corr_seq)
            elif "%" in line or seq_line_num == 2:
                seq_line_num = 0
                corrected_sequences[-1].specie_name = line.replace("\n", "")
            elif line.startswith(("T", "A", "G", "C")):
                seq_line_num += 1
                # Add the sequence to the RDP specie directly from the list of "sequences"
                # Replace the "-" with "". Remove also \n
                corrected_sequences[-1].sequence = line.replace("\n", "")

    for sequence in corrected_sequences:

        # if sequence.num_seq <= 96:
        #     continue

        logger.info(f"Analyzing sequence {sequence.id} - Number {sequence.num_seq}")

        # If a sequence is empty, it means it should not be analyzed!
        if sequence.sequence == "":
            logger.warning(
                f"{sequence.id} {sequence.specie_name} has no sequence. Not quering to database!"
            )
            continue

        # Open and configure Chrome using Selenium
        sequence_matcher = SequenceMatcher()
        sequence_matcher.configure_browser(
            download_path=dir_sequences, driver_path=PATH_CHROME_DRIVER
        )

        file_name = sequence_matcher.query_sequence(sequence.sequence)

        modify_rdp_file(
            file_path=f"{dir_sequences}\\{file_name}",
            output_file=f"{dir_sequences}\\{sequence.id} - {sequence.specie_name.replace('/', '-')}",
            main_sequence=sequence,
        )

        # Remove downloaded file
        os.remove(f"{dir_sequences}\\{file_name}")

        sequence_matcher.quit()
