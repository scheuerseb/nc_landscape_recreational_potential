# This script computes the recreational potential of a landscape based on a gridded land systems map and a gridded population dataset.
# It uses the recreat package to perform the necessary calculations and reds inputs/writes outputs from/into the specified working directory.
# Installation of the recreat package is required via pip: pip install recreat
# The current recreat version is 0.3.2 
#
# Sebastian Scheuer, 2025
#

from recreat.assessment import Recreat
from recreat.disaggregation import DisaggregationMethod

# Path to working directory with the gridded land systems map dataset and the gridded population dataset for baseline in subfolder 'baseline' (i.e., as root path) and into which results will be written.
working_directory = "<path/to/folder>"
baseline_root_path = 'baseline'
baseline_lsm_filename = '<land-systems-map-for-baseline.tif>'
baseline_gridded_population_filename = '<gridded-population-dataset-for-baseline.tif>'
nodata_value = -9999

reclsm = Recreat(working_directory)
reclsm.set_params('nodata-value', nodata_value)
reclsm.set_params('verbose-reporting', 'True')

reclsm.set_land_use_map(root_path=baseline_root_path, land_use_filename=baseline_lsm_filename)

# need to redefine classes to match scenarios
mappings_of_classes = {
    810 : [810, 820],
    840 : [840, 850]
}

reclsm.align_land_use_map(nodata_values=[0], reclassification_mappings=mappings_of_classes, overwrite=False)

reclsm.set_params('classes.patch', [300, 410, 420, 610, 620, 630, 810, 830, 840]) 
reclsm.set_params('classes.edge', [100, 700])
reclsm.set_params('classes.builtup', [210, 220, 230])

# define cost thresholds ij units of pixels
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


# (1) basic pre-processing
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

# (4) determination of demand and flow
reclsm.disaggregation(baseline_gridded_population_filename, max_pixel_count=1, disaggregation_method=DisaggregationMethod.SimpleAreaWeighted)
reclsm.beneficiaries_within_cost()
reclsm.average_beneficiaries_across_cost(cost_weights=inverse_logistic_cost_weights)
reclsm.class_flow()
reclsm.aggregate_class_flow()
reclsm.average_flow_across_cost(cost_weights=inverse_logistic_cost_weights)

