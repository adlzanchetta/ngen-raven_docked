from typing import Union
import multiprocessing
import pandas as pd
import numpy as np
import subprocess
import argparse
import shutil
import glob
import sys
import os
import re


# ## CONSTANTS ################################################################################### #


#
TEST_FDNA_KEYS_INT = {"ngnp", "nsub"}
TEST_FDNA_VALUES_NGTS = {'h', 'd'}
TEST_FDNA_VALUES_RVMD = {'gr4j', 'hbv', 'hmets', 'hymod', 'mohyse', 'sacsma', 'vic', 'blended', 'mixed'}

# 
TEST_SUBFDNA_RV_STANDALONE = "data_raven-standalone"
TEST_SUBFDNA_RV_IN_NGEN = "data_raven-in-nexgen"

# binary file paths
NGEN_BIN_FIPA = {
    "serial": {
        "d": "/ngen_daily_serial",
        "h": "/ngen_hourly_serial",
    },
    "parallel": {
        "d": "/ngen_daily_parallel",
        "h": "/ngen_hourly_parallel",
    }
}
RAVEN_STANDALONE_BIN_FIPA = "/Raven"

# files need to be placed into specific folders in order to run the models
RAVEN_RUN_DATA_FDPA = "/data_raven"
NGEN_RUN_DATA_FDPA = "/data"
NGEN_RUN_OUTPUT_FDPA = os.path.join(NGEN_RUN_DATA_FDPA, "3_models_outputs")
COMPARING_RUNS_DATA_FDPA = "/data_comparison"

# exit codes
PASSING, FAILING = 0, 1

DATETIME_FORMAT = "%Y-%m-%d %H:%M"

MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE = 0.015  # 1.5%, chosen arbitrarily


# ## FUNCTIONS ################################################################################### #


def assess_test_subfolders(test_folder_path: str, meta_info: dict) -> None:
    """
    Assess the subfolders in the example/test folder
    """

    def assess_subfolder(subfolder_path: str) -> None:
        if not os.path.exists(subfolder_path):
            fail_exit(f"Subfolder '{subfolder_path}' does not exist.")
        elif not os.path.isdir(subfolder_path):
            fail_exit(f"Path '{subfolder_path}' exists but is not a folder.")
        return None

    if ("ngnp" in meta_info) or ("ngts" in meta_info):
        assess_subfolder(os.path.join(test_folder_path, TEST_SUBFDNA_RV_IN_NGEN))

    if "rvmd" in meta_info:
        assess_subfolder(os.path.join(test_folder_path, TEST_SUBFDNA_RV_STANDALONE))

    return None


def clean_folder_used_for_model_run() -> None:
    """
    Clean the folder used for the model run
    """

    removable_fdpas = [NGEN_RUN_DATA_FDPA, RAVEN_RUN_DATA_FDPA, COMPARING_RUNS_DATA_FDPA]

    [shutil.rmtree(i_fdpa) for i_fdpa in removable_fdpas if os.path.exists(i_fdpa)]

    return None


