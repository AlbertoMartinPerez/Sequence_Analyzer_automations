from dataclasses import dataclass, field
import time
import subprocess
from typing import Dict, List, Tuple
from loguru import logger

import selenium
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver

TIMING_FACTOR = 1


@dataclass
class BlastNCBIResults:
    description: str
    description_url: str
    scientific_name: str
    scientific_name_url: str
    max_score: int
    total_score: int
    query_cover: int
    e_value: int
    per_indentity: float
    accession_len: int
    accession: str
    accession_url: str


@dataclass
class BlastNCBI:
    megablast_page: str = field(
        default="https://blast.ncbi.nlm.nih.gov/Blast.cgi??DATABASE=nr&PAGE=MegaBlast"
    )
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

    def query_sequence(self, sequence: str) -> Tuple[BlastNCBIResults, Dict[str, str]]:
        # Open URL
        logger.info("Accessing URL, please wait...")
        self.web_driver.get(self.megablast_page)
        logger.info("URL loaded!")

        # Copy the sequence to the text area
        textarea = self.web_driver.find_element(By.XPATH, "//textarea[@name='QUERY']")
        textarea.click()
        textarea.clear()
        textarea.send_keys(sequence)

        time.sleep(0.5 * TIMING_FACTOR)

        # Check the "Uncultured/enviromental sample sequences"
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//label[@for='exclSeqUncult']"))
        ).click()
        time.sleep(0.5 * TIMING_FACTOR)

        # Click on the BLAST button
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='blastButton1']/input"))
        ).click()

        time.sleep(5 * TIMING_FACTOR)

        # Wait until results appear
        obtained_result = False

        while not obtained_result:

            # Check if the results have been provided
            try:
                self.web_driver.find_element(By.XPATH, "//div[@class='usa-alert-body']")
                obtained_result = True
            except selenium.common.exceptions.NoSuchElementException:
                # Get the amount of seconds to wait
                wait_seconds = int(
                    self.web_driver.find_element(By.XPATH, "//p[@class='WAITING']").text.split(" ")[
                        7
                    ]
                )
                logger.debug(f"Waiting {wait_seconds} seconds until receiving results from NCBI...")
                time.sleep(wait_seconds)

        # * Once the results have been retrieved by the database, get the data

        # Unselect all data
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//label[@for='select-all']"))
        ).click()

        time.sleep(0.5 * TIMING_FACTOR)

        # Then select the first 5
        species_results: List[BlastNCBIResults] = list()

        sequence_error: bool = False

        for num in range(1, 6):
            try:
                WebDriverWait(self.web_driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//label[@for='chk_{num}']"))
                ).click()
                time.sleep(0.5 * TIMING_FACTOR)
            except selenium.common.exceptions.TimeoutException:
                logger.warning(
                    f"Only found {num-1} species for current sequence. Saving all possible results..."
                )
                sequence_error = True
                break

            # Store the data for the selected species
            specie_record = self.web_driver.find_element(By.XPATH, f"//tbody/tr[@ind='{num}']")

            specie_description = specie_record.find_element(By.XPATH, "./td[@class='ellipsis c2']")
            scientific_name = specie_record.find_element(By.XPATH, "./td[@class='ellipsis c3']")
            max_score = specie_record.find_element(By.XPATH, "./td[@class='c6']").text
            total_score = specie_record.find_element(By.XPATH, "./td[@class='c7']").text
            query_cover = specie_record.find_element(By.XPATH, "./td[@class='c8']").text
            e_value = specie_record.find_element(By.XPATH, "./td[@class='c9']").text
            per_indentity = specie_record.find_element(By.XPATH, "./td[@class='c10']").text
            accession_len = specie_record.find_element(By.XPATH, "./td[@class='c11 acclen']").text
            accession = specie_record.find_element(By.XPATH, "./td[@class='c12 l lim']")

            species_results.append(
                BlastNCBIResults(
                    description=specie_description.find_element(By.XPATH, "./span/a").text,
                    description_url=specie_description.find_element(
                        By.XPATH, "./span/a"
                    ).get_attribute("href"),
                    scientific_name=scientific_name.find_element(By.XPATH, "./span/a").text,
                    scientific_name_url=scientific_name.find_element(
                        By.XPATH, "./span/a"
                    ).get_attribute("href"),
                    max_score=max_score,
                    total_score=total_score,
                    query_cover=query_cover,
                    e_value=e_value,
                    per_indentity=per_indentity,
                    accession_len=accession_len,
                    accession=accession.find_element(By.XPATH, "./a").text,
                    accession_url=accession.find_element(By.XPATH, "./a").get_attribute("href"),
                )
            )

        # Select the "Aligments" tab to extract the information of the sequences
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[contains(@class,'alignments')]"))
        ).click()
        time.sleep(0.5 * TIMING_FACTOR)

        # In the alignment view, select the "flat query-anchored with dots for identities" option
        WebDriverWait(self.web_driver, 20).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//select[@name='ALIGNMENT_VIEW' and @id='alignViewSelect']/option[@value='FlatQueryAnchored']",
                )
            )
        ).click()
        time.sleep(1.5 * TIMING_FACTOR)

        # Get the characters of all aligments for the 5 species
        num_query_ranges = len(self.web_driver.find_elements(By.XPATH, "//span[@class='alnRn']"))

        logger.debug(f"{num_query_ranges = }")

        species_align_dict: Dict[int, str] = dict()

        for q_range in range(1, num_query_ranges + 1):

            # This is just the alignment of one of the query ranges for all 5 species
            q_alignment = self.web_driver.find_element(
                By.XPATH, f"//*[@id='qarow_{q_range}']"
            ).text.split("\n")

            # Only get the offset from the queried unidentified specie (the sequence queried)
            nucleotide_offset = min(
                [
                    q_alignment[0].find("A"),
                    q_alignment[0].find("C"),
                    q_alignment[0].find("G"),
                    q_alignment[0].find("T"),
                ]
            )
            logger.debug(f"{nucleotide_offset = }")

            # For each alignment in the range, only get the sequence without the numbers or extra information
            for specie_num, q_al in enumerate(q_alignment):
                if q_range == 1:
                    species_align_dict.update({specie_num: q_al[0 : nucleotide_offset + 60]})
                else:
                    species_align_dict[specie_num] += q_al[
                        nucleotide_offset : nucleotide_offset + 60
                    ]

        return species_results, species_align_dict, sequence_error
