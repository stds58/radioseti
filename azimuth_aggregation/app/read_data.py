import pprint
import asyncio
from pathlib import Path
import polars as pl


async def read_csv() -> pl.DataFrame:
    csv_path = Path(__file__).parent.parent / "app/data" / "data_fixed_h3.csv"

    df = pl.read_csv(
        csv_path,
        separator=";",
        try_parse_dates=True
    )
    return df


async def group_by_avtocod_enodebid(df: pl.DataFrame) -> pl.DataFrame:
    all_cols = df.columns
    exclude_cols = [
        "avtocod", "enodebid", "azimuth", "nc_latitude", "nc_longitude", "eventtime", "neighbour",
        "latitude", "longitude", "altitude", "h3_15", "servingcellrsrp", "servingcellrsrq"
    ]
    other_cols = [col for col in all_cols if col not in exclude_cols]

    result = (
        df
        .unique(subset=other_cols)
        .group_by(["avtocod", "enodebid", "azimuth", "nc_latitude", "nc_longitude"])
        .agg([
            pl.struct(other_cols).alias("cells"),
            pl.len().alias("uniq_count")
        ])
    )

    return result


async def main() -> list[dict]:
    df = await read_csv()
    grouped_df = await group_by_avtocod_enodebid(df)
    return grouped_df.to_dicts()


if __name__ == "__main__":
    grouped_df = asyncio.run(main())

    with pl.Config(tbl_rows=10, tbl_cols=50, tbl_width_chars=1000, fmt_str_lengths=1000):
        print("\nСгруппированный DataFrame:")
        print(grouped_df)

        pprint.pprint(grouped_df, width=120, compact=False)