def compare_results(meta_info: dict) -> dict:
    """
    Compare the results of the model runs
    :return: A dictionary containing the results of the comparison with the keys:
        - "auto": PASSING | FAILING                      # when we determine pass/fail without comparing
        - "same_number_of_time_points": int | str        # int: equal number of time points, str: diff
        - "same_simulated_time_length": timedelta | str  # timedelta: equal time length,     str: diff
        - "same_simulated_time_finish": datetime | str   # datetime: equal time finish,      str: diff
        - "differences": dict                            # only present if the above indicate no difference
    """

    # if one among the NexGen and Raven standalone models was not run: no comparison to be made
    if ("ngnp" not in meta_info) or ("rvmd" not in meta_info):
        auto_ret = PASSING if (("ngnp" in meta_info) or ("rvmd" in meta_info)) else FAILING
        return {"auto": auto_ret}
    
    echo("Comparing results.")

    os.makedirs(COMPARING_RUNS_DATA_FDPA) if not os.path.exists(COMPARING_RUNS_DATA_FDPA) else None

    # copy all files with name matching regex 'cat-[0-9]+.csv' and 'nex-[0-9]+_output.csv'
    #   from the NexGen runs to the '/data_comparison' folder
    ngen_fipas = glob.glob(os.path.join(NGEN_RUN_OUTPUT_FDPA, "*-*.csv"))
    total_ngen_files_copied = 0
    for i_fipa in ngen_fipas:
        i_fina = os.path.basename(i_fipa)
        if re.match(r"cat-[0-9]+.csv", i_fina) or re.match(r"nex-[0-9]+_output.csv", i_fina):
            shutil.copy(i_fipa, COMPARING_RUNS_DATA_FDPA)
            total_ngen_files_copied += 1
        del i_fipa, i_fina
    del ngen_fipas
    if total_ngen_files_copied == 0:
        echo("ISSUE: No files matching 'cat-[0-9]+.csv' or 'nex-[0-9]+_output.csv' found.")
    
    # copy all files with name matching regex 'cat-[0-9]+_Hydrographs.csv'
    #   from the Raven standalone runs to the '/data_comparison' folder
    raven_fipas = glob.glob(os.path.join(RAVEN_RUN_DATA_FDPA, "*.csv"))
    total_raven_files_copied = 0
    for i_fipa in raven_fipas:
        i_fina = os.path.basename(i_fipa)
        if re.match(r"cats_Hydrographs.csv", i_fina):
            shutil.copy(i_fipa, COMPARING_RUNS_DATA_FDPA)
            total_raven_files_copied += 1
        del i_fipa, i_fina
    if total_raven_files_copied == 0:
        echo(f"ISSUE: No files matching 'cats_Hydrographs.csv' found among {raven_fipas}.")
    del raven_fipas

    # at least one file from each run needs to be copied
    if (total_ngen_files_copied == 0) or (total_raven_files_copied == 0):
        fail_exit("At least one file from each run needs to be copied")

    # our working directory needs to be set to '/data_comparison'
    os.chdir(COMPARING_RUNS_DATA_FDPA)

    # Raven is expected to produce a single file with the name 'cats_Hydrographs.csv'
    raven_df= pd.read_csv("cats_Hydrographs.csv", index_col="time", infer_datetime_format=True,
                          parse_dates={'Time': ['date','hour']},)
    
    # all time information from Raven is the same for all records, so we can just get once
    n_time_points_raven = raven_df.shape[0]
    raven_ini, raven_end = raven_df['Time'].values[0], raven_df['Time'].values[-1]
    delta_time_raven = nptimedelta_to_days(raven_end - raven_ini)
    
    # each subcat in NGen is expected to produce a file with the name 'cat-[0-9]+.csv'
    # we need to find each file and compare the results
    ngen_cat_finas = [i for i in os.listdir() if re.match(r"cat-[0-9]+.csv", i)]

    # if there are no files, then there is no comparison to be made
    if len(ngen_cat_finas) == 0:
        fail_exit("No files matching 'cat-[0-9]+.csv' found.")
    
    # we need to compare the results of each subcat and accumulate the results
    ret_dict = {}
    for i_cat_fina in ngen_cat_finas:
        i_cat_fibana = i_cat_fina[:-4]

        # 
        i_ngen_df = pd.read_csv(i_cat_fina, index_col="Time Step", infer_datetime_format=True,
                                parse_dates=['Time'])

        # first of all, the date times must match in size and content
        i_any_time_issue = False

        # simplest: just count the number of records
        i_n_time_points_ngen = i_ngen_df.shape[0]
        if i_n_time_points_ngen != n_time_points_raven:
            ret_dict["same_number_of_time_points"] = f"Different number of time steps for {0}. "\
                                    f"NexGen: {i_n_time_points_ngen}, Raven: {n_time_points_raven}"
            i_any_time_issue = True
        else:
            ret_dict["same_number_of_time_points"] = i_n_time_points_ngen
        del i_n_time_points_ngen, n_time_points_raven

        i_ngen_ini, i_ngen_end = i_ngen_df['Time'].values[0], i_ngen_df['Time'].values[-1]
        
        # total delta time: the difference between the last and first time points
        i_delta_time_ngen = nptimedelta_to_days(i_ngen_end - i_ngen_ini)
        
        if i_delta_time_ngen != delta_time_raven:
            ret_dict["same_simulated_time_length"] = f"Different total simulated duration. "\
                                f"NexGen: {i_delta_time_ngen} days, Raven: {delta_time_raven} days."
            i_any_time_issue = True
        else:
            ret_dict["same_simulated_time_length"] = i_delta_time_ngen
        del i_delta_time_ngen

        # last time point: the last time point of the simulation
        if i_ngen_end != raven_end:
            i_ngen_end = pd.to_datetime(i_ngen_end).strftime(DATETIME_FORMAT)
            raven_end = pd.to_datetime(raven_end).strftime(DATETIME_FORMAT)
            ret_dict["same_simulated_time_finish"] = f"Different final simulated time. "\
                                                     f"NexGen: {i_ngen_end}, Raven: {raven_end}"
            i_any_time_issue = True
        else:
            ret_dict["same_simulated_time_finish"] = i_ngen_end
        del i_ngen_ini, i_ngen_end

        # there is not reason to continue if there is any issue with the time
        if i_any_time_issue:
            return ret_dict
        
    del raven_ini, raven_end, delta_time_raven

    ret_dict["differences"] = {}
    for i_cat_fina in ngen_cat_finas:
        i_cat_fibana = i_cat_fina[:-4]

        # first record from the Raven standalone model is garbage, so we remove it and the last record
        #  from the NexGen model to have the same number of records
        i_col_name = f'{i_cat_fibana} [m3/s]'
        if i_col_name not in raven_df.columns:
            fail_exit(f"Column {i_col_name} not found in 'cats_Hydrographs.csv' (columns: "\
                      f"{', '.join(raven_df.columns)}).")
        i_discharges_raven = raven_df[i_col_name].values[1:]
        i_ngen_df = pd.read_csv(i_cat_fina, index_col="Time Step", infer_datetime_format=True,
                                parse_dates=['Time'])
        i_discharge_ngen = i_ngen_df['OUTFLOW'].values[:-1]

        echo(f"Comparing {i_cat_fibana}.")
        echo(f"  NexGen: {i_discharge_ngen[:3]} ... {i_discharge_ngen[-4:]}")
        echo(f"   Raven: {i_discharges_raven[:3]} ... {i_discharges_raven[-4:]}")

        # we divide the difference by the average of the average to reduce the bias caused by the scale
        i_pct_diff = np.abs((i_discharges_raven - i_discharge_ngen) /
                            ((i_discharges_raven + i_discharge_ngen)/2))

        i_min_ngen,  i_max_ngen  = np.min(i_discharge_ngen),   np.max(i_discharge_ngen)
        i_min_raven, i_max_raven = np.min(i_discharges_raven), np.max(i_discharges_raven)

        i_pct_max_diff = np.abs((i_max_ngen - i_max_raven)/((i_max_ngen + i_max_raven)/2))
        i_pct_min_diff = np.abs((i_min_ngen - i_min_raven)/((i_min_ngen + i_min_raven)/2))

        # we may not use all of that information, but it is good to have it
        ret_dict["differences"][i_cat_fibana] = {
            "pct_diff_range":  (np.min(i_pct_diff), np.max(i_pct_diff)),
            "pct_minmax_diff": (i_pct_min_diff,     i_pct_max_diff),
            "ngen_range":      (i_min_ngen,         i_max_ngen),
            "raven_range":     (i_min_raven,        i_max_raven)
        }

    return ret_dict


