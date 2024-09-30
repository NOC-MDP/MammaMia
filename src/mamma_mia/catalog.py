from dataclasses import dataclass,field,InitVar
import intake
import copernicusmarine

# TODO find a better way to do this, MSM sources use meta data in intake catalog.
cmems_alias = {
    "nitrate": ["no3"],
    "phosphate": ["po4"],
    "silicate": ["si"],
    "temperature": ["thetao"],
    "salinity": ["so"],
    "pressure": ["pres"],
    "ucomponent": ["uo"],
    "vcomponent": ["vo"],
}


@dataclass
class Cats:
    """
    Catalog class
    """
    cmems_cat: dict = field(init=False)
    msm_cat: intake.Catalog = field(init=False)
    search : InitVar[str] = "Global"
    cat_path: InitVar[str] = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = False
    # TODO need some kind of refresh option that will delete caches of downloaded data. (user enabled and probably if data is older than x?)
    def __post_init__(self, search,cat_path ):
        self.cmems_cat = copernicusmarine.describe(contains=[search], include_datasets=True,
                                                   overwrite_metadata_cache=self.overwrite)
        self.msm_cat = intake.open_catalog(cat_path)