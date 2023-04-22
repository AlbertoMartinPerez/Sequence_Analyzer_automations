from datetime import datetime
from typing import List
from pathlib import Path

from loguru import logger

from blast_ncbi import BlastNCBI
from data_saver import save_alignments_to_notes, save_results_in_word


def main(dir_files: str):

    # Save log fil e
    logger.add(
        f"{dir_placa}\log\{datetime.today().strftime('%Y-%m-%d_%H-%M-%S')}.log",
        level="DEBUG",
    )

    ncbi = BlastNCBI()
    ncbi.configure_browser(download_path=dir_files, driver_path=PATH_CHROME_DRIVER)

    # Get path from every file
    downloaded_files: List[Path] = list()
    for path in Path(dir_files).glob("*.txt"):
        # Only copy files and not directories
        if path.is_file():
            downloaded_files.append(path)

    for file_num, file in enumerate(downloaded_files):

        # if file_num != 97:
        #     continue

        sequence_id = file.name.split("_")[1]
        logger.info(f"Working with {sequence_id = }")

        # Read lines from file
        with open(file.absolute()) as f:
            lines = f.readlines()

            header, num_nucleots = lines[0].split("\t")
            num_nucleots = num_nucleots.removesuffix("\n")
            # logger.debug(f"{header = }")
            # logger.debug(f"{num_nucleots = }")

            sequence = "".join(lines[1:]).replace("\n", "")
            logger.debug(f"{sequence = }")
            logger.debug(f"{sequence[10:1100] = }")

        # Query the full sequence without cropping
        logger.info("Quering full sequence to MEGABLAST!")
        species_results, alignments, error = ncbi.query_sequence(sequence=sequence)

        logger.info("Saving full sequence results...")
        save_results_in_word(
            path=f"{dir_description}",
            file_name=f"{sequence_id}_full",
            species=species_results,
        )
        save_alignments_to_notes(
            path=f"{dir_alignments}",
            file_name=f"{sequence_id}_full",
            alignments=alignments,
        )

        # If there has been an error finding similar species to current sequence,
        # then continue with next sequence without cropping the current one
        if error:
            continue

        # Query the sequence with defined cropped
        logger.info("Quering cropped sequence to MEGABLAST!")
        species_results_crop, alignments_crop, error = ncbi.query_sequence(
            sequence=sequence[10:1100]
        )

        logger.info("Saving cropped sequence results...")
        save_results_in_word(
            path=f"{dir_description}",
            file_name=f"{sequence_id}_10-1100_crop",
            species=species_results_crop,
        )
        save_alignments_to_notes(
            path=f"{dir_alignments}",
            file_name=f"{sequence_id}_10-1100_crop",
            alignments=alignments_crop,
        )

    ncbi.quit()


if __name__ == "__main__":
    PATH_CHROME_DRIVER = "C:/Program Files (x86)/chromedriver.exe"
    dir_placa = "C:/Users/alber/Desktop/Sequence_automations/data/Placa_2/"

    dir_description = rf"{dir_placa}Descriptions/"
    dir_alignments = rf"{dir_placa}Alignments/"
    main(dir_files=dir_placa)