def echo(message: str) -> None:
    """
    Print a message
    """

    print(f"│├ {message}")
    return None


def fail_exit(message: str) -> None:
    """
    Print a message and exit with a failure code
    """

    print(f"│└ FAIL: {message}")
    clean_folder_used_for_model_run()
    sys.exit(FAILING)


def pass_exit() -> None:
    """
    Exit with a passing code
    """

    print(f"│└ Ok.")
    clean_folder_used_for_model_run()
    sys.exit(PASSING)


def get_cli_args() -> dict:
    """
    Get the command line arguments
    """

    parser = argparse.ArgumentParser(description="Test")
    parser.add_argument("folder_path", help="Path to the folder containing the exemple/test files.",
                        type=str)
    args = vars(parser.parse_args())

    if not os.path.exists(args["folder_path"]):
        fail_exit("The example/test folder path provided does not exist:\n"\
                  f"       '{args['folder_path']}'.")

    return args


def passed(results: dict) -> bool:
    """
    Judge the results of the model runs
    :return: True if the results are considered passing, False otherwise
    """

    # the "auto" key is used to indicate if there is a need to compare the results
    if "auto" in results:
        return True if (results["auto"] == PASSING) else False
    
    # if the number of time points is different or the time points are different, then it is a fail
    issues_with_time = []
    if "same_number_of_time_points" in results:
        if type(results["same_number_of_time_points"]) is str:
            issues_with_time.append(results["same_number_of_time_points"])
        else:
            echo(f"Common number of time points: {results['same_number_of_time_points']}.")
    if "same_simulated_time_length" in results:
        if type(results["same_simulated_time_length"]) is str:
            issues_with_time.append(results["same_simulated_time_length"])
        else:
            echo(f"Common simulated time: {'%.2f' % results['same_simulated_time_length']} days.")
    if "same_simulated_time_finish" in results:
        if type(results["same_simulated_time_finish"]) is str:
            issues_with_time.append(results["same_simulated_time_finish"])
        else:
            # convert np.datetime64 to datetime
            dt_str = pd.to_datetime(results["same_simulated_time_finish"]).strftime(DATETIME_FORMAT)
            echo(f"Common simulated time finish: {dt_str}.")
            del dt_str
    if len(issues_with_time) > 0:
        echo("ISSUE: There is at least one issue with the time:")
        [echo(f"- {i_issue}") for i_issue in issues_with_time]
        return False
    del issues_with_time
    
    # now we can compare the discharge values
    if "differences" not in results:
        echo("No differences found. Shouldn't it be here?")
        return True
    
    # if timming is ok, we can go for the discharge values
    issues_with_values = []
    for i_run, i_run_diff in results["differences"].items():
        i_pass_max = i_run_diff["pct_minmax_diff"][0] <= MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE
        i_pass_min = i_run_diff["pct_minmax_diff"][1] <= MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE
        i_e = f"- Run '{i_run}':"
        if i_pass_max and i_pass_min:
            echo(f"{i_e} PASS simulated discharge comparison.")
        else:
            if (not i_pass_max) and i_pass_min:
                i_e2 = "min value difference %0.1f%% > %0.1f%% threshold" % \
                        (i_run_diff["pct_minmax_diff"][0]*100,
                            MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE*100)
            elif i_pass_max and (not i_pass_min):
                i_e2 = "max value difference %0.1f%% > %0.1f%% threshold" % \
                        (i_run_diff["pct_minmax_diff"][1]*100,
                        MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE*100)
            else:
                i_e2 = "both min (%0.1f%%) and max (%0.1f%%) differences > %0.1f%% threshold" % \
                        (i_run_diff["pct_minmax_diff"][0]*100,
                         i_run_diff["pct_minmax_diff"][1]*100,
                         MAX_SUPPORTED_EXTREME_PERCENT_DIFFERENCE*100)
            echo(f"{i_e} FAIL simulated discharge comparisoncomparison ({i_e2}).")
            echo(f"{i_e}   NexGen range: {i_run_diff['ngen_range']}.")
            echo(f"{i_e}    Raven range: {i_run_diff['raven_range']}.")
            issues_with_values.append(i_run)
            del i_e2
        del i_run, i_run_diff, i_pass_max, i_pass_min, i_e

    # one single issue with the discharge values is enough to fail
    if len(issues_with_values) > 0:
        echo("ISSUE: There is at least one issue with the discharge values:")
        [echo(f"- {i_issue}") for i_issue in issues_with_values]
        return False
    del issues_with_values

    # ok, time to give up, you win, pass!
    return True


