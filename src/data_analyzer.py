import pandas as pd


class DataAnalyzer:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def _validate_columns(
        self,
        columns: list[str]
    ):
        missing = [
            column
            for column in columns
            if column not in self.df.columns
        ]

        if missing:
            raise ValueError(
                f"These columns do not exist in the dataset: {missing}"
            )

    def _apply_filters(
        self,
        df: pd.DataFrame,
        filters: list[dict],
    ) -> pd.DataFrame:

        if not filters:
            return df

        result = df

        for condition in filters:

            column = condition.get("column")
            operator = condition.get("operator", "==")
            value = condition.get("value")

            if column is None:
                continue

            self._validate_columns([column])

            series = result[column]

            if operator == "==":
                result = result[series == value]

            elif operator == "!=":
                result = result[series != value]

            elif operator == ">":
                result = result[series > value]

            elif operator == "<":
                result = result[series < value]

            elif operator == ">=":
                result = result[series >= value]

            elif operator == "<=":
                result = result[series <= value]

            elif operator == "in":
                values = value if isinstance(value, list) else [value]
                result = result[series.isin(values)]

            elif operator == "contains":
                result = result[
                    series.astype(str).str.contains(
                        str(value), case=False, na=False
                    )
                ]

            else:
                raise ValueError(
                    f"Unsupported filter operator: {operator}"
                )

        return result

    def _aggregate_series(
        self,
        series: pd.Series,
        aggregation: str,
    ):

        if aggregation in {"sum", "total"}:
            return series.sum()

        elif aggregation in {"mean", "average"}:
            return series.mean()

        elif aggregation == "median":
            return series.median()

        elif aggregation == "min":
            return series.min()

        elif aggregation == "max":
            return series.max()

        elif aggregation == "count":
            return series.count()

        elif aggregation == "nunique":
            return series.nunique()

        raise ValueError(
            f"Unsupported aggregation: {aggregation}"
        )

    def _execute_compare_periods(
        self,
        analysis: dict,
    ) -> pd.DataFrame:

        group_by = analysis.get("group_by", [])
        period_column = analysis.get("period_column")
        current_period = analysis.get("current_period")
        previous_period = analysis.get("previous_period")
        value_column = analysis.get("value_column")
        aggregation = analysis.get("aggregation", "sum").lower()

        if not group_by:
            raise ValueError(
                "compare_periods requires 'group_by' to be set."
            )

        for field_name, field_value in {
            "period_column": period_column,
            "current_period": current_period,
            "previous_period": previous_period,
            "value_column": value_column,
        }.items():
            if field_value in (None, ""):
                raise ValueError(
                    f"compare_periods requires '{field_name}' to be set."
                )

        self._validate_columns(group_by + [period_column, value_column])

        filters = analysis.get("filters", [])
        base_df = self._apply_filters(self.df, filters)

        current_df = base_df[
            base_df[period_column] == current_period
        ]
        previous_df = base_df[
            base_df[period_column] == previous_period
        ]

        current_grouped = (
            current_df
            .groupby(group_by, dropna=False)[value_column]
            .apply(lambda s: self._aggregate_series(s, aggregation))
            .reset_index(name="current_value")
        )

        previous_grouped = (
            previous_df
            .groupby(group_by, dropna=False)[value_column]
            .apply(lambda s: self._aggregate_series(s, aggregation))
            .reset_index(name="previous_value")
        )

        merged = pd.merge(
            current_grouped,
            previous_grouped,
            on=group_by,
            how="outer",
        )

        merged["current_value"] = merged["current_value"].fillna(0)
        merged["previous_value"] = merged["previous_value"].fillna(0)

        def compute_growth(row):
            if row["previous_value"] == 0:
                return None
            return (
                (row["current_value"] - row["previous_value"])
                / row["previous_value"]
                * 100
            )

        merged["growth_percent"] = merged.apply(compute_growth, axis=1)

        sort = analysis.get("sort", "descending").lower()
        ascending = sort in {"ascending", "asc", "lowest"}

        merged = merged.sort_values(
            by="growth_percent",
            ascending=ascending,
            na_position="last",
        )

        limit = analysis.get("limit")
        if isinstance(limit, int) and limit > 0:
            merged = merged.head(limit)

        return merged.reset_index(drop=True)

    def execute(
        self,
        analysis: dict
    ):

        operation = analysis.get("operation", "aggregate").lower()

        if operation == "compare_periods":
            return self._execute_compare_periods(analysis)

        required_columns = analysis.get(
            "required_columns",
            []
        )

        group_by = analysis.get(
            "group_by",
            []
        )

        aggregation = analysis.get(
            "aggregation",
            ""
        ).lower()

        sort = analysis.get(
            "sort",
            ""
        ).lower()

        limit = analysis.get("limit")

        filters = analysis.get("filters", [])

        self._validate_columns(required_columns)
        self._validate_columns(group_by)

        working_df = self._apply_filters(self.df, filters)

        # ---------------------------------------
        # GROUP BY OPERATIONS
        # ---------------------------------------

        if group_by:

            value_column = None

            for column in required_columns:
                if column not in group_by:
                    value_column = column
                    break

            if value_column:

                grouped = working_df.groupby(
                    group_by,
                    dropna=False
                )[value_column]

                if aggregation in {"sum", "total"}:

                    result = grouped.sum()

                elif aggregation in {"mean", "average"}:

                    result = grouped.mean()

                elif aggregation == "median":

                    result = grouped.median()

                elif aggregation == "min":

                    result = grouped.min()

                elif aggregation == "max":

                    result = grouped.max()

                elif aggregation == "count":

                    result = grouped.count()

                elif aggregation == "nunique":

                    result = grouped.nunique()

                else:

                    raise ValueError(
                        f"Unsupported aggregation: {aggregation}"
                    )

                result = result.reset_index()

            else:

                result = (
                    working_df
                    .groupby(group_by, dropna=False)
                    .size()
                    .reset_index(name="count")
                )

        # ---------------------------------------
        # SINGLE COLUMN AGGREGATION
        # ---------------------------------------

        elif required_columns:

            value_column = required_columns[0]

            self._validate_columns([value_column])

            series = working_df[value_column]

            if aggregation in {"sum", "total"}:

                result = pd.DataFrame({
                    value_column: [series.sum()]
                })

            elif aggregation in {"mean", "average"}:

                result = pd.DataFrame({
                    value_column: [series.mean()]
                })

            elif aggregation == "median":

                result = pd.DataFrame({
                    value_column: [series.median()]
                })

            elif aggregation == "min":

                result = pd.DataFrame({
                    value_column: [series.min()]
                })

            elif aggregation == "max":

                result = pd.DataFrame({
                    value_column: [series.max()]
                })

            elif aggregation == "count":

                result = pd.DataFrame({
                    "count": [series.count()]
                })

            elif aggregation == "nunique":

                result = pd.DataFrame({
                    value_column: [series.nunique()]
                })

            else:

                raise ValueError(
                    f"Unsupported aggregation: {aggregation}"
                )

        else:

            raise ValueError(
                "The analysis did not specify columns to calculate."
            )

        # ---------------------------------------
        # SORTING
        # ---------------------------------------

        if sort:

            if isinstance(sort, str):

                sort_column = (
                    value_column
                    if value_column
                    and value_column in result.columns
                    else result.columns[-1]
                )

                ascending = sort in {
                    "ascending",
                    "asc",
                    "lowest"
                }

                result = result.sort_values(
                    by=sort_column,
                    ascending=ascending
                )

        # ---------------------------------------
        # LIMIT
        # ---------------------------------------

        if isinstance(limit, int) and limit > 0:

            result = result.head(limit)

        return result.reset_index(drop=True)


def dataframe_to_records(
    df: pd.DataFrame
) -> list[dict]:

    result = df.copy()

    # Handle NaN / NaT values.
    result = result.astype(object).where(
        result.notna(),
        None
    )

    return result.to_dict(
        orient="records"
    )