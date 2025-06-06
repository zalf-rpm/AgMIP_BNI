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

import copy
import json
import os
import sys
import zmq
from collections import defaultdict
import pandas as pd
from datetime import datetime

import monica_io3
import shared

def run_producer(server=None, port=None, exp_nos=None):
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)  # pylint: disable=no-member

    config = {
        "mode": "mbm-local-remote",
        "server-port": port if port else "6666",
        "server": server if server else "localhost",
        "sim.json": os.path.join(os.path.dirname(__file__), "sim.json"),
        "crop.json": os.path.join(os.path.dirname(__file__), "crop.json"),
        "site.json": os.path.join(os.path.dirname(__file__), "site.json"),
        "monica_path_to_climate_dir": r"C:\Users\escueta\PycharmProjects\AgMIP_BNI\data",
        "path_to_data_dir": "./data/",
        "path_to_out": "out/",
    }
    shared.update_config(config, sys.argv, print_config=True, allow_new_keys=False)

    socket.connect("tcp://" + config["server"] + ":" + config["server-port"])

    with open(config["sim.json"]) as _:
        sim_json = json.load(_)

    with open(config["site.json"]) as _:
        site_json = json.load(_)

    with open(config["crop.json"]) as _:
        crop_json = json.load(_)

    with open("data/monica-parameters/mineral-fertilisers/AN.json") as f:
        an_fert_params = json.load(f)

    with open("data/monica-parameters/mineral-fertilisers/UAN.json") as f:
        uan_fert_params = json.load(f)

    with open("data/monica-parameters/organic-fertilisers/CAM.json") as f:
        cam_fert_params = json.load(f)

    with open("data/monica-parameters/organic-fertilisers/CAS.json") as f:
        cas_fert_params = json.load(f)

    # Extract templates from crop configuration
    fert_min_template = crop_json.pop("fert_min_template")
    fert_org_template = crop_json.pop("fert_org_template")
    irrig_template = crop_json.pop("irrig_template")
    till_template = crop_json.pop("till_template")

    # Read soil data and fill missing values
    soil_df = pd.read_csv(f"{config['path_to_data_dir']}/Soil.csv", sep=';')

    soil_profiles = defaultdict(list)
    prev_depth_m = 0
    prev_soil_name = None

    for _, row in soil_df.iterrows():
        soil_name = row['Soil']
        if soil_name != prev_soil_name:
            prev_soil_name = soil_name
            prev_depth_m = 0
        current_depth_m = float(row['Depth'])/100.0
        thickness = round(current_depth_m - prev_depth_m, 1)
        prev_depth_m = current_depth_m

        layer = {
            "Thickness": [thickness, "m"],
            "SoilBulkDensity": [float(row['Bulk_density'])*1000 , "kg/m3"] if pd.notnull(row['Bulk_density']) else
            print("Bulk_density is missing for soil: ", soil_name),
            "SoilOrganicCarbon": [float(row['Corg']), "%"] if pd.notnull(row['Corg']) else print("Corg is missing for "
                                                                                                 "soil: ", soil_name),
            "Clay": [float(row['Clay']), "m3/m3"],
            "Sand": [float(row['Sand']), "m3/m3"],
            "Silt": [float(row['Silt']), "m3/m3"],
            "pH": [float(row['pH']), "pH"] if pd.notnull(row['pH']) else print("pH is missing for soil: ", soil_name),
            "CN": [float(row['C_N']), ""] if pd.notnull(row['C_N']) else print("CN is missing for soil: ", soil_name)
        }
        soil_profiles[soil_name].append(layer)

    # Read metadata and management data
    metadata_df = pd.read_csv(f"{config['path_to_data_dir']}/Meta.csv", sep=';') #This is the path to the "Meta" file, which connects everything
    fert_min_df = pd.read_csv(f"{config['path_to_data_dir']}/Fertilisation_min.csv", sep=';')
    fert_org_df = pd.read_csv(f"{config['path_to_data_dir']}/Fertilisation_org.csv", sep=';')
    irrig_df = pd.read_csv(f"{config['path_to_data_dir']}/Irrigation.csv", sep=';')
    till_df = pd.read_csv(f"{config['path_to_data_dir']}/Management.csv", sep=';')

    # Merge datasets
    merged_df_fert_min = pd.merge(metadata_df, fert_min_df, on='Fertilisation_min')
    merged_df_fert_org = pd.merge(metadata_df, fert_org_df, on='Fertilisation_org')
    merged_df_irrig = pd.merge(metadata_df, irrig_df, on='Irrigation')
    merged_df_till = pd.merge(metadata_df, till_df, on='Management')

    exp_no_to_fertilizers_min = defaultdict(dict)
    exp_no_to_fertilizers_org = defaultdict(dict)
    exp_no_to_irrigation = defaultdict(dict)
    exp_no_to_management = defaultdict(dict)

    for _, row in merged_df_fert_min.iterrows():
        if pd.isna(row['Fertilisation_min']) or row['Fertilisation_min'] == 'no_fert':
            continue
        fert_min_temp = copy.deepcopy(fert_min_template)
        fert_min_temp["date"] = datetime.strptime(row['Date'], '%d.%m.%Y').strftime('%Y-%m-%d')
        fert_min_temp["amount"][0] = float(row['Amount_kg_ha'])
        if row['Material'] == 'ammonium nitrate lime':
            fert_min_temp["partition"] = copy.deepcopy(an_fert_params)
        if row['Material'] == 'ammonium urea solution':
            fert_min_temp["partition"] = copy.deepcopy(uan_fert_params)
        exp_no_to_fertilizers_min[row['Experiment']][fert_min_temp["date"]] = fert_min_temp

    for _, row in merged_df_fert_org.iterrows():
        if pd.isna(row['Fertilisation_org']) or row['Fertilisation_org'] == 'no_fert':
            continue
        fert_org_temp = copy.deepcopy(fert_org_template)
        fert_org_temp["date"] = datetime.strptime(row['Date'], '%d.%m.%Y').strftime('%Y-%m-%d')
        fert_org_temp["amount"][0] = float(row['Amount_kg_ha'])
        # fert_org_temp["parameters"] = copy.deepcopy(cam_fert_params)
        if row['Material'] == 'Farmyard manure':
            fert_org_temp["parameters"] = copy.deepcopy(cam_fert_params)
        elif row['Material'] == 'Liquid manure':
            fert_org_temp["parameters"] = copy.deepcopy(cas_fert_params)
        exp_no_to_fertilizers_org[row['Experiment']][fert_org_temp["date"]] = fert_org_temp

    for _, row in merged_df_irrig.iterrows():
        if pd.isna(row['Irrigation']) or row['Irrigation'] in ['no_irrig', 'wet', 'dry', 1, 2]:
            continue
        irrig_temp = copy.deepcopy(irrig_template)
        irrig_temp["date"] = datetime.strptime(row['Date'], '%d.%m.%Y').strftime('%Y-%m-%d')
        irrig_temp["amount"][0] = float(row['Amount_mm'])
        exp_no_to_irrigation[row['Experiment']][irrig_temp["date"]] = irrig_temp

    # Soil management
    for _, row in merged_df_till.iterrows():
        if pd.isna(row['Management']) or row['Management'] == 'no_manag':
            continue
        till_temp = copy.deepcopy(till_template)
        till_temp["date"] = datetime.strptime(row['Date'], '%d.%m.%Y').strftime('%Y-%m-%d')
        till_temp["depth"] = [float(row['Depth']) / 100.0, 'm']
        exp_no_to_management[row['Experiment']][till_temp["date"]] = till_temp

    exp_no_to_meta = metadata_df.set_index('Experiment').T.to_dict('dict')
    no_of_exps = 0

    env_template = None
    for exp_no, meta in exp_no_to_meta.items():
        # Skip experiments not in the exp_nos list if exp_nos is provided
        if exp_nos is not None and exp_no not in exp_nos:
            continue

        # if meta['Crop'] not in ['ZR']:
        #     continue

        # Set the crop based on the experiment
        crop_json["cropRotation"][2] = meta['Crop']

        env_template = monica_io3.create_env_json_from_json_config({
            "crop": crop_json,
            "site": site_json,
            "sim": sim_json,
            "climate": ""  # climate_csv
        })

        worksteps: list = copy.deepcopy(env_template["cropRotation"][0]["worksteps"])

        env_template["csvViaHeaderOptions"] = sim_json["climate.csv-options"]
        env_template["pathToClimateCSV"] = f"{config['monica_path_to_climate_dir']}/{meta['Weather']}.csv"

        env_template["params"]["siteParameters"]["SoilProfileParameters"] = soil_profiles[meta['Soil']]

        env_template["params"]["siteParameters"]["HeightNN"] = float(meta['Elevation'])
        env_template["params"]["siteParameters"]["Latitude"] = float(meta['Lat'])

        # complete crop rotation
        dates = set()
        dates.update(exp_no_to_fertilizers_min[exp_no].keys(), exp_no_to_fertilizers_org[exp_no].keys(),
                     exp_no_to_irrigation[exp_no].keys(), exp_no_to_management[exp_no].keys())

        worksteps_copy = copy.deepcopy(worksteps)
        sowing_date = datetime.strptime(meta['Sowing'], '%d.%m.%Y')
        worksteps_copy[0]["date"] = sowing_date.strftime('%Y-%m-%d')
        harvest_date = datetime.strptime(meta['Harvest'], '%d.%m.%Y')
        worksteps_copy[-1]["date"] = harvest_date.strftime('%Y-%m-%d')

        # Residue management
        residue = str(meta.get("Residues", "")).strip()

        if "straw ploughed in" == residue:
            worksteps_copy[-1]["shoot"] = {
                "export": [0, "%"],
                "incorporate": True
            }
        elif "straw exported" == residue:
            worksteps_copy[-1]["shoot"] = {
                "export": [100, "%"],
                "incorporate": True
            }
        elif "leaves ploughed in" == residue:
            worksteps_copy[-1]["leaf"] = {
                "export": [0, "%"],
                "incorporate": True
            }

        for date in sorted(dates):
            if date in exp_no_to_fertilizers_min[exp_no]:
                worksteps_copy.insert(-1, copy.deepcopy(exp_no_to_fertilizers_min[exp_no][date]))
            if date in exp_no_to_fertilizers_org[exp_no]:
                worksteps_copy.insert(-1, copy.deepcopy(exp_no_to_fertilizers_org[exp_no][date]))
            if date in exp_no_to_irrigation[exp_no]:
                worksteps_copy.insert(-1, copy.deepcopy(exp_no_to_irrigation[exp_no][date]))
            if date in exp_no_to_management[exp_no]:
                tillage_event = copy.deepcopy(exp_no_to_management[exp_no][date])
                tillage_date = datetime.strptime(tillage_event["date"], '%Y-%m-%d')
                # Add tillage events before sowing at the beginning of worksteps
                if tillage_date < sowing_date:
                    worksteps_copy.insert(0, tillage_event)
                # Add tillage events after harvest at the end of worksteps
                elif tillage_date > harvest_date:
                    worksteps_copy.insert(-1, tillage_event)
                # Add tillage events between sowing and harvest before the harvest
                else:
                    worksteps_copy.insert(-1, tillage_event)

        env_template["cropRotation"][0]["worksteps"] = worksteps_copy

        env_template["customId"] = {
            "nodata": False,
            "exp_no": exp_no,
            "soil_name": meta['Soil']
        }

        socket.send_json(env_template)
        no_of_exps += 1
        print(f"{os.path.basename(__file__)} sent job {no_of_exps} for experiment number: {exp_no}")

        # Save the sent env_template as a json file
        # with open(f"out/env_template_{exp_no}.json", "w") as _:
        #     json.dump(env_template, _, indent=4)

    env_template["customId"] = {
            "no_of_exps": no_of_exps,
            "nodata": True,
            "soil_name": meta['Soil']
    }
    socket.send_json(env_template)
    print(f"{os.path.basename(__file__)} done")

if __name__ == "__main__":
    # Run all experiments
    run_producer()

    # Run specific experiments
    # run_producer(exp_nos=["EX1", "EX2", "EX3", "EX4", "EX5", "EX6"])  # plot1
    # run_producer(exp_nos=["EX7", "EX8", "EX9", "EX10", "EX11", "EX12")  # plot2
    # run_producer(exp_nos=["EX13", "EX14", "EX15", "EX16", "EX17", "EX18"])  # plot3