def parse_folder_path(folder_path: str) -> dict:
    """
    Parse the folder path
    """

    folder_name = os.path.basename(folder_path)
    folder_name_parts = folder_name.split("_")

    ret_args = {}

    for i, i_folder_name_part in enumerate(folder_name_parts):
        i_key_value = i_folder_name_part.split("-")

        if len(i_key_value) != 2:
            fail_exit(f"The folder name part {i_folder_name_part} does not a key-value pair.")

        i_key, i_value = i_key_value
        del i_key_value, i, i_folder_name_part

        # each value needs to be processed differently based on the key
        if i_key in TEST_FDNA_KEYS_INT:
            if not i_value.isdigit():
                fail_exit(f"The {i_key} value '{i_value}' is not an integer.")
            ret_args[i_key] = int(i_value)
        elif i_key == "id":
            if (not i_value.isdigit()) or (len(i_value) != 2):
                fail_exit(f"The id value {i_value} is not a 2-digit integer.")
            ret_args[i_key] = i_value
        elif i_key == "ngts":
            if i_value not in TEST_FDNA_VALUES_NGTS:
                fail_exit(f"Value of ngts '{i_value}' is not among {TEST_FDNA_VALUES_NGTS}.")
            ret_args[i_key] = i_value
        elif i_key == "rvmd":
            if i_value not in TEST_FDNA_VALUES_RVMD:
                fail_exit(f"Value of rvmd '{i_value}' is not among {TEST_FDNA_VALUES_RVMD}.")
            ret_args[i_key] = i_value
        else:
            fail_exit(f"Unexpected key {i_key} in folder name.")

        del i_key, i_value

    return ret_args


