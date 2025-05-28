#!/usr/bin/python
# -*- coding: UTF-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Michael Berg-Mohnicke <michael.berg@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the Institute of
# Landscape Systems Analysis at the ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)

import csv
from datetime import datetime, timedelta
import os
import sys
from collections import defaultdict
import zmq
import shared

import monica_io3


def run_consumer(server=None, port=None):
    config = {
        "port": port if port else "7777",
        "server": server if server else "localhost",
        "path-to-output-dir": "./out",
    }
    shared.update_config(config, sys.argv, print_config=True, allow_new_keys=False)

    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://" + config["server"] + ":" + config["port"])
    socket.RCVTIMEO = 6000

    path_to_out_dir = config["path-to-output-dir"]
    if not os.path.exists(path_to_out_dir):
        try:
            os.makedirs(path_to_out_dir)
        except OSError:
            print(f"{os.path.basename(__file__)} Couldn't create dir {path_to_out_dir}! Exiting.")
            exit(1)

    daily_filepath = f"{path_to_out_dir}/Ex_All_Daily_MONICA_Results.csv"
    with open(daily_filepath, "wt", newline="", encoding="utf-8") as daily_f:
        daily_writer = csv.writer(daily_f, delimiter=",")

        # Write headers
        daily_writer.writerow([
            "Experiment", "Crop", "Date", "Zadocks phenology stage", "N Fertilizer", "Irrigation Amount",
            "Primary Yield", "Total above biomass", "Leaf Area Index", "Daily Transpiration",
            "Actual evapotranspiration", "Runoff", "Deep Percolation", "N Leaching", "Soil Water Content"
        ])

        swc_header_row = [f"SWC_{i}" for i in range(1, 21)]
        n_header_row = [f"N_{i}" for i in range(1, 21)]
        daily_writer.writerow([
            "Exp", "Crop", "Date", "ZDPH", "NFert", "Irrig", "PYield", "AbBiom", "LAI", "TRANS", "ETa", "Roff", "DPER",
            "NLEA"
        ] + swc_header_row + n_header_row)

        no_of_exps_to_receive = None
        no_of_exps_received = 0

        while no_of_exps_to_receive != no_of_exps_received:
            try:
                # Receive message
                msg: dict = socket.recv_json()

                if msg.get("errors", []):
                    print(f"{os.path.basename(__file__)} received errors: {msg['errors']}")
                    continue

                custom_id = msg.get("customId", {})

                # Check if all experiments are received
                if custom_id.get("nodata", False):
                    no_of_exps_to_receive = custom_id.get("no_of_exps", None)
                    print(f"{os.path.basename(__file__)} received nodata=true -> done")
                    continue

                no_of_exps_received += 1
                exp_no = custom_id.get("exp_no", None)

                print(f"{os.path.basename(__file__)} received result exp_no: {exp_no}")

                # Process data from the message
                data: dict = msg["data"][0]
                results: list = data["results"]

                sowing_date = None
                for vals in results:
                    if not sowing_date:
                        sowing_date = vals["Date"]

                    swc_data = vals["SWC"]
                    n_data = vals["N"]
                    row = [exp_no, vals["Crop"], vals["Date"], vals["Stage"], vals["NFert"], vals["Irrig"],
                           vals["Yield"], vals["AbBiom"], vals["LAI"], vals["TRANS"], vals["ETa"], vals["Roff"],
                           vals["DPER"], vals["NLEA"]] + swc_data + n_data
                    daily_writer.writerow(row)

            except Exception as e:
                print(f"{os.path.basename(__file__)} Exception: {e}")

        print(f"{os.path.basename(__file__)} exiting run_consumer()")


def write_monica_out(exp_no, msg):
    path_to_out_dir = "out"
    if not os.path.exists(path_to_out_dir):
        try:
            os.makedirs(path_to_out_dir)
        except OSError:
            print("c: Couldn't create dir:", path_to_out_dir, "! Exiting.")
            exit(1)

    # with open("out/out-" + str(i) + ".csv", 'wb') as _:
    path_to_file = path_to_out_dir + "/exp_no-" + str(exp_no) + ".csv"
    with open(path_to_file, "w", newline='') as _:
        writer = csv.writer(_, delimiter=";")
        for data_ in msg.get("data", []):
            results = data_.get("results", [])
            orig_spec = data_.get("origSpec", "")
            output_ids = data_.get("outputIds", [])
            if len(results) > 0:
                writer.writerow([orig_spec.replace("\"", "")])
                for row in monica_io3.write_output_header_rows(output_ids,
                                                               include_header_row=True,
                                                               include_units_row=False,
                                                               include_time_agg=False):
                    writer.writerow(row)
                for row in monica_io3.write_output_obj(output_ids, results):
                    writer.writerow(row)
            writer.writerow([])
    print("wrote:", path_to_file)


if __name__ == "__main__":
    run_consumer()
