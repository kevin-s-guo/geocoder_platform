import os
import pandas as pd
import psycopg2
import psycopg2.extras
import re

from lib import DBNAME, DBUSER


def load_sdoh_desc(desc_csv_fn, source, version, census_year, granularity, url, desc):  # version has to be a year
    # replace space with _
    df = pd.read_csv(desc_csv_fn).rename(columns=lambda s: s.replace(" ", "_"))

    if granularity not in ["zip", "county", "tract", "blockgroup"]:
        return False, "Granularity must be one of 'zip', 'county', 'tract', or 'blockgroup'"

    if census_year not in [2010, 2020]:
        return False, 'Census boundary year must be 2010 or 2020'

    if "variable" not in df.columns or "description" not in df.columns:
        return False, "Variable description csv must have columns for 'variable' and 'description'"

    df = df.set_index("variable")['description'].fillna("")

    vars = list(df.index)

    for v in vars:
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            return False, "Variables must have alphanumeric (with dash/underscore) names. Error: " + str(v)

    tablename = source + "_" + str(version) + "_" + granularity
    with psycopg2.connect(f"dbname={DBNAME} user={DBUSER}") as conn:
        with conn.cursor() as cur:
            # insert into sdoh_source:
            cur.execute(
                "INSERT INTO sdoh.sdoh_source (id, name, version, url, description, granularity, census_year) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (tablename, source, version, url, desc, granularity, census_year))

            # insert each variable
            for v in vars:
                cur.execute(
                    "INSERT INTO sdoh.sdoh (id, description, census_year, level, source, version) VALUES (%s, %s, %s, %s, %s, %s)",
                    (v, df[v], census_year, granularity, source, version))

    return True, f"{len(vars)} variables"


def load_sdoh_data(data_csv_fn, index_col, source, version, granularity):
    # confirm that columns are only alphanumeric
    df = pd.read_csv(data_csv_fn, dtype={index_col: int})
    df = df.rename(columns=lambda s: s.replace(" ", "_")).drop_duplicates().set_index(index_col, verify_integrity=True)

    for col in df:
        if not re.match(r'^[a-zA-Z0-9-_]+$', col):
            return False, "Columns must have alphanumeric (with dash/underscore) names. Error: " + str(col)

    vars = list(df.columns)

    if len(vars) > 1599:
        return False, "Postgres does not support tables with more than 1600 columns. Please split into multiple databases with 1599 or fewer variables."

    # determine which table to store into (based on granularity and year) based on sdoh table
    tablename = source + "_" + str(version) + "_" + granularity
    with psycopg2.connect(f"dbname={DBNAME} user={DBUSER}") as conn:
        with conn.cursor() as cur:
            # need to create a new table for each source because postgres only allows 1600 per table
            col_sql = ", ".join(list(map(lambda s: s + " varchar(255)", vars)))
            cur.execute(
                f"CREATE TABLE sdoh.{tablename} ({granularity.upper() + 'FIPS'} bigint PRIMARY KEY, {col_sql});")

            entities = [[e] + [s[v] for v in vars] for e, s in df.iterrows()]
            sql = "INSERT INTO sdoh." + tablename + " (" + granularity.upper() + "FIPS," + ",".join(vars)
            sql += ") VALUES (%s, " + ", ".join(["%s" for v in vars]) + ")"
            psycopg2.extras.execute_batch(cur, sql, entities)


def download_data(name=""):
    if name == "places":
        # TODO: download appropriate version
        places_df = pd.read_csv("tmp/PLACES__Local_Data_for_Better_Health__Census_Tract_Data_2021_release.csv")
        places_df["variable"] = places_df["MeasureId"]
        places_df["description"] = places_df["Category"] + ": " + places_df["Measure"]
        places_df["TRACTFIPS"] = places_df["LocationID"]

        places_df[["variable", "description"]].drop_duplicates().to_csv("tmp/places_2021_desc.csv")

        pd.pivot(places_df[["variable", "Data_Value", "TRACTFIPS"]], index="TRACTFIPS", columns="variable",
                 values="Data_Value").to_csv("tmp/places_2021.csv")
        pass
    elif name == "ahrq":
        # TODO: download appropriate data

        # TODO: process data
        print(load_sdoh_desc("data/places_2021_desc.csv", source="places", version="2021",
                             desc="PLACES: Local Data for Better Health",
                             census_year=2010, granularity="tract",
                             url="https://chronicdata.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-Census-Tract-D/cwsq-ngmh"))
        load_sdoh_data("data/ahrq_2020.csv", index_col="TRACTFIPS", source="ahrq", version="2020", granularity="tract")


# print(load_sdoh_desc("data/ahrq_2020_desc.csv", source="ahrq", version="2020", desc="Agency for Healthcare Research and Quality Social Determinants of Health Database",
#                census_year=2020, granularity="tract", url="https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html"))
#
# load_sdoh_data("data/ahrq_2020.csv", index_col="TRACTFIPS", source="ahrq", version="2020", granularity="tract")

# print(load_sdoh_desc("data/places_2021_desc.csv", source="places", version="2021", desc="PLACES: Local Data for Better Health",
#                census_year=2010, granularity="tract", url="https://chronicdata.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-Census-Tract-D/cwsq-ngmh"))

# load_sdoh_data("data/places_2021.csv", index_col="TRACTFIPS", source="places", version="2021", granularity="tract")

# print(load_sdoh_desc("data/svi_2020_desc.csv", source="svi", version="2020", desc="CDC/ATSDR Social Vulnerability Index",
#                census_year=2020, granularity="tract", url="https://www.atsdr.cdc.gov/placeandhealth/svi/index.html"))
# load_sdoh_data("data/svi_2020.csv", index_col="FIPS", source="svi", version="2020", granularity="tract")

# print(load_sdoh_desc("data/fea_2020_desc.csv", source="fea", version="2020", desc="Food Environment Atlas",
#                census_year=2010, granularity="county", url="https://www.ers.usda.gov/data-products/food-environment-atlas/"))
# load_sdoh_data("data/fea_2020.csv", index_col="FIPS", source="fea", version="2020", granularity="county")

# print(load_sdoh_desc("data/eji_2022_desc.csv", source="eji", version="2022", desc="CDC/ATSDR Environmental Justice Index",
#                census_year=2010, granularity="tract", url="https://www.atsdr.cdc.gov/placeandhealth/eji/index.html/"))
# load_sdoh_data("data/eji_2022.csv", index_col="geoid", source="eji", version="2022", granularity="tract") # many duplicate rows...

# print(load_sdoh_desc("data/cre_2019_desc.csv", source="cre", version="2019", desc="Community Resilience Estimates",
#                census_year=2010, granularity="tract", url="https://www.census.gov/programs-surveys/community-resilience-estimates.html"))
# print(load_sdoh_data("data/cre_2019.csv", index_col="GEO_ID", source="cre", version="2019", granularity="tract"))

# print(load_sdoh_desc("data/ruca_2019_desc.csv", source="ruca", version="2019", desc="Rural-Urban Commuting Area Codes",
#                census_year=2010, granularity="tract", url="https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes.aspx"))
# load_sdoh_data("data/ruca_2019.csv", index_col="FIPS", source="ruca", version="2019", granularity="tract")

# print(load_sdoh_desc("data/hl_2003_desc.csv", source="hl", version="2003", desc="National Health Literacy Map",
#                census_year=2010, granularity="blockgroup", url="http://healthliteracymap.unc.edu/#"))
load_sdoh_data("data/hl_2003.csv", index_col="ID", source="hl", version="2003", granularity="blockgroup")