def run_nexgen(test_folder_path: str, meta_info: dict) -> Union[bool, None]:
    """
    Run the NexGen model
    :return: True if the model ran successfully, False otherwise
    """

    # it can be the case where the NexGen model is not to be run
    if "ngnp" not in meta_info:
        return None
    
    # files need to be copied to the '/data' folder
    src_fdpa = os.path.join(test_folder_path, TEST_SUBFDNA_RV_IN_NGEN)
    shutil.copytree(src_fdpa, "/data")

    # working directory needs to be set to '/data/3_models_outputs'
    os.chdir(NGEN_RUN_OUTPUT_FDPA)

    if meta_info["ngnp"] > 1:
        raise NotImplementedError("Running NexGen with more than 1 worker is not implemented.")
    else:
        return run_nexgen_serial(meta_info)


def run_nexgen_serial(meta_info: dict) -> bool:
    """
    Run the NexGen model in serial
    :return: True if the model ran successfully, False otherwise
    """

    ngen_bin_fipa = NGEN_BIN_FIPA["serial"][meta_info["ngts"]]
    cmd = f"{ngen_bin_fipa} /data/1_raw/gis/catchments.geojson all "\
                           "/data/1_raw/gis/nexus.geojson all "\
                           "/data/2_models_inputs/realization_raven.json"

    # a new subprocess is created to run the NexGen model
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, shell=True)
    std_out, std_err = process.communicate()
    del cmd, ngen_bin_fipa

    # at this moment we are only interested in checking if the model ran successfully
    if process.returncode == 0:
        return True
    
    echo(f"NGen failed to run. Exit code: {process.returncode}.")
    echo(f"NGen stdout:")
    echo(std_out)
    echo(f"NGen stderr:")
    echo(std_err)

    return False


