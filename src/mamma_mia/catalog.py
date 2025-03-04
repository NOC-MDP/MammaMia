from dataclasses import dataclass,field,InitVar
import intake
import copernicusmarine

# TODO find a better way to do this, MSM sources use meta data in intake catalog.
# Aliases used to map CMEMS variable names to Mamma Mia parameter names
cmems_alias = {
    "nitrate": ["no3"],
    "phosphate": ["po4"],
    "silicate": ["si"],
    "TEMP": ["thetao"],
    "CNDC": ["so"],
    "PRES": ["pres"],
    "u_component": ["uo"],
    "v_component": ["vo"],
    "w_component": ["wo"]
}


@dataclass
class Cats:
    """
    Catalog class, contains all the model source data that is available to download. There is a field for each source,
    these are populated with their relevent catalogs that can be searched for matching worlds.

    Args:
        search: string that overrides the default search term used for CMEMS sources
        cat_path: string that overides the default catalog location used for MSM sources
        overwrite: bool that overwrites the metadata cache used for CMEMS sources

    Returns:
        Populated Cats object
    """
    cmems_cat: dict = field(init=False)
    msm_cat: intake.Catalog = field(init=False)
    search : InitVar[str] = "Global"
    cat_path: InitVar[str] = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = True
    # TODO need some kind of refresh option that will delete caches of downloaded data. (user enabled and probably if data is older than x?)
    def __post_init__(self, search,cat_path ):
        self.cmems_cat = copernicusmarine.describe(contains=[search], include_datasets=True,overwrite_metadata_cache=self.overwrite)
        self.msm_cat = intake.open_catalog(cat_path)