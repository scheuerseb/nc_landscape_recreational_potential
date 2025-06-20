# This script computes the recreational potential of a landscape based on projected NFF scenario data and baseline conditions of landscape recreational potential.
# It uses the recreat package to perform the necessary calculations and reads inputs/writes outputs from/into the specified working directory.
# Installation of the recreat package is required via pip: pip install recreat
# The current recreat version is 0.3.2 
#
# Sebastian Scheuer, 2025
#

from recreat.assessment import Recreat

import numpy as np
import os
import rioxarray as riox

# To run this script, prepare a working directory that contains, in subdirectories (i.e., root paths), the land systems map files corresponding to the NFF scenario. 
# In addition, the working directory should contain a baseline directory (baseline root path) with the land systems map and assessments conducted for baseline.

# path to folder with the LSM grid and into which results will be exported
working_directory = "<path/to/folder>"
nodata_value = -9999

reclsm = Recreat(working_directory)
reclsm.set_params('nodata-value', nodata_value)
reclsm.set_params('verbose-reporting', 'True')

# first, open the baseline land-use map and burn class 100 into scenario map 
# this step is done manually for scnenarios
baseline_root_path = 'baseline'
baseline_lsm_filename = '<land-systems-map-for-baseline.tif>'
scenario_filename = '<NFF-scenario-filename.tif>'
scenario_root_path = '<root-path-foldername-in-working-directory-containing-scenario-file>'
scenario_outfile_name = '<name-of-modified-scenario-file-used-in-assessment.tif>'

scenario_file_path = os.path.join(working_directory, scenario_root_path, scenario_filename)
baseline_file_path = os.path.join(working_directory, baseline_root_path, baseline_lsm_filename)
# open the baseline land use map
baseline_map = riox.open_rasterio(baseline_file_path)
# open the scenario land use map
scenario_map = riox.open_rasterio(scenario_file_path)
# burn class 100 into the scenario map
scenario_map.values = np.where( ((scenario_map == nodata_value) & (baseline_map == 100)), baseline_map, scenario_map)
# similarly, burn class 900 into the scenario map, as otherwise, clumps will be incorrect due to nodata values
scenario_map.values = np.where( ((scenario_map == nodata_value) & (baseline_map == 900)), baseline_map, scenario_map)

# write burned raster
scenario_map.rio.to_raster(os.path.join(working_directory, scenario_root_path, scenario_outfile_name), driver='GTiff', dtype='int16', nodata=nodata_value)

# the scenarios require re-coding, as they use other land use class codes
mappings_of_classes = {
    210 : [0],
    220 : [1],
    230 : [2],
    300 : [3],
    410 : [4],
    420 : [5],
    510 : [6],
    520 : [7],
    530 : [8],
    610 : [9],
    620 : [10],
    630 : [11],
    700 : [12],
    810 : [13],
    830 : [14],
    840 : [15]
}


reclsm.set_land_use_map(root_path=scenario_root_path, land_use_filename=scenario_outfile_name)
reclsm.align_land_use_map(nodata_values=[-9999], reclassification_mappings=mappings_of_classes, overwrite=False)

reclsm.set_params('classes.patch', [300, 410, 420, 610, 620, 630, 810, 830, 840]) 
reclsm.set_params('classes.edge', [100, 700])
reclsm.set_params('classes.builtup', [210, 220, 230])

# define cost thresholds in units of pixels
reclsm.set_params('costs', [3,11,21,61]) 

# set cost weighting schema
inverse_distance_cost_weights = {
    3 : 1,
    11: 1/5,
    21: 1/10,
    61: 1/30
}

inverse_logistic_cost_weights = {
     3 : 0.974773792,
    11 : 0.799354883,
    21 : 0.430832418,
    61 : 0.002161295
}


# # (1) basic pre-processing
reclsm.detect_clumps(barrier_classes=[nodata_value, 100])
reclsm.mask_landuses()    
reclsm.detect_edges(ignore_edges_to_class=nodata_value, buffer_edges=[100]) 

# (2) determination of supply and diversity
reclsm.class_total_supply()
reclsm.aggregate_class_total_supply()
reclsm.average_total_supply_across_cost(cost_weights=inverse_logistic_cost_weights)
reclsm.class_diversity()
reclsm.average_diversity_across_cost(cost_weights=inverse_logistic_cost_weights)

# (3) compute proximities
reclsm.compute_proximity_rasters(mode = 'xr', assess_builtup=False)
reclsm.cost_to_closest()
reclsm.minimum_cost_to_closest()
reclsm.average_cost_to_closest(distance_threshold=61)

# (4) manually process changes in demand based on disaggregated baseline population
baseline_disagr_pop = os.path.join(working_directory, baseline_root_path, 'DEMAND', 'disaggregated_population.tif')
scenario_file_path = os.path.join(working_directory, scenario_root_path, 'BASE', 'lulc.tif')

# open the baseline land use map
baseline_pop = riox.open_rasterio(baseline_disagr_pop)
# open the scenario land use map
scenario_map = riox.open_rasterio(scenario_file_path)
# make numpy arrays
lulc_data = scenario_map.values[0]
mtx_baseline_pop = baseline_pop.values[0]
mtx_scenario_pop = np.zeros_like(lulc_data, dtype=np.float32)

# transfer rules:
# direct transfer of disgaggregated pop values to classes 210, 220, 230. This will keep population constant for pixels already existing in baseline
# for residential pixels in baseline not existing in scenarios, this will set population to 0. 
# for residential pixels not in baseline but existing in scenarios, population will be 0 and needs to be corrected afterwards.
mtx_scenario_pop = np.where(lulc_data == 210, mtx_baseline_pop, mtx_scenario_pop)
mtx_scenario_pop = np.where(lulc_data == 220, mtx_baseline_pop, mtx_scenario_pop)
mtx_scenario_pop = np.where(lulc_data == 230, mtx_baseline_pop, mtx_scenario_pop)

# determine mean pixel values per class
mean_210 = np.mean(mtx_baseline_pop, where=lulc_data == 210)
mean_220 = np.mean(mtx_baseline_pop, where=lulc_data == 220)
mean_230 = np.mean(mtx_baseline_pop, where=lulc_data == 230)

mtx_scenario_pop = np.where(((lulc_data == 210) & (mtx_scenario_pop == 0)), mean_210, mtx_scenario_pop)
mtx_scenario_pop = np.where(((lulc_data == 220) & (mtx_scenario_pop == 0)), mean_220, mtx_scenario_pop)
mtx_scenario_pop = np.where(((lulc_data == 230) & (mtx_scenario_pop == 0)), mean_230, mtx_scenario_pop)

# get nodata mask from clumps 
ds_clump = riox.open_rasterio(os.path.join(working_directory, scenario_root_path, 'BASE', 'clumps.tif'))
scenario_nodata_mask = np.isin(ds_clump.values[0], [nodata_value], invert=False)
mtx_scenario_pop[scenario_nodata_mask] = nodata_value

# re-assign data source and write raster
scenario_map.values = mtx_scenario_pop.reshape(1, lulc_data.shape[0], lulc_data.shape[1])
scenario_map.rio.to_raster(os.path.join(working_directory, scenario_root_path, 'DEMAND', 'disaggregated_population.tif'), driver='GTiff', dtype='float32', nodata=nodata_value)

# run through demand/flow-based steps
reclsm.beneficiaries_within_cost()
reclsm.average_beneficiaries_across_cost(cost_weights=inverse_logistic_cost_weights)
reclsm.class_flow()
reclsm.aggregate_class_flow()
reclsm.average_flow_across_cost(cost_weights=inverse_logistic_cost_weights)