def run_raven(test_folder_path: str, meta_info: dict) -> Union[bool, None]:
    """
    Run the Raven model
    :return: True if the model ran successfully, False if it failed, None if it was not to be run
    """

    if "rvmd" not in meta_info:
        return None

    # files need to be copied to the '/data_raven' folder
    shutil.copytree(os.path.join(test_folder_path, TEST_SUBFDNA_RV_STANDALONE),
                    RAVEN_RUN_DATA_FDPA)

    # working directory needs to be set to '/data_raven'
    os.chdir(RAVEN_RUN_DATA_FDPA)

    # find file in the folder with the extension '.rvi'
    rvi_finas = [i for i in os.listdir() if i.endswith(".rvi")]
    if len(rvi_finas) != 1:
        echo(f"ISSUE: Expected to find a \'.rvi\' file in \'{RAVEN_RUN_DATA_FDPA}\' but found "\
             f"{len(rvi_finas)}{'' if len(rvi_finas) == 0 else ', '.join(rvi_finas)}.")
        return False
    rvi_fibana = rvi_finas[0][:-4]
    del rvi_finas

    # 
    cmd = f"{RAVEN_STANDALONE_BIN_FIPA} {os.path.join(RAVEN_RUN_DATA_FDPA, rvi_fibana)} -r cats -s"

    # a new subprocess is created to run the Raven model
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, shell=True)
    std_out, std_err = process.communicate()
    del cmd, rvi_fibana

    # at this moment we are only interested in checking if the model ran successfully
    if process.returncode != 0:
        echo(f"Raven failed to run. Exit code: {process.returncode}.")
        echo(f"Raven stderr:")
        echo(std_err)
        return False

    # all runs should produce a 'Raven_errors.txt' file
    if not 'Raven_errors.txt' in os.listdir():
        echo("ISSUE: Raven run did not produce a 'Raven_errors.txt' file.")
        return False

    # content of the 'Raven_errors.txt' file needs to be assessed
    with open('Raven_errors.txt', 'r') as f:
        raven_errors_lines = f.readlines()
    
    # any line starting with 'ERROR :' means a fail
    errors = [i_line for i_line in raven_errors_lines if i_line.startswith("ERROR :")]
    if len(errors) > 0:
        echo(f"Raven errors:")
        for i_error in errors:
            echo(f"- {i_error[8:].strip()}")
        return False
    
    # not ending with 'SIMULATION COMPLETE': means fail
    if not raven_errors_lines[-1].strip().startswith("SIMULATION COMPLETE"):
        echo("Raven did not finish the simulation.")
        return False
    
    # got here? then the model ran successfully! congratulations!
    return True


def run_test(test_folder_path: str, meta_info: dict) -> None:
    """
    Run the models
    """

    try:
        n_total_workers =  multiprocessing.cpu_count()
    except NotImplementedError:
        n_total_workers =  os.cpu_count()

    n_workers_ngen = meta_info["ngnp"] if ("ngnp" in meta_info) else 0 
    n_workers_rv = 1 if "rvmd" in meta_info else 0
    n_workers_demanded = n_workers_ngen + n_workers_rv
    echo(f"Total workers: {n_total_workers}. Workers demanded: {n_workers_demanded}.")

    if (n_workers_ngen > 0) and (n_workers_rv > 0) and (n_total_workers >= n_workers_demanded) and False:  # TODO - remove the False after implementing
        echo(f"Running NexGen and Raven standalone in parallel.")
        echo(f"WARNING: not implemented - assumes PASS.")
        sys.exit(PASSING)
    else:
        echo(f"Running NexGen and Raven standalone in serial.")
        ngen_success = run_nexgen(test_folder_path, meta_info)
        raven_success = run_raven(test_folder_path, meta_info)
    
    if (type(ngen_success) is None) and (type(raven_success) is None):
        fail_exit("No models to run! Test poorly configured!")
    
    # check both models to alert the user if one (or both) of them failed
    passes = True
    if (type(ngen_success) is bool) and (not ngen_success):
        echo("NexGen failed to run.")
        passes = False
    if (type(raven_success) is bool) and (not raven_success):
        echo("Raven failed to run.")
        passes = False
    fail_exit(FAILING) if (not passes) else None

    return None


def nptimedelta_to_days(td: np.timedelta64) -> float:
    """
    Convert a numpy timedelta64 to days
    """

    return td / np.timedelta64(1, 'D')


# ## MAIN ######################################################################################## #

if __name__ == "__main__":

    # 
    cli_args = get_cli_args()

    # the name of the folder holds some meta information about the tests
    test_meta_info = parse_folder_path(cli_args["folder_path"])
    assess_test_subfolders(cli_args["folder_path"], test_meta_info)

    # example/test folder needs to have the minimum required subfolders before running the models
    run_test(cli_args["folder_path"], test_meta_info)
    
    # once the model runs are complete, we can compare the results
    comparison_results = compare_results(test_meta_info)

    # communication with the main process is done through the exit code
    pass_exit() if passed(comparison_results) else fail_exit("Something went wrong.")
